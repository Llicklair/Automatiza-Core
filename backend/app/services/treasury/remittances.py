"""Remesas SEPA persistidas: creación, historial y ciclo de estados.

Ciclo de vida:
    generated → sent → executed → reconciled
    generated → cancelled   (una remesa nunca enviada puede descartarse)

La creación genera el XML (pain.001 o pain.008 vía `sepa.py`) y persiste
la remesa con sus órdenes en la misma transacción.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
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
    "generated": {"sent", "executed", "cancelled"},
    "cancelled": set(),
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


async def _assert_links_free(db: AsyncSession, tenant_id: uuid.UUID, links: list[dict] | None) -> None:
    """Rechaza la creación si alguna factura/nómina vinculada ya está en otra
    remesa viva (no cancelada): evita el doble pago/cobro cuando el usuario
    reintenta porque perdió el feedback de una generación anterior."""
    if not links:
        return
    invoice_ids = [ln["invoice_id"] for ln in links if ln and ln.get("invoice_id")]
    payroll_ids = [ln["payroll_id"] for ln in links if ln and ln.get("payroll_id")]
    conds = []
    if invoice_ids:
        conds.append(SepaRemittanceOrder.invoice_id.in_(invoice_ids))
    if payroll_ids:
        conds.append(SepaRemittanceOrder.payroll_id.in_(payroll_ids))
    if not conds:
        return
    msg_id = (
        await db.execute(
            select(SepaRemittance.msg_id)
            .join(SepaRemittanceOrder, SepaRemittanceOrder.remittance_id == SepaRemittance.id)
            .where(
                SepaRemittance.tenant_id == tenant_id,
                SepaRemittance.status != "cancelled",
                or_(*conds),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if msg_id:
        raise RemittanceError(
            f"Alguna factura o nómina de esta remesa ya está incluida en la remesa {msg_id}. "
            "Cancélala antes de volver a generar una remesa con los mismos elementos."
        )


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
    await _assert_links_free(db, tenant_id, links)
    _ensure_e2e(orders)
    xml_str, summary = build_pain001(debtor, execution_date, orders)
    return await _persist(
        db,
        tenant_id,
        "pain.001",
        xml_str,
        summary,
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
    await _assert_links_free(db, tenant_id, links)
    _ensure_e2e(orders)
    xml_str, summary = build_pain008(creditor, collection_date, orders)
    return await _persist(
        db,
        tenant_id,
        "pain.008",
        xml_str,
        summary,
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
    try:
        await db.flush()
    except IntegrityError as exc:
        # Red de seguridad de la barrera de BD (índice parcial único): dos
        # generaciones concurrentes pasaron el guard de aplicación y chocaron
        # aquí. Se convierte en el mismo error de negocio, no en un 500.
        raise RemittanceError(
            "Alguna factura o nómina de esta remesa ya está incluida en otra remesa viva. "
            "Cancélala antes de volver a generar una remesa con los mismos elementos."
        ) from exc
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
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        (await db.execute(base.order_by(SepaRemittance.created_at.desc()).limit(limit).offset(offset))).scalars().all()
    )
    return list(rows), total


async def get_remittance(db: AsyncSession, tenant_id: uuid.UUID, remittance_id: uuid.UUID) -> SepaRemittance | None:
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
        raise RemittanceError(f"Transición inválida: {remittance.status} → {new_status}.")
    remittance.status = new_status
    if new_status == "executed":
        remittance.executed_at = datetime.now(timezone.utc)
    if new_status == "cancelled":
        # Libera las facturas/nóminas de esta remesa del índice único parcial,
        # para que puedan incluirse en una remesa nueva (vía de escape del guard).
        await db.execute(
            update(SepaRemittanceOrder)
            .where(SepaRemittanceOrder.remittance_id == remittance_id)
            .values(is_cancelled=True)
        )
    if bank_transaction_id is not None:
        remittance.bank_transaction_id = bank_transaction_id
    await db.flush()
    return remittance
