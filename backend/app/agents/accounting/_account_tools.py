"""Herramientas de contabilidad para el agente de asientos y libro diario."""
import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import func, select

from app.db.base import AsyncSessionLocal
from app.db.models.accounting import BankTransaction, FixedAsset, JournalEntry, JournalLine

logger = logging.getLogger(__name__)


@tool
async def create_journal_entry(
    tenant_id: str,
    description: str,
    entry_date: str,
    lines: list[dict],
) -> str:
    """
    Crea un asiento contable manual en el libro diario.
    Cada línea debe tener: account_code (str), account_name (str), debit (float), credit (float).
    La suma de débitos debe ser igual a la suma de créditos.

    Args:
        tenant_id: ID del tenant
        description: Descripción del asiento
        entry_date: Fecha en formato YYYY-MM-DD
        lines: Lista de líneas con account_code, account_name, debit, credit
    """
    try:
        total_debit = sum(Decimal(str(l.get("debit", 0))) for l in lines)
        total_credit = sum(Decimal(str(l.get("credit", 0))) for l in lines)
        if abs(total_debit - total_credit) > Decimal("0.01"):
            return f"Error: El asiento no cuadra. Débitos: {total_debit}, Créditos: {total_credit}. Deben ser iguales."

        parsed_date = date.fromisoformat(entry_date)

        async with AsyncSessionLocal() as db:
            entry = JournalEntry(
                tenant_id=UUID(tenant_id),
                date=parsed_date,
                description=description,
            )
            db.add(entry)
            await db.flush()

            for l in lines:
                db.add(JournalLine(
                    tenant_id=UUID(tenant_id),
                    entry_id=entry.id,
                    account_code=str(l["account_code"]),
                    account_name=l.get("account_name", ""),
                    debit=Decimal(str(l.get("debit", 0))),
                    credit=Decimal(str(l.get("credit", 0))),
                ))

            await db.commit()
            return f"Asiento creado correctamente. ID: {entry.id}. Descripción: {description}. Fecha: {entry_date}. Importe: {total_debit:.2f}€."
    except Exception as e:
        logger.exception("Error creando asiento")
        return f"Error creando asiento: {e}"


@tool
async def list_journal_entries(
    tenant_id: str,
    date_from: str = "",
    date_to: str = "",
    account_code: str = "",
    limit: int = 20,
) -> str:
    """
    Lista asientos del libro diario. Permite filtrar por rango de fechas y cuenta contable.

    Args:
        tenant_id: ID del tenant
        date_from: Fecha inicio YYYY-MM-DD (opcional)
        date_to: Fecha fin YYYY-MM-DD (opcional)
        account_code: Código de cuenta PGC para filtrar (opcional)
        limit: Máximo de resultados (por defecto 20)
    """
    try:
        async with AsyncSessionLocal() as db:
            q = (
                select(JournalEntry)
                .where(JournalEntry.tenant_id == UUID(tenant_id))
                .order_by(JournalEntry.date.desc())
                .limit(min(limit, 50))
            )
            if date_from:
                q = q.where(JournalEntry.date >= date.fromisoformat(date_from))
            if date_to:
                q = q.where(JournalEntry.date <= date.fromisoformat(date_to))

            if account_code:
                entry_ids_q = select(JournalLine.entry_id).where(
                    JournalLine.tenant_id == UUID(tenant_id),
                    JournalLine.account_code == account_code,
                )
                q = q.where(JournalEntry.id.in_(entry_ids_q))

            result = await db.execute(q)
            entries = result.scalars().all()

            if not entries:
                return "No se encontraron asientos con los filtros indicados."

            lines_out = []
            for e in entries:
                lines_out.append(f"- [{e.date.strftime('%d/%m/%Y') if e.date else '?'}] {e.description} | ID: {e.id}")
            return f"Asientos encontrados ({len(entries)}):\n" + "\n".join(lines_out)
    except Exception as e:
        logger.exception("Error listando asientos")
        return f"Error listando asientos: {e}"


