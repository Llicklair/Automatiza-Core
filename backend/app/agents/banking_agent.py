"""
Agente bancario — Fase 3.

Funciones:
  1. Obtener saldo actual de las cuentas vinculadas
  2. Listar y clasificar transacciones del período (LLM)
  3. Detectar pagos pendientes de facturas (conciliación)
  4. Alertar sobre movimientos inusuales (determinista por umbrales)
  5. Generar resumen financiero del mes
"""
import json
from datetime import date, timedelta

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field

from app.core.config import settings

# ─── Umbrales deterministas (sin LLM) ────────────────────────────────────────

ALERT_THRESHOLDS = {
    "cargo_inusual_eur": 5_000,    # Cargo > 5000€ → alerta
    "saldo_minimo_eur":  1_000,    # Saldo < 1000€ → alerta
    "multiple_cargos":       5,    # Más de 5 cargos en 1 día → revisión
}


# ─── Prompt para clasificación de transacciones ───────────────────────────────

CATEGORIZATION_PROMPT = """Eres un contable experto en PYMEs españolas.

Clasifica cada transacción bancaria en UNA de estas categorías:
- proveedor_material: Compras a proveedores de materiales/productos
- proveedor_servicio: Compras de servicios (software, marketing, consultoría)
- nominas: Pagos de nóminas a empleados
- impuestos: Pagos a AEAT, SS, tributos
- alquiler: Alquiler oficinas/almacenes
- suministros: Luz, agua, gas, telefonía, internet
- financiero: Cuotas préstamos, intereses, comisiones bancarias
- cliente_cobro: Cobros de clientes
- transferencia_interna: Entre tus propias cuentas
- otros: No clasificable

REGLAS:
1. Clasifica SOLO según el concepto y los nombres proporcionados. NO inventes.
2. Si el concepto está vacío, clasifica como "otros".
3. Devuelve ÚNICAMENTE JSON: [{"id": "...", "categoria": "...", "confianza": 0.9}, ...]"""


def _get_llm():
    return ChatOllama(
        model="llama3.2",
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0,
        format="json",
    )


# ─── Resultado del agente ─────────────────────────────────────────────────────

class BankingAgentResult(BaseModel):
    success: bool
    action: str  # "saldos" | "transacciones" | "resumen" | "alertas"
    saldos: list[dict] = Field(default_factory=list)
    transacciones: list[dict] = Field(default_factory=list)
    alertas: list[str] = Field(default_factory=list)
    resumen_financiero: str | None = None
    error: str | None = None


# ─── Función principal ────────────────────────────────────────────────────────

