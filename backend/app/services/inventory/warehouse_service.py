"""Gestión de almacenes/tiendas (multi-almacén, capa 1).

No lanza HTTPException — solo excepciones Python o valores de retorno.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inventory import Warehouse


def _wh_dict(w: Warehouse) -> dict:
    return {
        "id": str(w.id),
        "name": w.name,
        "code": w.code,
        "address": w.address,
        "is_default": bool(w.is_default),
        "is_active": bool(w.is_active),
    }


async def list_warehouses(db: AsyncSession, tenant_id: UUID) -> list[dict]:
    result = await db.execute(
        select(Warehouse)
        .where(Warehouse.tenant_id == tenant_id)
        .order_by(Warehouse.is_default.desc(), Warehouse.name.asc())
    )
    return [_wh_dict(w) for w in result.scalars().all()]


async def get_default_id(db: AsyncSession, tenant_id: UUID) -> UUID:
    """ID del almacén por defecto. Si no existe ninguno, crea 'Principal'."""
    result = await db.execute(
        select(Warehouse.id).where(Warehouse.tenant_id == tenant_id, Warehouse.is_default.is_(True)).limit(1)
    )
    wid = result.scalars().first()
    if wid:
        return wid
    result = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tenant_id).limit(1))
    existing = result.scalars().first()
    if existing:
        return existing.id
    warehouse = Warehouse(tenant_id=tenant_id, name="Principal", is_default=True, is_active=True)
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return warehouse.id


async def _unset_defaults(db: AsyncSession, tenant_id: UUID) -> None:
    result = await db.execute(select(Warehouse).where(Warehouse.tenant_id == tenant_id, Warehouse.is_default.is_(True)))
    for w in result.scalars().all():
        w.is_default = False


async def create_warehouse(db: AsyncSession, tenant_id: UUID, data: dict) -> dict:
    make_default = bool(data.get("is_default"))
    if make_default:
        await _unset_defaults(db, tenant_id)
    warehouse = Warehouse(
        tenant_id=tenant_id,
        name=data["name"],
        code=data.get("code"),
        address=data.get("address"),
        is_default=make_default,
        is_active=data.get("is_active", True),
    )
    db.add(warehouse)
    await db.commit()
    await db.refresh(warehouse)
    return _wh_dict(warehouse)


async def update_warehouse(db: AsyncSession, tenant_id: UUID, warehouse_id: UUID, fields: dict) -> dict:
    result = await db.execute(select(Warehouse).where(Warehouse.id == warehouse_id, Warehouse.tenant_id == tenant_id))
    warehouse = result.scalars().first()
    if warehouse is None:
        raise LookupError(f"Almacén {warehouse_id} no encontrado")

    if fields.get("is_default") is True and not warehouse.is_default:
        await _unset_defaults(db, tenant_id)
        warehouse.is_default = True
    for key in ("name", "code", "address", "is_active"):
        if key in fields and fields[key] is not None:
            setattr(warehouse, key, fields[key])

    await db.commit()
    await db.refresh(warehouse)
    return _wh_dict(warehouse)
