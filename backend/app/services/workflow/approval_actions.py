"""Ejecución de acciones financieras retenidas tras aprobación humana.

Cuando una tool de escritura financiera supera `APPROVAL_THRESHOLD_EUR`, en vez de
ejecutar la acción guarda en `PendingApproval.action_payload` la acción
**estructurada**: `{"kind": <str>, "params": {...}, "summary": <str>}` (vía
`create_action_approval`). Al aprobar, `_resume_orchestrator` llama a
`execute_approved_action`, que ejecuta el executor registrado para ese `kind`
saltándose el cap — la decisión humana ES la autorización.

Registro genérico (`register_action`) para que añadir un nuevo tipo de acción
aprobable sea declarar un executor, sin tocar el resume.

Capa servicios: NO importa agentes. La persistencia vive aquí.
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import get_current_task
from app.db.base import AsyncSessionLocal
from app.db.models.accounting import JournalEntry, JournalLine
from app.db.models.hr import Payroll
from app.db.models.models import Client, PendingApproval

logger = logging.getLogger(__name__)

# kind -> executor(params, db, tenant_id) -> (ok, summary)
Executor = Callable[[dict, AsyncSession, str], Awaitable[tuple[bool, str]]]
_EXECUTORS: dict[str, Executor] = {}

_APPROVAL_TTL = timedelta(hours=2)


def register_action(kind: str) -> Callable[[Executor], Executor]:
    def deco(fn: Executor) -> Executor:
        _EXECUTORS[kind] = fn
        return fn

    return deco


def is_registered(kind: str | None) -> bool:
    return bool(kind) and kind in _EXECUTORS


async def execute_approved_action(payload: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    """Ejecuta la acción retenida descrita por `payload` (kind+params).

    No hace commit ni toca la Task: el caller (resume) hace el bookkeeping.
    """
    kind = (payload or {}).get("kind")
    executor = _EXECUTORS.get(kind or "")
    if executor is None:
        return False, f"Acción aprobable desconocida: {kind!r}"
    params = payload.get("params") or {}
    try:
        return await executor(params, db, tenant_id)
    except Exception as e:  # noqa: BLE001 — el resume decide qué hacer con el fallo
        logger.exception("[APPROVAL] Error ejecutando acción aprobada kind=%s", kind)
        return False, f"Error ejecutando la acción aprobada: {e}"


async def create_action_approval(
    *,
    tenant_id: str,
    kind: str,
    params: dict,
    summary: str,
    task_id: str | None = None,
    execution_id: str | None = None,
) -> str | None:
    """Crea (o reutiliza) un PendingApproval estructurado para una acción retenida.

    Idempotente por task_id/execution_id: si ya hay una pendiente para esta
    task/execution, la reutiliza (no duplica). `task_id` se toma del ContextVar
    si no se pasa.
    """
    task_id = task_id or get_current_task()
    if not task_id and not execution_id:
        logger.warning(
            "[APPROVAL] create_action_approval sin task_id/execution_id (kind=%s) — "
            "no se puede enlazar la aprobación; se omite.",
            kind,
        )
        return None

    async with AsyncSessionLocal() as db:
        if task_id:
            existing = await db.execute(
                select(PendingApproval).where(
                    PendingApproval.task_id == uuid.UUID(task_id),
                    PendingApproval.status == "pending",
                )
            )
        else:
            existing = await db.execute(
                select(PendingApproval).where(
                    PendingApproval.execution_id == uuid.UUID(execution_id),
                    PendingApproval.status == "pending",
                )
            )
        row = existing.scalars().first()
        if row:
            return str(row.id)

        approval = PendingApproval(
            task_id=uuid.UUID(task_id) if task_id else None,
            execution_id=uuid.UUID(execution_id) if execution_id else None,
            tenant_id=uuid.UUID(tenant_id),
            action_description=summary[:500],
            action_payload={"kind": kind, "params": params, "summary": summary},
            risk_level="high",
            expires_at=datetime.now(UTC) + _APPROVAL_TTL,
            status="pending",
        )
        db.add(approval)
        await db.commit()
        await db.refresh(approval)
        return str(approval.id)


# ─── Executors ───────────────────────────────────────────────────────────────


@register_action("create_journal_entry")
async def _exec_create_journal_entry(params: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    lines = params.get("lines") or []
    total_debit = sum(Decimal(str(ln.get("debit", 0))) for ln in lines)
    entry = JournalEntry(
        tenant_id=uuid.UUID(tenant_id),
        date=date.fromisoformat(params["entry_date"]),
        description=params.get("description", ""),
    )
    db.add(entry)
    await db.flush()
    for ln in lines:
        db.add(
            JournalLine(
                tenant_id=uuid.UUID(tenant_id),
                entry_id=entry.id,
                account_code=str(ln["account_code"]),
                account_name=ln.get("account_name", ""),
                debit=Decimal(str(ln.get("debit", 0))),
                credit=Decimal(str(ln.get("credit", 0))),
            )
        )
    await db.flush()
    return True, f"Asiento creado tras aprobación. Importe: {total_debit:.2f}€."


@register_action("approve_payroll")
async def _exec_approve_payroll(params: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    tid = uuid.UUID(tenant_id)
    if params.get("approve_all"):
        from calendar import monthrange

        month = int(params.get("month") or 0)
        year = int(params.get("year") or 0)
        if not month or not year:
            return False, "Faltan mes/año para aprobar todas las nóminas."
        start = datetime(year, month, 1, tzinfo=UTC)
        end = datetime(year, month, monthrange(year, month)[1], 23, 59, 59, tzinfo=UTC)
        res = await db.execute(
            select(Payroll).where(
                and_(
                    Payroll.tenant_id == tid,
                    Payroll.status == "draft",
                    Payroll.period_start >= start,
                    Payroll.period_end <= end,
                )
            )
        )
        payrolls = res.scalars().all()
        for p in payrolls:
            p.status = "approved"
        await db.flush()
        return True, f"{len(payrolls)} nóminas de {month}/{year} aprobadas tras aprobación."

    payroll_id = params.get("payroll_id")
    if not payroll_id:
        return False, "Falta payroll_id."
    res = await db.execute(select(Payroll).where(Payroll.tenant_id == tid, Payroll.id == uuid.UUID(payroll_id)))
    payroll = res.scalar_one_or_none()
    if not payroll:
        return False, f"Nómina {payroll_id} no encontrada."
    payroll.status = "approved"
    await db.flush()
    return True, f"Nómina {payroll_id[:8]}... aprobada tras aprobación."


@register_action("create_invoice")
async def _exec_create_invoice(params: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    tid = uuid.UUID(tenant_id)
    amount_base = Decimal(str(params.get("amount_base", "0")).replace(",", "."))
    vat_rate = Decimal(str(params.get("vat_rate", 21)))
    concept = params.get("concept", "Concepto por aprobación manual")
    client_nif = params.get("client_nif") or ""
    client_name = params.get("client_name") or "Cliente"
    inv_date = date.fromisoformat(params.get("invoice_date") or datetime.now(UTC).strftime("%Y-%m-%d"))

    client = None
    if client_nif:
        res = await db.execute(select(Client).where(Client.tenant_id == tid, Client.nif == client_nif))
        client = res.scalars().first()
    if not client:
        # Resolver por nombre si no hay NIF / no existe
        res = await db.execute(select(Client).where(Client.tenant_id == tid, Client.name == client_name))
        client = res.scalars().first()
    if not client:
        client = Client(tenant_id=tid, nif=client_nif or None, name=client_name)
        db.add(client)
        await db.flush()

    # M6 del re-audit: este camino construía la factura A MANO (numeración por
    # count()+1 sin advisory lock y serie "FAC-" paralela — el patrón que el
    # propio repo califica de ilegal en sales/commands). Delegamos en el
    # servicio canónico: numeración con lock, totales Decimal y guardas
    # Verifactu centralizadas (nace draft: encadena al expedirse).
    from app.services.billing.commands import create_invoice as _create_invoice_svc

    try:
        invoice = await _create_invoice_svc(
            client.id,
            {"date": inv_date, "status": "draft", "invoice_type": "issued"},
            [
                {
                    "description": concept,
                    "quantity": 1,
                    "unit_price": float(amount_base),
                    "tax_percentage": float(vat_rate),
                }
            ],
            tid,
            None,
            db,
        )
    except ValueError as e:
        return False, f"Error creando la factura aprobada: {e}"
    return True, (
        f"Factura {invoice.invoice_number} creada tras aprobación. Total: {float(invoice.amount_total):.2f}€."
    )


@register_action("inventory_batch_adjust")
async def _exec_inventory_batch_adjust(params: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    """Aplica un ajuste de stock por lotes que estaba pendiente de aprobación."""
    from app.services.inventory import batch_service

    tid = uuid.UUID(tenant_id)
    res = await batch_service.batch_adjust_stock(
        db,
        tid,
        params.get("items") or [],
        op=params.get("op", "set"),
        reason=params.get("reason", "Aprobado"),
        dry_run=False,
    )
    return True, (
        f"Ajuste de stock aplicado tras aprobación: {res['applied']} productos "
        f"({res['ok']} OK, {res['skipped']} omitidos)."
    )


@register_action("gated_tool_call")
async def _exec_gated_tool_call(params: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    """Re-ejecuta una tool retenida por `gated_tool` (CONFIRM), saltándose el gate.

    El payload guarda module/func/kwargs. Se importa dinámicamente y se invoca
    la función ORIGINAL (`__wrapped__`), no el wrapper — re-llamar al wrapper
    re-evaluaría la política y volvería a bloquear (bucle de re-aprobación).
    """
    import importlib

    module_name = params.get("module") or ""
    func_name = params.get("func") or ""
    kwargs = dict(params.get("kwargs") or {})
    kwargs.setdefault("tenant_id", tenant_id)

    if not module_name.startswith("app."):
        return False, f"Módulo no permitido para gated_tool_call: {module_name!r}"

    mod = importlib.import_module(module_name)
    fn = getattr(mod, func_name, None)
    if fn is None:
        return False, f"Tool {module_name}.{func_name} no encontrada."
    # @tool de LangChain envuelve en StructuredTool: la coroutine real está en .coroutine
    fn = getattr(fn, "coroutine", fn)
    # Saltar el wrapper del gate (functools.wraps expone la original en __wrapped__)
    fn = getattr(fn, "__wrapped__", fn)

    result = await fn(**kwargs)
    return True, f"Acción ejecutada tras aprobación: {str(result)[:300]}"


@register_action("send_email")
async def _exec_send_email(params: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    """Envía un email retenido (recordatorios de pago, comunicaciones a clientes)."""
    from app.services.email.sender import send_email

    to = params.get("to") or ""
    subject = params.get("subject") or ""
    if not to or not subject:
        return False, "Faltan destinatario o asunto para enviar el email."
    result = await send_email(
        tenant_id=tenant_id,
        to=to,
        subject=subject,
        body=params.get("body") or "",
        attachment_ids=params.get("attachment_ids"),
    )
    ok = "enviado" in result.lower()
    return ok, result[:300]


@register_action("reconcile_transaction")
async def _exec_reconcile_transaction(params: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    """Concilia manualmente un movimiento bancario contra una factura (aprobado)."""
    from app.services.banking.service import reconcile_transaction

    tx_id = params.get("transaction_id")
    invoice_id = params.get("invoice_id")
    if not tx_id or not invoice_id:
        return False, "Faltan transaction_id o invoice_id para conciliar."
    user_id = params.get("user_id")
    try:
        await reconcile_transaction(
            db,
            uuid.UUID(tenant_id),
            uuid.UUID(user_id) if user_id else None,  # solo viaja a emit_event (nullable)
            uuid.UUID(str(tx_id)),
            str(invoice_id),
        )
    except LookupError as e:
        return False, str(e)
    return True, f"Movimiento {str(tx_id)[:8]}… conciliado con la factura tras aprobación."


@register_action("inventory_batch_update")
async def _exec_inventory_batch_update(params: dict, db: AsyncSession, tenant_id: str) -> tuple[bool, str]:
    """Aplica una actualización de catálogo por lotes pendiente de aprobación."""
    from app.services.inventory import batch_service

    tid = uuid.UUID(tenant_id)
    res = await batch_service.batch_update_fields(db, tid, params.get("items") or [], dry_run=False)
    return True, (
        f"Actualización de catálogo aplicada tras aprobación: {res['applied']} "
        f"productos ({res['ok']} OK, {res['skipped']} omitidos)."
    )