async def run_banking_agent(
    user_intent: str,
    tenant_id: str | None = None,
    nordigen_secret_id: str | None = None,
    nordigen_secret_key: str | None = None,
    account_ids: list[str] | None = None,
    days_back: int = 30,
) -> BankingAgentResult:
    """Ejecuta el agente bancario según la intención del usuario."""

    if not nordigen_secret_id or not nordigen_secret_key:
        # Sin PSD2 configurado → devolver datos de demo realistas
        intent_lower = user_intent.lower()
        
        demo_txs = [
            {"id": "1", "fecha": "2026-02-22", "concepto": "TRANSFERENCIA RECIBIDA ACME SL", "importe": 4500, "tipo": "abono", "categoria": "cliente_cobro"},
            {"id": "2", "fecha": "2026-02-21", "concepto": "AMAZON WEB SERVICES", "importe": -350, "tipo": "cargo", "categoria": "proveedor_servicio"},
            {"id": "3", "fecha": "2026-02-20", "concepto": "NOMINAS FEBRERO 2026", "importe": -12000, "tipo": "cargo", "categoria": "nominas"},
            {"id": "4", "fecha": "2026-02-19", "concepto": "ENGIE ENERGIA FACTURA", "importe": -280.50, "tipo": "cargo", "categoria": "suministros"},
            {"id": "5", "fecha": "2026-02-18", "concepto": "HOLDED PLAN PRO MENSUAL", "importe": -99, "tipo": "cargo", "categoria": "proveedor_servicio"},
            {"id": "6", "fecha": "2026-02-17", "concepto": "COBRO FACTURA #2026-041", "importe": 7200, "tipo": "abono", "categoria": "cliente_cobro"},
            {"id": "7", "fecha": "2026-02-15", "concepto": "CUOTA PRESTAMO BANCO", "importe": -1100, "tipo": "cargo", "categoria": "financiero"},
        ]

        if any(kw in intent_lower for kw in ["resumen", "informe", "análisis", "mes"]):
            return BankingAgentResult(
                success=True,
                action="resumen",
                saldos=[
                    {"account_id": "demo_001", "iban": "ES91 2100 0418 4502 0005 1332", "nombre": "Cuenta Corriente (Demo)", "saldo": 18450.72, "moneda": "EUR"},
                    {"account_id": "demo_002", "iban": "ES80 2310 0001 1800 0001 2345", "nombre": "Cuenta Ahr Reservas (Demo)", "saldo": 5200.00, "moneda": "EUR"},
                ],
                transacciones=demo_txs,
                resumen_financiero=(
                    "📅 Resumen de los últimos 30 días (datos de demo):\n\n"
                    "• Ingresos totales: +18.500€ (cobros de clientes y ventas)\n"
                    "• Gastos estructurados: -12.730€ (nóminas, proveedores, suministros)\n"
                    "• Resultado neto del mes: +5.770€\n\n"
                    "Recomendación: El mes cierra en positivo. El principal gasto son las nóminas "
                    "(55% del total de gastos). Considera revisar los contratos con proveedores de servicios "
                    "para optimizar el margen.\n\n"
                    "⚠️ Conecta tu banco real desde la sección de Integraciones para ver datos reales."
                ),
                alertas=["🟡 Banco no conectado: mostrando datos de demo. Ve a Integraciones → Conectar banco."],
            )
        else:
            action_type = "transacciones" if any(kw in intent_lower for kw in ["transacción", "movimiento", "cobro", "pago", "cargo"]) else "saldos"
            return BankingAgentResult(
                success=True,
                action=action_type,
                saldos=[
                    {"account_id": "demo_001", "iban": "ES91 2100 0418 4502 0005 1332", "nombre": "Cuenta Corriente (Demo)", "saldo": 18450.72, "moneda": "EUR"},
                    {"account_id": "demo_002", "iban": "ES80 2310 0001 1800 0001 2345", "nombre": "Cuenta Ahr Reservas (Demo)", "saldo": 5200.00, "moneda": "EUR"},
                ],
                transacciones=demo_txs if action_type == "transacciones" else [],
                alertas=["🟡 Banco no conectado: mostrando datos de demo. Ve a Integraciones → Conectar banco."],
            )

    intent_lower = user_intent.lower()

    if any(kw in intent_lower for kw in ["saldo", "balance", "cuánto tengo", "disponible"]):
        return await _accion_saldos(nordigen_secret_id, nordigen_secret_key, account_ids or [])

    elif any(kw in intent_lower for kw in ["transacción", "movimiento", "cobro", "pago", "cargo"]):
        return await _accion_transacciones(
            nordigen_secret_id, nordigen_secret_key, account_ids or [], days_back
        )

    elif any(kw in intent_lower for kw in ["resumen", "informe", "análisis", "mes"]):
        return await _accion_resumen(
            nordigen_secret_id, nordigen_secret_key, account_ids or [], days_back
        )

    else:
        return await _accion_saldos(nordigen_secret_id, nordigen_secret_key, account_ids or [])


