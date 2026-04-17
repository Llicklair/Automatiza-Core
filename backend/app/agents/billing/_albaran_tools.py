"""
Delivery note (albarán) tools for the billing agent.
"""

import json
import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import desc, select

from app.db.base import AsyncSessionLocal
from app.db.models.billing import DeliveryNote, DeliveryNoteLine

from ._client_tools import _resolve_client

logger = logging.getLogger(__name__)


@tool
async def list_albaranes(tenant_id: str, status: str = "") -> str:
    """
    Lista los albaranes del tenant. Opcionalmente filtra por status: draft, confirmed, delivered.

    Args:
        tenant_id: ID del tenant
        status: Filtro de estado (vacío = todos)
    """
    try:
        async with AsyncSessionLocal() as db:
            q = select(DeliveryNote).where(DeliveryNote.tenant_id == UUID(tenant_id))
            if status:
                q = q.where(DeliveryNote.status == status)
            q = q.order_by(desc(DeliveryNote.created_at)).limit(20)
            result = await db.execute(q)
            notes = result.scalars().all()
            if not notes:
                return "No hay albaranes registrados."
            lines = [
                f"- {n.albaran_number} | {n.date} | {n.status} | {float(n.amount_total):.2f}€"
                for n in notes
            ]
            return "Albaranes:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listando albaranes: {e}"


@tool
async def create_albaran(
    tenant_id: str,
    client_name: str,
    lines_json: str,
    albaran_date: str = "",
    notes: str = "",
) -> str:
    """
    Crea un albarán de entrega.

    Args:
        tenant_id: ID del tenant
        client_name: Nombre del cliente
        lines_json: JSON string con lista de líneas, cada una con: description, quantity, unit_price, tax_percentage
        albaran_date: Fecha del albarán en formato YYYY-MM-DD (opcional, hoy por defecto)
        notes: Observaciones opcionales
    """
    try:
        lines_data = json.loads(lines_json)
        entry_date = date.fromisoformat(albaran_date) if albaran_date else date.today()

        client_result = await _resolve_client(tenant_id, client_name)
        if isinstance(client_result, str):
            return client_result
        client_id, _resolved_name, _resolved_nif = client_result

        async with AsyncSessionLocal() as db:
            last_result = await db.execute(
                select(DeliveryNote)
                .where(DeliveryNote.tenant_id == UUID(tenant_id))
                .order_by(desc(DeliveryNote.created_at))
                .limit(1)
            )
            last = last_result.scalar_one_or_none()
            try:
                num = int(last.albaran_number.split("-")[-1]) + 1 if last and last.albaran_number else 1
            except (ValueError, IndexError):
                num = 1
            albaran_number = f"ALB-{num:05d}"

            amount_base = Decimal("0")
            tax_amount = Decimal("0")
            for line in lines_data:
                base = Decimal(str(line.get("quantity", 1))) * Decimal(str(line.get("unit_price", 0)))
                tax_amount += base * Decimal(str(line.get("tax_percentage", 21))) / Decimal("100")
                amount_base += base
            amount_total = amount_base + tax_amount

            note = DeliveryNote(
                tenant_id=UUID(tenant_id), client_id=client_id,
                albaran_number=albaran_number, date=entry_date,
                notes=notes or None, amount_base=amount_base,
                tax_amount=tax_amount, amount_total=amount_total,
            )
            db.add(note)
            await db.flush()

            for line in lines_data:
                base = Decimal(str(line.get("quantity", 1))) * Decimal(str(line.get("unit_price", 0)))
                total = base + base * Decimal(str(line.get("tax_percentage", 21))) / Decimal("100")
                db.add(DeliveryNoteLine(
                    albaran_id=note.id,
                    description=line.get("description", ""),
                    quantity=line.get("quantity", 1),
                    unit_price=line.get("unit_price", 0),
                    tax_percentage=line.get("tax_percentage", 21),
                    total=total,
                ))

            await db.commit()
            return (
                f"Albarán {albaran_number} creado correctamente para {client_name or 'sin cliente'}. "
                f"Total: {float(amount_total):.2f}€"
            )
    except Exception as e:
        return f"Error creando albarán: {e}"
