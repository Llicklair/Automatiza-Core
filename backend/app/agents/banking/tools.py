"""
Banking agent tools — all @tool decorated functions.
"""

import json
import logging
from datetime import date, timedelta

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.core.llm_factory import get_llm

logger = logging.getLogger(__name__)

ALERT_THRESHOLDS = {
    "cargo_inusual_eur": 5_000,
    "saldo_minimo_eur": 1_000,
}

# Datos demo cuando PSD2 no está configurado
_DEMO_SALDOS = [
    {
        "account_id": "demo_001",
        "iban": "ES91 2100 0418 4502 0005 1332",
        "nombre": "Cuenta Corriente (Demo)",
        "saldo": 18450.72,
        "moneda": "EUR",
    },
    {
        "account_id": "demo_002",
        "iban": "ES80 2310 0001 1800 0001 2345",
        "nombre": "Cuenta Ahorro (Demo)",
        "saldo": 5200.00,
        "moneda": "EUR",
    },
]
_DEMO_TXS = [
    {
        "id": "1",
        "fecha": "2026-03-15",
        "concepto": "TRANSFERENCIA RECIBIDA ACME SL",
        "importe": 4500,
        "tipo": "abono",
        "categoria": "cliente_cobro",
    },
    {
        "id": "2",
        "fecha": "2026-03-14",
        "concepto": "AMAZON WEB SERVICES",
        "importe": -350,
        "tipo": "cargo",
        "categoria": "proveedor_servicio",
    },
    {
        "id": "3",
        "fecha": "2026-03-13",
        "concepto": "NOMINAS MARZO 2026",
        "importe": -12000,
        "tipo": "cargo",
        "categoria": "nominas",
    },
    {
        "id": "4",
        "fecha": "2026-03-12",
        "concepto": "ENGIE ENERGIA FACTURA",
        "importe": -280.50,
        "tipo": "cargo",
        "categoria": "suministros",
    },
    {
        "id": "5",
        "fecha": "2026-03-11",
        "concepto": "COBRO FACTURA #2026-041",
        "importe": 7200,
        "tipo": "abono",
        "categoria": "cliente_cobro",
    },
    {
        "id": "6",
        "fecha": "2026-03-10",
        "concepto": "CUOTA PRESTAMO BANCO",
        "importe": -1100,
        "tipo": "cargo",
        "categoria": "financiero",
    },
]


def _get_llm():
    return get_llm(temperature=0)


def _get_llm_json():
    return get_llm(temperature=0, format_output="json")


async def _get_psd2_credentials(tenant_id: str) -> dict | None:
    """Obtiene credenciales PSD2 del tenant si están configuradas."""
    import uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantIntegration
    from app.services.encryption import decrypt_credentials

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantIntegration).where(
                    TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                    TenantIntegration.integration_type == "psd2",
                    TenantIntegration.is_active.is_(True),
                )
            )
            integration = result.scalars().first()
            if not integration:
                return None
            creds = decrypt_credentials(integration.encrypted_credentials)
            if not creds.get("secret_id") or not creds.get("secret_key"):
                return None
            return creds
    except Exception as e:
        logger.error("Error obteniendo credenciales PSD2 para tenant %s: %s", tenant_id, e)
        return None


# ─── Herramientas del agente ──────────────────────────────────────────────────


@tool
async def check_balances(tenant_id: str) -> str:
    """
    Consulta los saldos actuales de las cuentas bancarias vinculadas.
    Si el banco no está conectado (PSD2), muestra datos de demo.

    Args:
        tenant_id: ID del tenant
    """
    return await _check_balances_async(tenant_id)