@tool
async def get_account_balance(
    tenant_id: str,
    account_code: str,
    date_to: str = "",
) -> str:
    """
    Calcula el saldo de una cuenta del Plan General Contable (PGC) acumulado hasta una fecha.

    Args:
        tenant_id: ID del tenant
        account_code: Código de cuenta (ej: "400", "430", "570")
        date_to: Fecha límite YYYY-MM-DD (opcional, por defecto hoy)
    """
    try:
        async with AsyncSessionLocal() as db:
            q = (
                select(
                    func.sum(JournalLine.debit).label("total_debit"),
                    func.sum(JournalLine.credit).label("total_credit"),
                )
                .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
                .where(
                    JournalLine.tenant_id == UUID(tenant_id),
                    JournalLine.account_code.startswith(account_code),
                )
            )
            if date_to:
                q = q.where(JournalEntry.date <= date.fromisoformat(date_to))

            result = await db.execute(q)
            row = result.one_or_none()

            total_debit = Decimal(str(row.total_debit or 0))
            total_credit = Decimal(str(row.total_credit or 0))
            balance = total_debit - total_credit

            return (
                f"Cuenta {account_code} — Saldo: {balance:.2f}€ "
                f"(Debe: {total_debit:.2f}€ | Haber: {total_credit:.2f}€)"
            )
    except Exception as e:
        logger.exception("Error calculando saldo")
        return f"Error calculando saldo de cuenta {account_code}: {e}"


@tool
async def get_profit_loss_summary(
    tenant_id: str,
    date_from: str,
    date_to: str,
) -> str:
    """
    Genera un resumen de Pérdidas y Ganancias para un período. Agrupa por cuentas 6xx (gastos) y 7xx (ingresos).

    Args:
        tenant_id: ID del tenant
        date_from: Fecha inicio YYYY-MM-DD
        date_to: Fecha fin YYYY-MM-DD
    """
    try:
        async with AsyncSessionLocal() as db:
            q = (
                select(
                    JournalLine.account_code,
                    JournalLine.account_name,
                    func.sum(JournalLine.debit).label("total_debit"),
                    func.sum(JournalLine.credit).label("total_credit"),
                )
                .join(JournalEntry, JournalLine.entry_id == JournalEntry.id)
                .where(
                    JournalLine.tenant_id == UUID(tenant_id),
                    JournalEntry.date >= date.fromisoformat(date_from),
                    JournalEntry.date <= date.fromisoformat(date_to),
                )
                .group_by(JournalLine.account_code, JournalLine.account_name)
                .order_by(JournalLine.account_code)
            )
            result = await db.execute(q)
            rows = result.all()

            if not rows:
                return f"No hay movimientos contables entre {date_from} y {date_to}."

            ingresos = []
            gastos = []
            total_ingresos = Decimal(0)
            total_gastos = Decimal(0)

            for row in rows:
                code = row.account_code or ""
                saldo = Decimal(str(row.total_credit or 0)) - Decimal(str(row.total_debit or 0))
                name = row.account_name or code
                if code.startswith("7"):
                    ingresos.append(f"  {code} {name}: {saldo:.2f}€")
                    total_ingresos += saldo
                elif code.startswith("6"):
                    gastos.append(f"  {code} {name}: {abs(saldo):.2f}€")
                    total_gastos += abs(saldo)

            resultado = total_ingresos - total_gastos
            signo = "BENEFICIO" if resultado >= 0 else "PÉRDIDA"

            parts = [f"Pérdidas y Ganancias ({date_from} → {date_to}):"]
            if ingresos:
                parts.append(f"\nINGRESOS ({total_ingresos:.2f}€):")
                parts.extend(ingresos)
            if gastos:
                parts.append(f"\nGASTOS ({total_gastos:.2f}€):")
                parts.extend(gastos)
            parts.append(f"\n{signo}: {abs(resultado):.2f}€")
            return "\n".join(parts)
    except Exception as e:
        logger.exception("Error generando PyG")
        return f"Error generando Pérdidas y Ganancias: {e}"


@tool
async def list_fixed_assets(tenant_id: str, status: str = "active") -> str:
    """
    Lista los activos fijos (inmovilizado) de la empresa.

    Args:
        tenant_id: ID del tenant
        status: Estado del activo (active, disposed, all). Por defecto: active.
    """
    try:
        async with AsyncSessionLocal() as db:
            q = select(FixedAsset).where(FixedAsset.tenant_id == UUID(tenant_id))
            if status != "all":
                q = q.where(FixedAsset.status == status)
            q = q.order_by(FixedAsset.purchase_date.desc()).limit(30)

            result = await db.execute(q)
            assets = result.scalars().all()

            if not assets:
                return "No hay activos fijos registrados."

            lines = []
            for a in assets:
                annual = a.purchase_value / a.useful_life_years if a.useful_life_years else 0
                lines.append(
                    f"- {a.name} | {a.category or 'Sin categoría'} | "
                    f"Valor: {a.purchase_value:.2f}€ | Amort.: {annual:.2f}€/año | "
                    f"Cuenta: {a.account_code or '?'} | Estado: {a.status}"
                )
            return f"Activos fijos ({len(assets)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listando activos fijos: {e}"
