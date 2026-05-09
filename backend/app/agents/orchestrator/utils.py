"""
Utilidades del orquestador: formateo de resúmenes y extracción de fechas.
"""

import re
from datetime import datetime, timedelta


def _format_summary(agent: str, output: dict, success: bool, error: str | None = None) -> str:
    """Convierte el output de un agente en una frase legible para el usuario."""
    if not success:
        return f"❌ {error or 'Error desconocido en el agente.'}"

    if agent == "billing":
        action = output.get("action", "")
        data = output.get("extracted_data") or {}
        if action == "approval_required":
            return "⏳ Pendiente de aprobación antes de procesar la factura."
        if action == "draft_created":
            num = data.get("invoice_number", "")
            client = data.get("client", data.get("client_name", ""))
            total = data.get("total", data.get("amount_total", ""))
            parts = ["✅ Factura creada"]
            if num:
                parts.append(f"**{num}**")
            if client:
                parts.append(f"para {client}")
            if total:
                parts.append(f"por {total}€")
            return " ".join(parts) + "."
        if action == "summary":
            response = (output.get("response") or "").strip()
            if response:
                first_line = response.split("\n", 1)[0].strip() or response
                return f"📊 {first_line[:200]}{'…' if len(first_line) > 200 else ''}"
            return "📊 Consulta de facturación completada."
        return f"✅ Facturación: {action}."

    if agent in ("hr", "crm", "email"):
        action = output.get("action", "")
        if action:
            return action if action.startswith(("✅", "❌", "📊", "⚠️")) else f"✅ {action}"
        return "✅ Operación completada."

    if agent == "documents":
        doc_type = output.get("document_type", "documento")
        requires_review = output.get("requires_review", False)
        msg = f"✅ Documento '{doc_type}' procesado."
        if requires_review:
            msg += " ⚠️ Requiere revisión manual."
        return msg

    if agent == "compliance":
        respuesta = output.get("respuesta_consulta", "")
        alertas = output.get("alertas") or []
        vencimientos = output.get("vencimientos") or []
        if respuesta:
            return f"✅ {respuesta}"
        parts = []
        if alertas:
            parts.append(f"⚠️ {len(alertas)} alerta(s): {'; '.join(str(a) for a in alertas[:2])}")
        if vencimientos:
            parts.append(f"📅 Vencimientos próximos: {'; '.join(str(v) for v in vencimientos[:2])}")
        return " | ".join(parts) if parts else "✅ Análisis fiscal completado."

    if agent == "banking":
        resumen = output.get("resumen_financiero", "")
        saldos = output.get("saldos") or []
        if resumen:
            return f"✅ {resumen}"
        if saldos:
            saldo_txt = ", ".join(
                f"{s.get('nombre', 'Cuenta')}: {s.get('saldo', '?')}€" for s in saldos[:3]
            )
            return f"✅ Saldos bancarios: {saldo_txt}."
        return "✅ Consulta bancaria completada."

    if agent == "rag":
        answer = output.get("answer", "")
        if answer:
            return f"✅ {answer[:300]}{'...' if len(answer) > 300 else ''}"
        return "✅ Consulta documental completada."

    if agent == "excel":
        return f"✅ {output.get('summary', output.get('action', 'Análisis Excel completado.'))}"

    return f"✅ Agente '{agent}' completado."


# ─── Utilidad: extraer mes y año de lenguaje natural ─────────────────────────

_MESES_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
    # abreviaturas comunes
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def _extract_month_year(intent: str) -> tuple[int, int]:
    """Extrae (mes, año) de un texto en lenguaje natural español.

    Maneja:
    - Nombres de mes: "marzo", "enero 2025", "el pasado octubre"
    - Relativos: "mes pasado", "mes anterior", "mes que viene", "próximo mes"
    - Numérico ISO: "2026-03", "2026/03"
    - Numérico directo: "03/2026", "3/2026", "mes 3"
    - Sin contexto: devuelve mes actual
    """
    now = datetime.now()
    text = intent.lower()

    # Relativos primero
    if re.search(r"mes\s+(pasado|anterior)", text):
        d = now.replace(day=1) - timedelta(days=1)
        return d.month, d.year
    if re.search(
        r"(próximo|siguiente|que\s+viene)\s+mes|mes\s+(próximo|siguiente|que\s+viene)", text
    ):
        d = now.replace(day=28) + timedelta(days=4)
        return d.month, d.year

    # Formato ISO: 2026-03 o 2026/03
    m = re.search(r"\b(20\d{2})[/-](\d{1,2})\b", text)
    if m:
        return int(m.group(2)), int(m.group(1))

    # Formato DD/MM/YYYY o MM/YYYY
    m = re.search(r"\b(\d{1,2})[/-](20\d{2})\b", text)
    if m:
        return int(m.group(1)), int(m.group(2))

    # Nombre de mes (con año opcional)
    for nombre, num in _MESES_ES.items():
        if re.search(rf"\b{nombre}\b", text):
            year_m = re.search(r"\b(20\d{2})\b", text)
            year = int(year_m.group(1)) if year_m else now.year
            return num, year

    # "mes N" numérico
    m = re.search(r"\bmes\s+(\d{1,2})\b", text)
    if m:
        month = int(m.group(1))
        if 1 <= month <= 12:
            year_m = re.search(r"\b(20\d{2})\b", text)
            year = int(year_m.group(1)) if year_m else now.year
            return month, year

    # Año solo → mes actual de ese año
    m = re.search(r"\b(20\d{2})\b", text)
    if m:
        return now.month, int(m.group(1))

    # Por defecto: mes actual
    return now.month, now.year