async def _accion_saldos(secret_id: str, secret_key: str, account_ids: list[str]) -> BankingAgentResult:
    """Obtiene saldos de todas las cuentas vinculadas."""
    from app.integrations.psd2 import NordigenClient
    client = NordigenClient(secret_id=secret_id, secret_key=secret_key)
    saldos = []
    alertas = []

    try:
        await client._get_access_token()
        for acc_id in account_ids:
            try:
                details  = await client.get_account_details(acc_id)
                balances = await client.get_account_balances(acc_id)
                saldo_disponible = next(
                    (b for b in balances if b.get("balanceType") == "interimAvailable"),
                    balances[0] if balances else {}
                )
                importe = float(saldo_disponible.get("balanceAmount", {}).get("amount", 0))
                saldos.append({
                    "account_id": acc_id,
                    "iban":       details.get("iban", ""),
                    "nombre":     details.get("name", "Cuenta"),
                    "saldo":      importe,
                    "moneda":     saldo_disponible.get("balanceAmount", {}).get("currency", "EUR"),
                })
                # Alerta si saldo bajo
                if importe < ALERT_THRESHOLDS["saldo_minimo_eur"]:
                    alertas.append(
                        f"⚠️ Saldo bajo en cuenta {details.get('iban', acc_id)}: {importe:.2f}€"
                    )
            except Exception as e:
                saldos.append({"account_id": acc_id, "error": str(e)})
    finally:
        await client.close()

    return BankingAgentResult(success=True, action="saldos", saldos=saldos, alertas=alertas)


async def _accion_transacciones(
    secret_id: str, secret_key: str, account_ids: list[str], days_back: int
) -> BankingAgentResult:
    """Obtiene y categoriza transacciones del período."""
    from app.integrations.psd2 import NordigenClient
    client = NordigenClient(secret_id=secret_id, secret_key=secret_key)
    todas_tx = []
    alertas  = []

    try:
        await client._get_access_token()
        date_from = date.today() - timedelta(days=days_back)

        for acc_id in account_ids:
            try:
                raw = await client.get_transactions(acc_id, date_from=date_from)
                normalized = NordigenClient.normalize_transactions(raw)
                todas_tx.extend(normalized)

                # Alertas deterministas por umbrales
                for tx in normalized:
                    if tx["tipo"] == "cargo" and abs(tx["importe"]) > ALERT_THRESHOLDS["cargo_inusual_eur"]:
                        alertas.append(
                            f"🔴 Cargo inusual: {abs(tx['importe']):.2f}€ en {tx['fecha']} — {tx['concepto']}"
                        )
            except Exception as e:
                todas_tx.append({"error": str(e), "account_id": acc_id})
    finally:
        await client.close()

    if not todas_tx or todas_tx[0].get("error"):
        return BankingAgentResult(
            success=True, action="transacciones",
            transacciones=todas_tx, alertas=alertas
        )

    if secret_id == "DEMO_PSD2_ID":
        categorias_raw = [
            {"id": "tx_1", "categoria": "alquiler", "confianza": 0.99},
            {"id": "tx_2", "categoria": "cliente_cobro", "confianza": 0.99},
            {"id": "tx_3", "categoria": "suministros", "confianza": 0.99}
        ]
        cat_map = {c["id"]: c for c in categorias_raw}
        for tx in todas_tx:
            cat_info = cat_map.get(tx["id"], {})
            tx["categoria"]  = cat_info.get("categoria", "otros")
            tx["confianza"]  = cat_info.get("confianza", 0.5)
    else:
        # Categorización con LLM (máx 50 transacciones para no saturar contexto)
        llm = _get_llm()
        sample = todas_tx[:50]
        tx_for_llm = [{"id": tx["id"], "concepto": tx["concepto"],
                       "acreedor": tx["acreedor"], "deudor": tx["deudor"],
                       "importe": tx["importe"]} for tx in sample]
    
        try:
            response = await llm.ainvoke([
                SystemMessage(content=CATEGORIZATION_PROMPT),
                HumanMessage(content=f"Transacciones:\n{json.dumps(tx_for_llm, ensure_ascii=False)}"),
            ])
            categorias_raw = json.loads(response.content)
            # Puede devolver {"categorias": [...]} o directamente [...]
            categorias = categorias_raw if isinstance(categorias_raw, list) else categorias_raw.get("categorias", [])
            cat_map = {c["id"]: c for c in categorias}
    
            for tx in todas_tx:
                cat_info = cat_map.get(tx["id"], {})
                tx["categoria"]  = cat_info.get("categoria", "otros")
                tx["confianza"]  = cat_info.get("confianza", 0.5)
        except Exception:
            for tx in todas_tx:
                tx["categoria"] = "otros"
                tx["confianza"] = 0.0

    return BankingAgentResult(
        success=True, action="transacciones",
        transacciones=todas_tx, alertas=alertas
    )


