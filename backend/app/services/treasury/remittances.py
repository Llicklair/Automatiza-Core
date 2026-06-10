"""Remesas SEPA persistidas: creación, historial y ciclo de estados.

Ciclo de vida:
    generated → sent → executed → reconciled

La creación genera el XML (pain.001 o pain.008 vía `sepa.py`) y persiste
la remesa con sus órdenes en la misma transacción.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.treasury import SepaRemittance, SepaRemittanceOrder
from app.services.treasury.sepa import (
    CreditorParty,
    DebtorParty,
    DirectDebitOrder,
    TransferOrder,
    build_pain001,
    build_pain008,
)

# Transiciones de estado permitidas
_TRANSITIONS: dict[str, set[str]] = {
    "generated": {"sent", "executed"},
    "sent": {"executed"},
    "executed": {"reconciled"},
    "reconciled": set(),
}


class RemittanceError(ValueError):
    """Error de negocio en la gestión de remesas."""


def _ensure_e2e(orders: list) -> None:
    """Autogenera end_to_end_id en los orders que no lo traigan, para que
    lo persistido coincida con lo emitido en el XML."""
    for o in orders:
        if not o.end_to_end_id:
            o.end_to_end_id = f"E2E-{uuid.uuid4().hex[:16].upper()}"


async def create_transfer_remittance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    debtor: DebtorParty,
    execution_date: date,
    orders: list[TransferOrder],
    *,
    links: list[dict] | None = None,
) -> SepaRemittance:
    """Genera pain.001 y persiste la remesa (status `generated`).

    `links` (opcional, alineado por índice con `orders`) permite asociar
    cada orden a su origen: {"invoice_id": ..., "payroll_id": ...}.
    """
    _ensure_e2e(orders)
    xml_str, summary = build_pain001(debtor, execution_date, orders)
    return await _persist(
        db, tenant_id, "pain.001", xml_str, summary,
        party_iban=summary["debtor_iban"],
        execution_date=execution_date,
        orders=[
            {
                "counterparty_name": o.creditor_name,
                "counterparty_iban": o.creditor_iban,
                "amount": o.amount_eur,
                "concept": o.concept,
                "end_to_end_id": o.end_to_end_id,
            }
            for o in orders
        ],
        links=links,
    )


async def create_direct_debit_remittance(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    creditor: CreditorParty,
    collection_date: date,
    orders: list[DirectDebitOrder],
    *,
    links: list[dict] | None = None,
) -> SepaRemittance:
    """Genera pain.008 (adeudos CORE) y persiste la remesa."""
    _ensure_e2e(orders)
    xml_str, summary = build_pain008(creditor, collection_date, orders)
    return await _persist(
        db, tenant_id, "pain.008", xml_str, summary,
        party_iban=summary["creditor_iban"],
        execution_date=collection_date,
        orders=[
            {
                "counterparty_name": o.debtor_name,
                "counterparty_iban": o.debtor_iban,
                "amount": o.amount_eur,
                "concept": o.concept,
                "end_to_end_id": o.end_to_end_id,
                "mandate_id": o.mandate_id,
                "mandate_date": o.mandate_date,
                "sequence_type": o.sequence_type,
            }
            for o in orders
        ],
        links=links,
    )


async def _persist(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    remittance_type: str,
    xml_str: str,
    summary: dict,
    *,
    party_iban: str,
    execution_date: date,
    orders: list[dict],
    links: list[dict] | None,
) -> SepaRemittance:
    remittance = SepaRemittance(
        tenant_id=tenant_id,
        remittance_type=remittance_type,
        msg_id=summary["msg_id"],
        status="generated",
        execution_date=execution_date,
        party_iban=party_iban,
        nb_of_txs=summary["nb_of_txs"],
        total_amount=summary["control_sum_eur"],
        xml=xml_str,
        sha256=summary["sha256"],
    )
    for i, o in enumerate(orders):
        link = (links[i] if links and i < len(links) else None) or {}
        remittance.orders.append(
            SepaRemittanceOrder(
                **o,
                invoice_id=link.get("invoice_id"),
                payroll_id=link.get("payroll_id"),
            )
        )
    db.add(remittance)
    await db.flush()
    return remittance


async def list_remittances(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SepaRemittance], int]:
    """Historial de remesas del tenant, más recientes primero."""
    base = select(SepaRemittance).where(SepaRemittance.tenant_id == tenant_id)
    if status:
        base = base.where(SepaRemittance.status == status)
    total = (
        await db.execute(
            select(func.count()).select_from(base.subquery())
        )
    ).scalar_one()
    rows = (
        await db.execute(
            base.order_by(SepaRemittance.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return list(rows), total


async def get_remittance(
    db: AsyncSession, tenant_id: uuid.UUID, remittance_id: uuid.UUID
) -> SepaRemittance | None:
    return (
        await db.execute(
            select(SepaRemittance).where(
                SepaRemittance.id == remittance_id,
                SepaRemittance.tenant_id == tenant_id,
            )
        )
    ).scalar_one_or_none()


async def update_remittance_status(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    remittance_id: uuid.UUID,
    new_status: str,
    *,
    bank_transaction_id: uuid.UUID | None = None,
) -> SepaRemittance:
    """Avanza el estado de la remesa validando la transición.

    - `executed`: registra `executed_at`.
    - `reconciled`: permite asociar el movimiento bancario que la liquida.
    """
    remittance = await get_remittance(db, tenant_id, remittance_id)
    if remittance is None:
        raise RemittanceError("Remesa no encontrada.")
    allowed = _TRANSITIONS.get(remittance.status, set())
    if new_status not in allowed:
        raise RemittanceError(
            f"Transición inválida: {remittance.status} → {new_status}."
        )
    remittance.status = new_status
    if new_status == "executed":
        remittance.executed_at = datetime.now(timezone.utc)
    if bank_transaction_id is not None:
        remittance.bank_transaction_id = bank_transaction_id
    await db.flush()
    return remittance