async def _check_balances_async(tenant_id: str) -> str:
    creds = await _get_psd2_credentials(tenant_id)

    if not creds:
        lines = [f"- {s['nombre']}: {s['saldo']:.2f}€ ({s['iban']})" for s in _DEMO_SALDOS]
        return (
            "⚠️ Banco no conectado — mostrando datos de demo.\n\n"
            "Saldos:\n"
            + "\n".join(lines)
            + "\n\nConecta tu banco desde Integraciones → PSD2 para ver datos reales."
        )

    from app.integrations.psd2 import NordigenClient

    client = NordigenClient(secret_id=creds["secret_id"], secret_key=creds["secret_key"])
    saldos = []
    alertas = []

    try:
        await client._get_access_token()
        for acc_id in creds.get("account_ids", []):
            try:
                details = await client.get_account_details(acc_id)
                balances = await client.get_account_balances(acc_id)
                saldo_disp = next(
                    (b for b in balances if b.get("balanceType") == "interimAvailable"),
                    balances[0] if balances else {},
                )
                importe = float(saldo_disp.get("balanceAmount", {}).get("amount", 0))
                saldos.append(
                    f"- {details.get('name', 'Cuenta')} ({details.get('iban', '')}): {importe:.2f}€"
                )
                if importe < ALERT_THRESHOLDS["saldo_minimo_eur"]:
                    alertas.append(f"⚠️ Saldo bajo: {importe:.2f}€ en {details.get('iban', acc_id)}")
            except Exception as e:
                saldos.append(f"- Cuenta {acc_id}: Error ({e})")
    finally:
        await client.close()

    result = "Saldos bancarios:\n" + "\n".join(saldos)
    if alertas:
        result += "\n\nAlertas:\n" + "\n".join(alertas)
    return result


@tool
async def list_transactions(tenant_id: str, days_back: int = 30) -> str:
    """
    Lista las transacciones bancarias del período indicado con categorización automática.
    Si el banco no está conectado, muestra datos de demo.

    Args:
        tenant_id: ID del tenant
        days_back: Días hacia atrás para buscar transacciones (por defecto 30)
    """
    return await _list_transactions_async(tenant_id, days_back)


async def _list_transactions_async(tenant_id: str, days_back: int) -> str:
    creds = await _get_psd2_credentials(tenant_id)

    if not creds:
        lines = [
            f"- {t['fecha']}: {t['concepto']} | {t['importe']:+.2f}€ [{t['categoria']}]"
            for t in _DEMO_TXS
        ]
        return (
            "⚠️ Banco no conectado — datos de demo.\n\n"
            f"Transacciones (últimos {days_back} días):\n" + "\n".join(lines)
        )

    from app.integrations.psd2 import NordigenClient

    client = NordigenClient(secret_id=creds["secret_id"], secret_key=creds["secret_key"])
    todas_tx = []
    alertas = []

    try:
        await client._get_access_token()
        date_from = date.today() - timedelta(days=days_back)

        for acc_id in creds.get("account_ids", []):
            try:
                raw = await client.get_transactions(acc_id, date_from=date_from)
                normalized = NordigenClient.normalize_transactions(raw)
                todas_tx.extend(normalized)

                for tx in normalized:
                    if (
                        tx["tipo"] == "cargo"
                        and abs(tx["importe"]) > ALERT_THRESHOLDS["cargo_inusual_eur"]
                    ):
                        alertas.append(
                            f"🔴 Cargo inusual: {abs(tx['importe']):.2f}€ — {tx['concepto']}"
                        )
            except Exception as e:
                todas_tx.append({"concepto": f"Error en cuenta {acc_id}: {e}", "importe": 0})
    finally:
        await client.close()

    if not todas_tx:
        return f"No hay transacciones en los últimos {days_back} días."

    # Categorizar con LLM
    llm = _get_llm_json()
    sample = todas_tx[:50]
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content="""Clasifica cada transacción en una categoría:
proveedor_material, proveedor_servicio, nominas, impuestos, alquiler,
suministros, financiero, cliente_cobro, transferencia_interna, otros.
Devuelve JSON: [{"id": "...", "categoria": "...", "confianza": 0.9}, ...]"""
                ),
                HumanMessage(
                    content=f"Transacciones:\n{json.dumps([{'id': t['id'], 'concepto': t['concepto'], 'importe': t['importe']} for t in sample], ensure_ascii=False)}"
                ),
            ]
        )
        cats = json.loads(response.content)
        cats = cats if isinstance(cats, list) else cats.get("categorias", [])
        cat_map = {c["id"]: c.get("categoria", "otros") for c in cats}
        for tx in todas_tx:
            tx["categoria"] = cat_map.get(tx["id"], "otros")
    except Exception as e:
        logger.warning("Error clasificando transacciones con LLM: %s. Usando categoría 'otros'.", e)
        for tx in todas_tx:
            tx["categoria"] = "otros"

    lines = [
        f"- {t.get('fecha', 'N/A')}: {t['concepto']} | {t['importe']:+.2f}€ [{t.get('categoria', 'otros')}]"
        for t in todas_tx[:30]
    ]
    result = f"Transacciones (últimos {days_back} días, {len(todas_tx)} total):\n" + "\n".join(
        lines
    )
    if alertas:
        result += "\n\nAlertas:\n" + "\n".join(alertas)
    return result


