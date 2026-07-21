"""URL de cotejo de la AEAT para el código QR tributario VeriFactu.

Doc técnico oficial de la AEAT ("Detalle de las especificaciones técnicas del código
QR de la factura y de la URL del servicio de cotejo"). La URL del servicio de cotejo
para facturas verificables es el endpoint `ValidarQR`, e incorpora ÚNICAMENTE los 4
parámetros obligatorios, en este orden: `nif`, `numserie`, `fecha`, `importe`,
codificados en UTF-8 (URL encoding).
"""

from __future__ import annotations

from urllib.parse import urlencode

# Servicio de cotejo VERI*FACTU (facturas verificables).
_AEAT_QR_PROD = "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR"
_AEAT_QR_TEST = "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR"


def qr_base_url() -> str:
    """URL base del servicio de cotejo. En entorno de pruebas (beta contra el portal
    de pruebas de la AEAT) apunta a preproducción; en producción, a producción.
    Overridable con la setting `VERIFACTU_QR_BASE`."""
    from app.core.config import settings

    override = getattr(settings, "VERIFACTU_QR_BASE", None)
    if override:
        return str(override)
    env = str(getattr(settings, "VERIFACTU_ENV", "test") or "test").lower()
    return _AEAT_QR_PROD if env in ("prod", "production", "produccion") else _AEAT_QR_TEST


def build_aeat_cotejo_url(
    *,
    nif: str,
    num_serie: str,
    fecha: str,
    importe: str,
    base: str | None = None,
) -> str:
    """URL de cotejo del QR tributario: base del servicio `ValidarQR` + los 4
    parámetros obligatorios en orden (nif, numserie, fecha, importe), URL-encoded
    en UTF-8. `fecha` en formato dd-mm-yyyy; `importe` con punto y 2 decimales."""
    params = {"nif": nif, "numserie": num_serie, "fecha": fecha, "importe": importe}
    return f"{base or qr_base_url()}?{urlencode(params)}"