async def _accion_resumen(
    secret_id: str, secret_key: str, account_ids: list[str], days_back: int
) -> BankingAgentResult:
    """Genera un resumen financiero del período con LLM."""
    # Primero obtener transacciones categorizadas
    tx_result = await _accion_transacciones(secret_id, secret_key, account_ids, days_back)
    saldo_result = await _accion_saldos(secret_id, secret_key, account_ids)

    txs = tx_result.transacciones
    if not txs:
        return BankingAgentResult(
            success=True, action="resumen",
            resumen_financiero="No hay transacciones en el período seleccionado.",
            saldos=saldo_result.saldos,
        )

    # Agregar por categoría (determinista)
    from collections import defaultdict
    by_cat: dict = defaultdict(lambda: {"total": 0.0, "count": 0})
    for tx in txs:
        cat = tx.get("categoria", "otros")
        by_cat[cat]["total"] += tx["importe"]
        by_cat[cat]["count"] += 1

    ingresos = sum(v["total"] for v in by_cat.values() if v["total"] > 0)
    gastos   = sum(abs(v["total"]) for v in by_cat.values() if v["total"] < 0)

    resumen_datos = {
        "periodo_dias": days_back,
        "total_transacciones": len(txs),
        "ingresos_eur": round(ingresos, 2),
        "gastos_eur": round(gastos, 2),
        "resultado_neto": round(ingresos - gastos, 2),
        "por_categoria": {cat: {"total": round(v["total"], 2), "operaciones": v["count"]}
                          for cat, v in by_cat.items()},
    }

    if secret_id == "DEMO_PSD2_ID":
        resumen_texto = (
            f"El período analizado de los últimos {days_back} días muestra unos ingresos de {ingresos:.2f}€ "
            f"y unos gastos estructurados de {abs(gastos):.2f}€. El resultado neto es positivo en {(ingresos - gastos):.2f}€. "
            "Se observa un buen control en gastos fijos como el alquiler de la oficina y cobros importantes realizados con éxito."
        )
    else:
        # Redactar resumen con LLM
        llm = _get_llm()
        try:
            response = await llm.ainvoke([
                SystemMessage(content="""Eres un contable experto en PYMEs españolas.
    Analiza los datos financieros proporcionados y redacta un resumen claro y útil para el empresario.
    Incluye: ingresos/gastos principales, tendencias destacables, y recomendación concreta.
    Máximo 200 palabras. NO inventes datos que no estén en el JSON."""),
                HumanMessage(content=f"Datos financieros:\n{json.dumps(resumen_datos, ensure_ascii=False)}"),
            ])
            resumen_texto = response.content
        except Exception:
            resumen_texto = (
                f"Período: últimos {days_back} días.\n"
                f"Ingresos: {ingresos:.2f}€ | Gastos: {gastos:.2f}€ | "
                f"Resultado neto: {(ingresos - gastos):.2f}€"
            )

    return BankingAgentResult(
        success=True, action="resumen",
        transacciones=txs,
        saldos=saldo_result.saldos,
        alertas=tx_result.alertas + saldo_result.alertas,
        resumen_financiero=resumen_texto,
    )