@tool
async def financial_summary(tenant_id: str, days_back: int = 30) -> str:
    """
    Genera un resumen financiero del período: ingresos, gastos por categoría,
    resultado neto y recomendaciones. Combina saldos + transacciones.

    Args:
        tenant_id: ID del tenant
        days_back: Días del período a analizar (por defecto 30)
    """
    return await _financial_summary_async(tenant_id, days_back)


async def _financial_summary_async(tenant_id: str, days_back: int) -> str:
    creds = await _get_psd2_credentials(tenant_id)

    if not creds:
        ingresos = sum(t["importe"] for t in _DEMO_TXS if t["importe"] > 0)
        gastos = sum(abs(t["importe"]) for t in _DEMO_TXS if t["importe"] < 0)
        return (
            f"⚠️ Banco no conectado — resumen con datos de demo.\n\n"
            f"Período: últimos {days_back} días\n"
            f"Ingresos: +{ingresos:.2f}€\n"
            f"Gastos: -{gastos:.2f}€\n"
            f"Resultado neto: {ingresos - gastos:+.2f}€\n\n"
            "Conecta tu banco desde Integraciones → PSD2 para análisis real."
        )

    tx_text = await _list_transactions_async(tenant_id, days_back)
    balance_text = await _check_balances_async(tenant_id)

    llm = _get_llm()
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(
                    content="""Eres un contable experto en PYMEs españolas.
Analiza los datos financieros y redacta un resumen claro para el empresario.
Incluye: ingresos/gastos principales, tendencias, y recomendación concreta.
Máximo 200 palabras. NO inventes datos."""
                ),
                HumanMessage(content=f"Saldos:\n{balance_text}\n\nTransacciones:\n{tx_text}"),
            ]
        )
        return response.content
    except Exception as e:
        logger.warning(
            "Error generando resumen financiero con LLM: %s. Devolviendo datos sin procesar.", e
        )
        return f"Datos disponibles:\n\n{balance_text}\n\n{tx_text}"


@tool
async def reconcile_transactions(
    tenant_id: str, tolerance_days: int = 3, tolerance_amount: float = 0.01
) -> str:
    """
    Concilia automáticamente transacciones bancarias con facturas pendientes/pagadas.
    Cruza movimientos de ingreso con facturas pending/paid por importe y fecha (±tolerancia).
    Marca como conciliadas las coincidencias encontradas.

    Args:
        tenant_id: ID del tenant
        tolerance_days: Días de tolerancia entre fecha de transacción y fecha de factura (por defecto 3)
        tolerance_amount: Tolerancia en euros para considerar coincidencia de importe (por defecto 0.01)
    """
    return await _reconcile_transactions_async(tenant_id, tolerance_days, tolerance_amount)


