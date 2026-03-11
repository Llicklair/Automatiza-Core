"""
Scraper del BOE (Boletín Oficial del Estado) para actualizaciones regulatorias.
Usa el feed RSS oficial + la API REST del BOE cuando está disponible.
Fuente RSS: https://www.boe.es/rss/
API REST BOE: https://boe.es/datosabiertos/api/
"""
import xml.etree.ElementTree as ET
from datetime import date

import httpx

BOE_RSS_BASE   = "https://www.boe.es/rss"
BOE_API_BASE   = "https://boe.es/datosabiertos/api"

# Secciones de interés para PYMEs
SECCIONES_INTERES = {
    "fiscal":   "https://www.boe.es/rss/canal.php?c=ayudas",    # Hacienda/Tributos
    "laboral":  "https://www.boe.es/rss/canal.php?c=empleo",    # Trabajo
    "mercantil":"https://www.boe.es/rss/canal.php?c=empresas",    # Sociedades
}

# Palabras clave fiscales relevantes para PYMEs
KEYWORDS_PYME = [
    "pyme", "autónomo", "iva", "irpf", "sociedades", "modelo 303",
    "modelo 130", "modelo 111", "modelo 347", "factura electrónica",
    "facturae", "sii", "aplazamiento", "fraccionamiento", "declaración",
    "retención", "rendimiento", "actividad económica",
]


