"""AI-powered executive summaries with deterministic fallback.

Extracted from api/v1/routes/reports/_helpers.py.
"""

import asyncio
import logging

# Cota dura para el resumen por IA dentro del request del snapshot. El cliente
# LLM trae timeout de 30 s, demasiado para un GET: si el proveedor no responde
# (típico en BYOK sin clave) o va lento, cortamos y devolvemos el determinista
# —que es instantáneo— en vez de bloquear la página varios segundos.
_RESUMEN_LLM_TIMEOUT_S = 8.0

from app.services.reports._schemas import (
    FiscalIRPF,
    FiscalIS,
    FiscalIVA,
    SnapshotSectionBanking,
    SnapshotSectionHR,
    SnapshotSectionInvoices,
)

_logger = logging.getLogger(__name__)


def _build_deterministic_resumen(
    month_str,
    ingresos,
    gastos,
    margen,
    margen_pct,
    fact_section,
    hr_section,
    bank_section,
    coste_nominas,
    total_clients,
    new_clients,
    top_client_name,
    top_amount,
) -> str:
    tendencia = "positiva" if margen > 0 else "negativa" if margen < 0 else "neutra"
    resumen = (
        f"El mes {month_str} presenta una tendencia {tendencia}. "
        f"La empresa facturo {ingresos:,.2f} € en ingresos con un margen bruto del {margen_pct:.1f}%. "
    )
    if fact_section.facturas_pendientes_cobro > 0:
        resumen += (
            f"Quedan {fact_section.facturas_pendientes_cobro} facturas pendientes de cobro "
            f"por un importe de {fact_section.importe_pendiente_cobro:,.2f} €. "
        )
    if hr_section.empleados_activos > 0:
        resumen += (
            f"La plantilla activa es de {hr_section.empleados_activos} empleados "
            f"con un coste de nominas de {coste_nominas:,.2f} €. "
        )
    if bank_section.transacciones > 0:
        resumen += f"Se registraron {bank_section.transacciones} movimientos bancarios. "
    if new_clients > 0:
        resumen += f"Se captaron {new_clients} clientes nuevos (total: {total_clients}). "
    if top_client_name:
        resumen += f"El cliente principal fue {top_client_name} ({top_amount:,.2f} €)."
    return resumen.strip()


async def generate_resumen_ejecutivo(
    month_str,
    ingresos,
    gastos,
    margen,
    margen_pct,
    fact_section: SnapshotSectionInvoices,
    hr_section: SnapshotSectionHR,
    bank_section: SnapshotSectionBanking,
    coste_nominas,
    total_clients,
    new_clients,
    top_client_name,
    top_amount,
) -> str:
    """Genera resumen ejecutivo con IA. Si falla, usa determinista."""
    deterministic = _build_deterministic_resumen(
        month_str,
        ingresos,
        gastos,
        margen,
        margen_pct,
        fact_section,
        hr_section,
        bank_section,
        coste_nominas,
        total_clients,
        new_clients,
        top_client_name,
        top_amount,
    )

    try:
        from app.core.llm_factory import get_llm

        llm = get_llm(temperature=0.3, max_tokens=600)

        prompt = (
            "Eres el director financiero de una PYME española. "
            "Redacta un resumen ejecutivo de 3-5 frases del mes para el CEO, "
            "en tono profesional pero accesible. Incluye tendencia, riesgos y recomendaciones. "
            "No inventes datos, usa SOLO los proporcionados.\n\n"
            f"MES: {month_str}\n"
            f"INGRESOS: {ingresos:,.2f} €  |  GASTOS: {gastos:,.2f} €  |  MARGEN: {margen:,.2f} € ({margen_pct:.1f}%)\n"
            f"FACTURAS EMITIDAS: {fact_section.facturas_emitidas}  |  RECIBIDAS: {fact_section.facturas_recibidas}\n"
            f"PENDIENTES COBRO: {fact_section.facturas_pendientes_cobro} facturas ({fact_section.importe_pendiente_cobro:,.2f} €)\n"
            f"EMPLEADOS: {hr_section.empleados_activos}  |  NOMINAS: {coste_nominas:,.2f} €\n"
            f"MOVIMIENTOS BANCARIOS: {bank_section.transacciones}  |  SALDO NETO: {bank_section.saldo_neto:,.2f} €\n"
            f"CLIENTES: {total_clients} (nuevos: {new_clients})"
            + (f"  |  TOP: {top_client_name} ({top_amount:,.2f} €)" if top_client_name else "")
            + "\n\nResponde SOLO el texto del resumen, sin encabezados ni formato."
        )

        from langchain_core.messages import HumanMessage

        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content=prompt)]), timeout=_RESUMEN_LLM_TIMEOUT_S
        )
        ai_resumen = response.content.strip()

        if len(ai_resumen) > 50:
            _logger.info("[REPORTS] Resumen ejecutivo generado por IA")
            return ai_resumen

    except (Exception, asyncio.TimeoutError) as e:
        _logger.warning("[REPORTS] IA no disponible para resumen, usando determinista: %s", e)

    return deterministic


