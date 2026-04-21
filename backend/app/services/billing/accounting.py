"""Accounting service — business logic for journal entries and fixed assets."""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.models import FixedAsset, JournalEntry, JournalLine

# ─── Journal Entries ──────────────────────────────────────────────────────────


async def list_journal_entries(db: AsyncSession, tenant_id: UUID) -> list[JournalEntry]:
    query = (
        select(JournalEntry)
        .where(JournalEntry.tenant_id == tenant_id)
        .options(selectinload(JournalEntry.lines))
        .order_by(desc(JournalEntry.date))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_journal_entry(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    date,
    description: str,
    reference_id: str | None,
    lines: list[dict],
) -> JournalEntry:
    total_debit = sum(line["debit"] for line in lines)
    total_credit = sum(line["credit"] for line in lines)

    if abs(total_debit - total_credit) > 0.01:
        raise ValueError(
            f"El asiento está descuadrado: Debe ({total_debit}) != Haber ({total_credit})"
        )

    new_entry = JournalEntry(
        tenant_id=tenant_id,
        date=date,
        description=description,
        reference_id=reference_id,
    )
    db.add(new_entry)
    await db.flush()

    for line_data in lines:
        new_line = JournalLine(
            tenant_id=tenant_id,
            entry_id=new_entry.id,
            account_code=line_data["account_code"],
            account_name=line_data.get("account_name"),
            debit=line_data["debit"],
            credit=line_data["credit"],
        )
        db.add(new_line)

    await db.commit()
    await db.refresh(new_entry)

    stmt = (
        select(JournalEntry)
        .where(JournalEntry.id == new_entry.id)
        .options(selectinload(JournalEntry.lines))
    )
    res = await db.execute(stmt)
    return res.scalar_one()


async def delete_journal_entry(db: AsyncSession, tenant_id: UUID, entry_id: UUID) -> None:
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id, JournalEntry.tenant_id == tenant_id
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise LookupError("Asiento no encontrado")
    await db.delete(entry)
    await db.commit()


# ─── Fixed Assets ─────────────────────────────────────────────────────────────


async def list_fixed_assets(db: AsyncSession, tenant_id: UUID) -> list[FixedAsset]:
    result = await db.execute(
        select(FixedAsset)
        .where(FixedAsset.tenant_id == tenant_id)
        .order_by(desc(FixedAsset.created_at))
    )
    return list(result.scalars().all())


async def create_fixed_asset(
    db: AsyncSession, tenant_id: UUID, data: dict
) -> FixedAsset:
    asset = FixedAsset(tenant_id=tenant_id, **data)
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def update_fixed_asset(
    db: AsyncSession, tenant_id: UUID, asset_id: UUID, data: dict
) -> FixedAsset:
    result = await db.execute(
        select(FixedAsset).where(
            FixedAsset.id == asset_id, FixedAsset.tenant_id == tenant_id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise LookupError("Activo no encontrado")
    for field, value in data.items():
        setattr(asset, field, value)
    await db.commit()
    await db.refresh(asset)
    return asset


async def delete_fixed_asset(db: AsyncSession, tenant_id: UUID, asset_id: UUID) -> None:
    result = await db.execute(
        select(FixedAsset).where(
            FixedAsset.id == asset_id, FixedAsset.tenant_id == tenant_id
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise LookupError("Activo no encontrado")
    await db.delete(asset)
    await db.commit()
