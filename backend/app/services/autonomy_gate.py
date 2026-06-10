"""Gate de autonomía — puente entre SEC.AUT y los agentes (AI.AGT wiring).

Los agentes que ejecuten tools con efecto secundario (escribir en banking,
emitir facturas, enviar emails, crear asientos contables) DEBEN consultar
este gate antes de actuar. La política la mantiene SEC.AUT en la tabla
`autonomy_policy`; este módulo la traduce en una decisión accionable.

Patrón de uso desde una tool LangGraph:

    from app.services.autonomy_gate import evaluate_autonomy, AutonomyDecision

    async def transfer_funds(db, tenant_id, user_id, amount, ...):
        decision = await evaluate_autonomy(
            db, tenant_id=tenant_id, domain="banking_write",
            action_summary=f"Transferir {amount}€ a {beneficiary}",
            action_payload={"amount": amount, "beneficiary": beneficiary},
            user_id=user_id,
        )
        if decision.mode == "MANUAL":
            return decision.to_suggestion_response()
        if decision.mode == "CONFIRM":
            await decision.persist_pending_approval(db)
            return decision.to_pending_response()
        # AUTO: ejecutar la acción real.
        result = await _actually_transfer(...)
        return result
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tasks import PendingApproval
from app.services.autonomy import AutonomyMode, check_autonomy

logger = logging.getLogger("autonomy_gate")


@dataclass
class AutonomyDecision:
    """Decisión derivada de la política del tenant para una acción concreta."""

    mode: AutonomyMode
    domain: str
    tenant_id: UUID
    action_summary: str
    action_payload: dict[str, Any] = field(default_factory=dict)
    user_id: UUID | None = None
    task_id: UUID | None = None

    @property
    def can_execute(self) -> bool:
        """True si el agente puede ejecutar la acción directamente (AUTO)."""
        return self.mode == "AUTO"

    @property
    def needs_approval(self) -> bool:
        return self.mode == "CONFIRM"

    @property
    def manual_only(self) -> bool:
        return self.mode == "MANUAL"

    async def persist_pending_approval(
        self, db: AsyncSession, *, expires_in_days: int = 7,
        risk_level: str = "MEDIUM", kind: str | None = None,
    ) -> PendingApproval:
        """Crea una `PendingApproval` para que un humano apruebe.

        Solo tiene sentido cuando `mode == "CONFIRM"`. El caller debe hacer
        commit explícito tras esta llamada. Requiere `task_id` en el
        `AutonomyDecision` (la tabla `pending_approvals` lo exige).

        `kind` enlaza con un executor de `approval_actions.register_action`:
        al aprobar, `_resume_orchestrator` ejecuta la acción automáticamente.
        Sin `kind`, el payload cae en la ruta legacy (solo facturas) — pásalo
        siempre que exista un executor registrado.
        """
        payload = (
            {"kind": kind, "params": self.action_payload, "summary": self.action_summary}
            if kind
            else self.action_payload
        )
        if not self.needs_approval:
            raise ValueError(
                "persist_pending_approval solo aplica en modo CONFIRM"
            )
        if self.task_id is None:
            raise ValueError(
                "task_id es obligatorio para persistir PendingApproval. "
                "Si el gate se invoca fuera de un task, omite este paso y "
                "muestra `to_pending_response()` en la respuesta."
            )

        approval = PendingApproval(
            tenant_id=self.tenant_id,
            task_id=self.task_id,
            action_description=self.action_summary,
            action_payload=payload,
            risk_level=risk_level,
            expires_at=datetime.now(UTC) + timedelta(days=expires_in_days),
            status="pending",
        )
        db.add(approval)
        await db.flush()
        logger.info(
            "autonomy_gate.CONFIRM persisted approval=%s domain=%s tenant=%s",
            approval.id, self.domain, self.tenant_id,
        )
        try:
            from app.api.ws.notifications import manager as ws_manager

            await ws_manager.broadcast_to_tenant(
                str(self.tenant_id),
                {
                    "type": "approval_created",
                    "approval_id": str(approval.id),
                    "description": self.action_summary,
                    "domain": self.domain,
                },
            )
        except Exception:  # noqa: BLE001 — el WS nunca debe romper el flujo
            logger.debug("WS approval_created no emitido", exc_info=True)
        return approval

    def to_suggestion_response(self) -> dict[str, Any]:
        """Respuesta cuando MANUAL: devuelve sugerencia, no ejecuta."""
        return {
            "executed": False,
            "mode": "MANUAL",
            "reason": (
                f"La política de autonomía para `{self.domain}` está en MANUAL. "
                "El agente sugiere la acción pero no la ejecuta."
            ),
            "suggested_action": self.action_summary,
            "suggested_payload": self.action_payload,
        }

    def to_pending_response(self, approval_id: UUID | None = None) -> dict[str, Any]:
        """Respuesta cuando CONFIRM: la acción quedó pendiente de aprobación."""
        return {
            "executed": False,
            "mode": "CONFIRM",
            "approval_id": str(approval_id) if approval_id else None,
            "reason": (
                f"La política de autonomía para `{self.domain}` requiere confirmación humana. "
                "La acción se ha enviado a la bandeja de aprobaciones."
            ),
            "pending_action": self.action_summary,
            "pending_payload": self.action_payload,
        }


async def evaluate_autonomy(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    domain: str,
    action_summary: str,
    action_payload: dict[str, Any] | None = None,
    user_id: UUID | None = None,
    task_id: UUID | None = None,
) -> AutonomyDecision:
    """Consulta SEC.AUT y empaqueta la decisión en `AutonomyDecision`."""
    mode = await check_autonomy(db, tenant_id=tenant_id, domain=domain)
    logger.debug(
        "autonomy_gate eval domain=%s tenant=%s -> %s",
        domain, tenant_id, mode,
    )
    return AutonomyDecision(
        mode=mode,
        domain=domain,
        tenant_id=tenant_id,
        action_summary=action_summary[:500],
        action_payload=action_payload or {},
        user_id=user_id,
        task_id=task_id,
    )


def serialize_action_payload(payload: dict[str, Any]) -> str:
    """Util para tools que necesitan persistir el payload como string opaco."""
    return json.dumps(payload, default=str)


def gated_tool(
    *,
    domain: str,
    summary_fn=None,
):
    """Decorator que envuelve una tool LangGraph con el autonomy gate.

    Patrón de uso:

        from app.services.autonomy_gate import gated_tool

        @tool
        @gated_tool(
            domain="banking_write",
            summary_fn=lambda kwargs: f"Conciliar movimientos del tenant {kwargs.get('tenant_id')}",
        )
        async def reconcile_transactions(tenant_id: str, ...) -> str:
            return await _do_reconcile(tenant_id, ...)

    Si la política es:
      - AUTO    → ejecuta la tool normal y devuelve su resultado.
      - CONFIRM → crea un PendingApproval estructurado (kind=`gated_tool_call`)
                  que al aprobarse re-ejecuta la tool original saltándose el
                  gate (la decisión humana ES la autorización), y devuelve
                  string explicando que la acción quedó pendiente. El task_id
                  sale del ContextVar; si no hay task en curso, solo string.
      - MANUAL  → devuelve string con la sugerencia, sin ejecutar.
    """
    from functools import wraps

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from uuid import UUID

            from app.db.base import AsyncSessionLocal

            tenant_raw = kwargs.get("tenant_id") or (args[0] if args else None)
            if not tenant_raw:
                return await func(*args, **kwargs)
            try:
                tenant_uuid = UUID(str(tenant_raw))
            except (ValueError, TypeError):
                return await func(*args, **kwargs)

            summary = (
                summary_fn(kwargs) if summary_fn
                else f"Tool `{func.__name__}` sobre dominio `{domain}`"
            )

            async with AsyncSessionLocal() as db:
                decision = await evaluate_autonomy(
                    db,
                    tenant_id=tenant_uuid,
                    domain=domain,
                    action_summary=summary,
                    action_payload={"tool": func.__name__, "kwargs": {
                        k: str(v) for k, v in kwargs.items() if k != "tenant_id"
                    }},
                )

            if decision.can_execute:
                return await func(*args, **kwargs)

            if decision.needs_approval:
                from app.services.workflow.approval_actions import create_action_approval

                approval_id = await create_action_approval(
                    tenant_id=str(tenant_uuid),
                    kind="gated_tool_call",
                    params={
                        "module": func.__module__,
                        "func": func.__name__,
                        # JSONB-safe: tipos no serializables se degradan a str
                        "kwargs": {
                            k: v
                            if isinstance(v, str | int | float | bool | list | dict | None)
                            else str(v)
                            for k, v in kwargs.items()
                        },
                    },
                    summary=summary,
                )
                suffix = (
                    " Revisa tu bandeja de aprobaciones."
                    if approval_id
                    else " (No hay tarea activa: ejecútala desde la UI o aprueba la política.)"
                )
                return (
                    f"⏸ Acción pendiente de aprobación humana ({domain} = CONFIRM). "
                    f"He preparado la acción: «{summary}».{suffix}"
                )

            # MANUAL
            return (
                f"⚠ Política {domain}=MANUAL: no ejecuto automáticamente. "
                f"Sugerencia: «{summary}». Ejecútalo manualmente desde la UI."
            )

        return wrapper

    return decorator