async def generate_resumen_fiscal(
    period: str, label: str, iva: FiscalIVA, irpf: FiscalIRPF, is_: FiscalIS
) -> str:
    """Resumen ejecutivo fiscal con IA, fallback determinista."""
    resultado_iva = iva.resultado_iva
    estado_iva = (
        "a ingresar"
        if resultado_iva > 0
        else "a compensar/devolver"
        if resultado_iva < 0
        else "neutro"
    )

    deterministic = (
        f"Periodo {label}: IVA repercutido {iva.total_repercutido:,.2f} € vs soportado {iva.total_soportado:,.2f} €, "
        f"resultado {estado_iva} de {abs(resultado_iva):,.2f} €. "
        f"Retenciones IRPF: {irpf.total_retenciones:,.2f} €. "
        f"Estimacion IS: base imponible {is_.base_imponible:,.2f} €, cuota estimada {is_.cuota_estimada:,.2f} € (tipo {is_.tipo_estimado:.0f}%)."
    )

    try:
        from app.core.llm_factory import get_llm

        llm = get_llm(temperature=0.3, max_tokens=600)

        prompt = (
            "Eres el asesor fiscal de una PYME española. "
            "Redacta un resumen fiscal de 3-5 frases para el CEO, "
            "en tono profesional. Incluye obligaciones fiscales proximas, riesgos y recomendaciones. "
            "No inventes datos, usa SOLO los proporcionados.\n\n"
            f"PERIODO: {label}\n"
            f"IVA REPERCUTIDO: {iva.total_repercutido:,.2f} € (base: {iva.base_repercutido:,.2f} €)\n"
            f"IVA SOPORTADO: {iva.total_soportado:,.2f} € (base: {iva.base_soportado:,.2f} €)\n"
            f"RESULTADO IVA: {resultado_iva:,.2f} € ({estado_iva})\n"
            f"IRPF RETENCIONES NOMINAS: {irpf.retenciones_nominas:,.2f} €\n"
            f"IS — INGRESOS: {is_.ingresos_brutos:,.2f} €  |  GASTOS DEDUCIBLES: {is_.gastos_deducibles:,.2f} €\n"
            f"IS — BASE IMPONIBLE: {is_.base_imponible:,.2f} €  |  CUOTA ESTIMADA: {is_.cuota_estimada:,.2f} €\n"
            "\nResponde SOLO el texto del resumen, sin encabezados ni formato."
        )

        from langchain_core.messages import HumanMessage

        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content=prompt)]), timeout=_RESUMEN_LLM_TIMEOUT_S
        )
        ai_resumen = response.content.strip()
        if len(ai_resumen) > 50:
            return ai_resumen
    except (Exception, asyncio.TimeoutError) as e:
        _logger.warning("[REPORTS] IA no disponible para resumen fiscal: %s", e)

    return deterministic