class BOEScraper:
    """Scraper async del BOE para obtener novedades regulatorias."""

    def __init__(self):
        self._client = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": "AutomatizaPyme-BOE/1.0 (contacto@automatizapyme.es)"},
        )

    async def close(self):
        await self._client.aclose()

    async def get_novedades(self, seccion: str = "fiscal", max_items: int = 10) -> list[dict]:
        """
        Obtiene las últimas entradas del RSS del BOE para una sección.
        Filtra por palabras clave relevantes para PYMEs.
        """
        url = SECCIONES_INTERES.get(seccion, SECCIONES_INTERES["fiscal"])
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()
            return self._parse_rss(resp.text, max_items=max_items)
        except Exception as exc:
            return [{"error": str(exc), "seccion": seccion}]

    async def get_norma(self, identificador: str) -> dict:
        """
        Obtiene el texto completo de una norma por su identificador BOE.
        Ej: identificador = "BOE-A-2024-12345"
        """
        url = f"{BOE_API_BASE}/norma/{identificador}"
        try:
            resp = await self._client.get(url, headers={"Accept": "application/json"})
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"error": str(exc)}

    def _parse_rss(self, xml_text: str, max_items: int = 10) -> list[dict]:
        """Parsea el XML del RSS del BOE y devuelve lista de items normalizados."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        items = []
        ns = {"dc": "http://purl.org/dc/elements/1.1/"}

        for item in root.findall(".//item")[:max_items * 3]:  # coge más para filtrar
            title       = (item.findtext("title") or "").strip()
            description = (item.findtext("description") or "").strip()
            link        = (item.findtext("link") or "").strip()
            pub_date    = (item.findtext("pubDate") or "").strip()
            identifier  = (item.findtext("dc:identifier", namespaces=ns) or "").strip()

            text_lower = f"{title} {description}".lower()
            is_relevant = any(kw in text_lower for kw in KEYWORDS_PYME)

            items.append({
                "identificador": identifier,
                "titulo":        title,
                "descripcion":   description[:500],
                "url":           link,
                "fecha":         pub_date,
                "relevante_pyme":is_relevant,
            })

            if len([i for i in items if i["relevante_pyme"]]) >= max_items:
                break

        return items


# ─── Calendario fiscal AEAT (datos estáticos + lógica de fechas) ─────────────

def get_calendario_fiscal(year: int) -> list[dict]:
    """
    Devuelve el calendario fiscal de una PYME española para el año dado.
    Datos basados en la normativa vigente. Actualizar anualmente si cambia.
    """
    eventos = []

    # Modelo 303 — Liquidación trimestral IVA
    trimestres_303 = [
        ("1T", f"{year}-01-01", f"{year}-03-31", f"{year}-04-20"),
        ("2T", f"{year}-04-01", f"{year}-06-30", f"{year}-07-20"),
        ("3T", f"{year}-07-01", f"{year}-09-30", f"{year}-10-20"),
        ("4T", f"{year}-10-01", f"{year}-12-31", f"{year+1}-01-30"),
    ]
    for trimestre, inicio, fin, limite in trimestres_303:
        eventos.append({
            "modelo":      "303",
            "nombre":      f"IVA {trimestre} {year}",
            "descripcion": f"Autoliquidación IVA {trimestre}. Período: {inicio} a {fin}",
            "fecha_limite":limite,
            "periodo":     trimestre,
            "tipo":        "iva",
            "urgente_dias":15,  # Alertar 15 días antes
        })

    # Modelo 130 — IRPF Estimación Directa (Fraccionado trimestral)
    trimestres_130 = [
        ("1T", f"{year}-01-01", f"{year}-03-31", f"{year}-04-20"),
        ("2T", f"{year}-01-01", f"{year}-06-30", f"{year}-07-20"),
        ("3T", f"{year}-01-01", f"{year}-09-30", f"{year}-10-20"),
        ("4T", f"{year}-01-01", f"{year}-12-31", f"{year+1}-01-30"),
    ]
    for trimestre, inicio, fin, limite in trimestres_130:
        eventos.append({
            "modelo":      "130",
            "nombre":      f"IRPF Fraccionado {trimestre} {year}",
            "descripcion": f"Pago fraccionado IRPF ED {trimestre}. Período: {inicio} a {fin}",
            "fecha_limite":limite,
            "periodo":     trimestre,
            "tipo":        "irpf_fraccionado",
            "urgente_dias":15,
        })

    # Modelo 111 — Retenciones IRPF (trimestral)
    for trimestre, inicio, fin, limite in trimestres_303:
        eventos.append({
            "modelo":      "111",
            "nombre":      f"Retenciones {trimestre} {year}",
            "descripcion": f"Retenciones IRPF {trimestre}. Nóminas y profesionales.",
            "fecha_limite":limite,
            "periodo":     trimestre,
            "tipo":        "retenciones",
            "urgente_dias":15,
        })

    # Modelo 347 — Operaciones con terceros (anual)
    eventos.append({
        "modelo":      "347",
        "nombre":      f"Operaciones con terceros {year}",
        "descripcion": f"Declaración anual de operaciones >3.005,06€ con terceros. Año {year}.",
        "fecha_limite": f"{year+1}-02-28",
        "periodo":      "Anual",
        "tipo":         "informativo_anual",
        "urgente_dias": 30,
    })

    # Modelo 190 — Resumen anual retenciones
    eventos.append({
        "modelo":      "190",
        "nombre":      f"Resumen Retenciones {year}",
        "descripcion": f"Resumen anual de retenciones e ingresos a cuenta {year}.",
        "fecha_limite": f"{year+1}-01-31",
        "periodo":      "Anual",
        "tipo":         "retenciones_anual",
        "urgente_dias": 30,
    })

    # IVA Anual — Modelo 390
    eventos.append({
        "modelo":      "390",
        "nombre":      f"Resumen Anual IVA {year}",
        "descripcion": f"Declaración-resumen anual IVA {year}.",
        "fecha_limite": f"{year+1}-01-30",
        "periodo":      "Anual",
        "tipo":         "iva_anual",
        "urgente_dias": 30,
    })

    return sorted(eventos, key=lambda x: x["fecha_limite"])


def get_proximos_vencimientos(days_ahead: int = 60) -> list[dict]:
    """Filtra los vencimientos fiscales de los próximos N días."""
    today = date.today()
    year = today.year
    calendario = get_calendario_fiscal(year) + get_calendario_fiscal(year + 1)

    proximos = []
    for evento in calendario:
        try:
            fecha = date.fromisoformat(evento["fecha_limite"])
        except ValueError:
            continue
        delta = (fecha - today).days
        if 0 <= delta <= days_ahead:
            proximos.append({**evento, "dias_restantes": delta})

    return sorted(proximos, key=lambda x: x["dias_restantes"])