async def _reconcile_transactions_async(
    tenant_id: str,
    tolerance_days: int,
    tolerance_amount: float,
) -> str:
    from uuid import UUID

    from sqlalchemy import or_, select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Client, Invoice

    try:
        creds = await _get_psd2_credentials(tenant_id)
        if creds:
            from app.integrations.psd2 import PSD2Client

            psd2 = PSD2Client(creds["secret_id"], creds["secret_key"])
            accounts = psd2.get_accounts()
            transactions = []
            for acc in accounts:
                transactions.extend(psd2.get_transactions(acc["id"], days=90))
        else:
            today = date.today()
            transactions = [
                {
                    "amount": 2420.00,
                    "date": (today - timedelta(days=5)).isoformat(),
                    "description": "Transferencia recibida - Acme Corp",
                    "type": "credit",
                },
                {
                    "amount": 1815.00,
                    "date": (today - timedelta(days=12)).isoformat(),
                    "description": "Transferencia recibida - López SL",
                    "type": "credit",
                },
                {
                    "amount": 3630.00,
                    "date": (today - timedelta(days=20)).isoformat(),
                    "description": "Transferencia recibida",
                    "type": "credit",
                },
                {
                    "amount": 605.00,
                    "date": (today - timedelta(days=2)).isoformat(),
                    "description": "Bizum recibido",
                    "type": "credit",
                },
                {
                    "amount": -850.00,
                    "date": (today - timedelta(days=8)).isoformat(),
                    "description": "Pago proveedor",
                    "type": "debit",
                },
                {
                    "amount": -1200.00,
                    "date": (today - timedelta(days=15)).isoformat(),
                    "description": "Alquiler oficina",
                    "type": "debit",
                },
            ]

        ingresos = [t for t in transactions if float(t.get("amount", 0)) > 0]

        if not ingresos:
            return "No se encontraron transacciones de ingreso para conciliar."

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Invoice, Client)
                .join(Client)
                .where(
                    Invoice.tenant_id == UUID(tenant_id),
                    or_(Invoice.status == "pending", Invoice.status == "paid"),
                )
            )
            invoices = result.all()

            if not invoices:
                return "No hay facturas pendientes o pagadas para conciliar."

            matched = []
            unmatched_txns = []

            for txn in ingresos:
                txn_amount = float(txn["amount"])
                txn_date = date.fromisoformat(txn["date"][:10]) if txn.get("date") else date.today()
                found = False

                for inv, cli in invoices:
                    inv_total = float(inv.amount_total)
                    inv_date = inv.date.date() if hasattr(inv.date, "date") else inv.date

                    amount_match = abs(txn_amount - inv_total) <= tolerance_amount
                    date_match = abs((txn_date - inv_date).days) <= tolerance_days

                    if amount_match and date_match:
                        if inv.status == "pending":
                            inv.status = "paid"
                        matched.append(
                            {
                                "invoice": inv.invoice_number,
                                "client": cli.name,
                                "amount": txn_amount,
                                "txn_desc": txn.get("description", ""),
                            }
                        )
                        found = True
                        break

                if not found:
                    unmatched_txns.append(
                        {
                            "amount": txn_amount,
                            "date": txn.get("date", "?")[:10],
                            "description": txn.get("description", ""),
                        }
                    )

            await db.commit()

        lines = []
        if matched:
            lines.append(f"CONCILIADOS ({len(matched)}):")
            for m in matched:
                lines.append(
                    f"  - {m['invoice']} ({m['client']}): {m['amount']:.2f}€ ← {m['txn_desc']}"
                )

        if unmatched_txns:
            lines.append(f"\nSIN CONCILIAR ({len(unmatched_txns)}):")
            for u in unmatched_txns:
                lines.append(f"  - {u['date']}: +{u['amount']:.2f}€ — {u['description']}")

        total_conciliado = sum(m["amount"] for m in matched)
        total_pendiente = sum(u["amount"] for u in unmatched_txns)

        lines.append(
            f"\nResumen: {len(matched)} conciliados ({total_conciliado:.2f}€), "
            f"{len(unmatched_txns)} sin conciliar ({total_pendiente:.2f}€)."
        )

        return "\n".join(lines)
    except Exception as e:
        return f"Error en conciliación: {e}"


# ─── Lista de herramientas ────────────────────────────────────────────────────

tools = [
    check_balances,
    list_transactions,
    financial_summary,
    reconcile_transactions,
    create_document,
    list_tenant_documents,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]
