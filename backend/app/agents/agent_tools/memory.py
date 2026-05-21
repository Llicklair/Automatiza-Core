"""Tools de memoria persistente para AIEmployee.

Solo se activan en empleados con `memory_enabled=True` (capacidad 2/4 del
contrato custom — migración 0029_aiemployee_contract). Persisten en la
tabla `employee_memory` (migración 0032_employee_memory_and_rag_scope).

Las tools devuelven strings legibles para el LLM, nunca lanzan excepciones
a la capa superior — un fallo se reporta como mensaje para que el agente
decida cómo seguir.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.base import AsyncSessionLocal
from app.db.models.ai_employees import AIEmployee, EmployeeMemory

logger = logging.getLogger(__name__)

_RECALL_DEFAULT_LIMIT = 20
_KEY_MAX_LEN = 160


async def _employee_or_none(db, tenant_id: UUID, employee_id: UUID) -> AIEmployee | None:
    res = await db.execute(
        select(AIEmployee).where(
            AIEmployee.id == employee_id,
            AIEmployee.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


@tool
async def remember(
    tenant_id: str,
    employee_id: str,
    key: str,
    value: str,
    importance: int = 0,
) -> str:
    """Guarda un recuerdo asociado al empleado.

    Útil cuando el usuario te enseña un dato que querrás recordar en
    futuras conversaciones (preferencias, alias de clientes, fechas
    importantes, etc.). Si ya existe la misma `key`, se actualiza.

    Args:
        tenant_id: UUID del tenant (inyectado por el dispatcher).
        employee_id: UUID del empleado (inyectado por el dispatcher).
        key: identificador corto del recuerdo (<160 chars).
        value: contenido del recuerdo. Puede ser texto plano o JSON.
        importance: 0-100, sirve para poda futura (no obligatorio).
    """
    if not key or len(key) > _KEY_MAX_LEN:
        return f"FAIL: key inválida (vacía o >{_KEY_MAX_LEN} chars)"

    try:
        tid = UUID(tenant_id)
        eid = UUID(employee_id)
    except (TypeError, ValueError):
        return "FAIL: tenant_id o employee_id no son UUID válidos"

    try:
        value_json = json.loads(value)
    except (TypeError, ValueError):
        value_json = value  # se guarda como string en JSONB

    async with AsyncSessionLocal() as db:
        emp = await _employee_or_none(db, tid, eid)
        if emp is None:
            return "FAIL: empleado no existe"
        if not emp.memory_enabled:
            return (
                "FAIL: este empleado no tiene memoria habilitada. "
                "Activa 'memory_enabled' en su configuración para usarla."
            )

        is_pg = db.bind.dialect.name == "postgresql"
        if is_pg:
            stmt = (
                pg_insert(EmployeeMemory)
                .values(
                    tenant_id=tid,
                    employee_id=eid,
                    key=key,
                    value=value_json,
                    importance=max(0, min(100, int(importance))),
                )
                .on_conflict_do_update(
                    constraint="uq_employee_memory_employee_key",
                    set_=dict(value=value_json, importance=max(0, min(100, int(importance)))),
                )
            )
            await db.execute(stmt)
        else:
            existing = await db.execute(
                select(EmployeeMemory).where(
                    EmployeeMemory.employee_id == eid,
                    EmployeeMemory.key == key,
                )
            )
            row = existing.scalar_one_or_none()
            if row is None:
                db.add(
                    EmployeeMemory(
                        tenant_id=tid,
                        employee_id=eid,
                        key=key,
                        value=value_json,
                        importance=int(importance),
                    )
                )
            else:
                row.value = value_json
                row.importance = int(importance)
        await db.commit()
    return f"OK: recuerdo '{key}' guardado."


@tool
async def recall(tenant_id: str, employee_id: str, key: str) -> str:
    """Recupera un recuerdo concreto por su `key`.

    Devuelve el contenido como string. Si la clave no existe, devuelve
    'NOT_FOUND'.
    """
    try:
        tid = UUID(tenant_id)
        eid = UUID(employee_id)
    except (TypeError, ValueError):
        return "FAIL: tenant_id o employee_id no son UUID válidos"

    async with AsyncSessionLocal() as db:
        emp = await _employee_or_none(db, tid, eid)
        if emp is None:
            return "FAIL: empleado no existe"
        if not emp.memory_enabled:
            return "FAIL: este empleado no tiene memoria habilitada."

        res = await db.execute(
            select(EmployeeMemory).where(
                EmployeeMemory.employee_id == eid,
                EmployeeMemory.key == key,
            )
        )
        row = res.scalar_one_or_none()
    if row is None:
        return "NOT_FOUND"
    return json.dumps(row.value, ensure_ascii=False) if not isinstance(row.value, str) else row.value


@tool
async def recall_all(tenant_id: str, employee_id: str, limit: int = _RECALL_DEFAULT_LIMIT) -> str:
    """Lista los recuerdos del empleado (los más recientes primero).

    Devuelve un JSON con [{key, value, importance, updated_at}, …]. Útil
    para "qué recuerdas de mí" o al inicio de una conversación larga.
    """
    try:
        tid = UUID(tenant_id)
        eid = UUID(employee_id)
    except (TypeError, ValueError):
        return "FAIL: tenant_id o employee_id no son UUID válidos"

    limit = max(1, min(200, int(limit)))

    async with AsyncSessionLocal() as db:
        emp = await _employee_or_none(db, tid, eid)
        if emp is None:
            return "FAIL: empleado no existe"
        if not emp.memory_enabled:
            return "FAIL: este empleado no tiene memoria habilitada."

        res = await db.execute(
            select(EmployeeMemory)
            .where(EmployeeMemory.employee_id == eid)
            .order_by(EmployeeMemory.updated_at.desc())
            .limit(limit)
        )
        rows = res.scalars().all()

    payload = [
        {
            "key": r.key,
            "value": r.value,
            "importance": r.importance,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
        for r in rows
    ]
    return json.dumps(payload, ensure_ascii=False)
