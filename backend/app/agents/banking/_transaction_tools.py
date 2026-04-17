"""Banking agent — transaction listing and financial summary tools."""

import json
import logging
from datetime import date, timedelta

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from app.agents.banking._psd2_helpers import (
    ALERT_THRESHOLDS,
    _DEMO_TXS,
    _get_psd2_credentials,
)
from app.core.llm_factory import get_llm

logger = logging.getLogger(__name__)


def _get_llm():
    return get_llm(temperature=0)


def _get_llm_json():
    return get_llm(temperature=0, format_output="json")


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

    from app.agents.banking._account_tools import _check_balances_async
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
