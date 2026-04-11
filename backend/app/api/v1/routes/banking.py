from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Invoice, User
from app.middleware.rate_limit import limiter

router = APIRouter(tags=["banking"])


@router.get("/summary")
@limiter.limit("20/minute")
async def get_banking_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene el resumen financiero del tenant basado en las facturas registradas localmente."""

    # Obtener todas las facturas del tenant
    query = select(Invoice).where(Invoice.tenant_id == current_user.tenant_id)
    result = await db.execute(query)
    invoices = result.scalars().all()

    ingresos = sum(float(inv.amount_total) for inv in invoices if inv.invoice_type == "issued")
    gastos = sum(float(inv.amount_total) for inv in invoices if inv.invoice_type == "received")

    neto = ingresos - gastos
    margen = round((neto / ingresos) * 100) if ingresos > 0 else 0

    # Si no hay facturas, devolvemos un flag is_demo=True para que el frontend lo sepa
    if not invoices:
        return {"ingresos": 0, "gastos": 0, "neto": 0, "margen": 0, "is_demo": False}

    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "neto": neto,
        "margen": margen,
        "is_demo": False,
    }


import random
import uuid
from datetime import date, timedelta

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc

from app.db.models.models import BankTransaction
from app.services.event_bus import emit_event


# --- Schemas ---
class TransactionReconcile(BaseModel):
    invoice_id: str


class BankTransactionResponse(BaseModel):
    id: uuid.UUID
    date: date
    description: str
    amount: float
    balance: float | None = None
    status: str
    invoice_id: uuid.UUID | None = None

    model_config = ConfigDict(from_attributes=True)


# --- Routes ---
@router.get("/transactions", response_model=list[BankTransactionResponse])
@limiter.limit("20/minute")
async def list_transactions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(BankTransaction)
        .where(BankTransaction.tenant_id == current_user.tenant_id)
        .order_by(desc(BankTransaction.date))
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/transactions/sync")
@limiter.limit("20/minute")
async def sync_bank_transactions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera movimientos demo simulando conexión PSD2 por Plaid/Nordigen"""
    descriptions = [
        "Recibo Luz Gesternova",
        "Abono Cliente STRIPE",
        "Cuota Seguridad Social",
        "Transferencia recibida F. Perez",
        "Pago Suministros",
    ]
    today = date.today()

    balance = 14500.00
    for i in range(5):
        day_offset = random.randint(0, 15)
        amount = random.uniform(-500, 1500)
        balance += amount
        tx = BankTransaction(
            tenant_id=current_user.tenant_id,
            date=today - timedelta(days=day_offset),
            description=random.choice(descriptions),
            amount=round(amount, 2),
            balance=round(balance, 2),
            status="unreconciled",
        )
        db.add(tx)

    await db.commit()
    await emit_event(db, current_user.tenant_id, current_user.id, "banking_synced", {"count": 5})
    return {"message": "Sincronizado correctamente", "status": "ok"}


@router.post("/transactions/{tx_id}/reconcile")
@limiter.limit("20/minute")
async def reconcile_transaction(
    request: Request,
    tx_id: uuid.UUID,
    payload: TransactionReconcile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Concilia el movimiento contra una factura"""
    result = await db.execute(
        select(BankTransaction).where(
            BankTransaction.id == tx_id, BankTransaction.tenant_id == current_user.tenant_id
        )
    )
    tx = result.scalars().first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaccion no encontrada")

    result_inv = await db.execute(
        select(Invoice).where(
            Invoice.id == uuid.UUID(payload.invoice_id), Invoice.tenant_id == current_user.tenant_id
        )
    )
    invoice = result_inv.scalars().first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    # Vincular transacción con factura
    tx.invoice_id = invoice.id
    tx.status = "reconciled"

    # ── State machine: valida la transición antes de marcar como pagada ──
    from app.services.state_machine import can_transition

    if can_transition("Invoice", invoice.status, "paid"):
        invoice.status = "paid"
    elif invoice.status == "paid":
        pass  # Ya estaba pagada — idempotente
    else:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede marcar como pagada una factura en estado '{invoice.status}'. "
            f"Emitela primero antes de conciliarla.",
        )

    await db.commit()
    await emit_event(
        db,
        current_user.tenant_id,
        current_user.id,
        "invoice_paid",
        {"invoice_number": invoice.invoice_number, "tx_id": str(tx.id)},
    )
    return {"message": "Conciliado correctamente", "status": "ok"}


@router.get("/analytics")
@limiter.limit("20/minute")
async def get_banking_analytics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve datos preprocesados de cashflow y consejos IA para la Home Page."""

    # Simulación de un proceso analítico que extraería datos de 6 meses
    # Y generaría insights de IA mediante embeddings o reglas lógicas.
    cashflow_data = [
        {"month": "Sep", "ingresos": 14200, "gastos": 8500},
        {"month": "Oct", "ingresos": 18500, "gastos": 9200},
        {"month": "Nov", "ingresos": 16100, "gastos": 10500},
        {"month": "Dic", "ingresos": 21000, "gastos": 12100},
        {"month": "Ene", "ingresos": 19400, "gastos": 11000},
        {"month": "Feb", "ingresos": 22300, "gastos": 10200},
    ]

    ai_insights = [
        {
            "id": "1",
            "type": "success",
            "title": "Crecimiento sostenido detectado",
            "message": "Los ingresos del Q1 muestran un incremento del 18% frente al mes anterior, impulsado por nuevos clientes de software.",
            "action_text": "Ver informes",
            "action_url": "/banca",
        },
        {
            "id": "2",
            "type": "warning",
            "title": "3 facturas a punto de vencer",
            "message": "Tienes 3 facturas emitidas por un valor total de 4.250€ que vencen esta semana y no están conciliadas.",
            "action_text": "Revisar facturas",
            "action_url": "/ventas/facturas",
        },
        {
            "id": "3",
            "type": "info",
            "title": "Eficiencia en gastos",
            "message": "En comparación con tu sector, tus gastos recurrentes (servicios/cloud) están un 5% optimizados. ¡Buen trabajo!",
            "action_text": "Analizar costes",
            "action_url": "/tesoreria/pagos-y-cobros",
        },
    ]

    return {"cashflow": cashflow_data, "insights": ai_insights}
