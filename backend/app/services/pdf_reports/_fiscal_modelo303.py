"""
Generación de PDF: Modelo 303 — Autoliquidación IVA trimestral.

Replica el formato oficial de la AEAT con casillas numeradas: identificación del
declarante, devengo (ejercicio/período) y liquidación con las casillas oficiales
(régimen general 01-09, intra/ISP 10-13, recargo de equivalencia 16-24, total
devengada 27, deducible 28-45 y resultado 46-71). Se marca como BORRADOR — no
sustituye la presentación telemática ante la AEAT.

Maquetación compartida con el resto de modelos AEAT vía `_aeat_layout.py`. Las
casillas de tipo impositivo (`_PCT_CASILLAS`) se formatean como porcentaje.
"""

import io
import logging
from datetime import datetime

from app.core.datetime_utils import BUSINESS_TZ, local_today
from app.services.aeat.casillas_303 import build_casillas_303
from app.services.pdf.pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _make_doc,
)
from app.services.pdf_reports._aeat_layout import (
    _casillas_table,
    _draft_badge,
    _identificacion_table,
    _resultado_badge,
    _section_banner,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, Spacer

_logger = logging.getLogger(__name__)

# Casillas cuyo valor es un porcentaje (tipo impositivo), no un importe.
_PCT_CASILLAS = {"02", "05", "08", "17", "20", "23", "65"}


# ---------------------------------------------------------------------------
# Modelo 303 — Autoliquidación IVA (formato oficial AEAT)
# ---------------------------------------------------------------------------


def generate_modelo_303_pdf(data: dict) -> bytes:
    """Genera el PDF borrador del Modelo 303 con las casillas oficiales AEAT.

    `data` es el dict de `build_modelo_303_data` (tenant, quarter, year,
    vat_collected, vat_deducted, vat_intra, vat_isp, recargo_equivalencia).
    """
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 303 BORRADOR Q{data.get('quarter')}/{data.get('year')}\n".encode()

    s = _common_styles()
    C = s["C"]
    quarter = int(data.get("quarter", 1))
    year = int(data.get("year", local_today().year))

    casillas = build_casillas_303(data)
    cmap = {c.codigo: c for c in casillas}

    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    el: list = [
        Paragraph(
            "Modelo 303 · Impuesto sobre el Valor Añadido · Autoliquidación",
            s["title"],
        ),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), quarter, year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Devengo · Liquidación — IVA devengado", s),
        Spacer(1, 2 * mm),
    ]

    # IVA devengado: régimen general (01-09), intra/ISP (10-13), recargo (16-24
    # solo si hay), total cuota devengada (27).
    devengado_codes = ["01", "02", "03", "04", "05", "06", "07", "08", "09",
                       "10", "11", "12", "13"]
    for cod_b, cod_c in (("16", "18"), ("19", "21"), ("22", "24")):
        cb, cc = cmap.get(cod_b), cmap.get(cod_c)
        if (cb and float(cb.valor)) or (cc and float(cc.valor)):
            base, tipo = cod_b, str(int(cod_b) + 1)
            devengado_codes += [base, tipo, cod_c]
    devengado_codes.append("27")
    dev_tbl = _casillas_table(cmap, devengado_codes, s, C, emphasis=("27",),
                              pct_codes=_PCT_CASILLAS)
    if dev_tbl is not None:
        el.append(dev_tbl)

    el += [
        Spacer(1, 5 * mm),
        _section_banner("3. Liquidación — IVA deducible", s),
        Spacer(1, 2 * mm),
    ]
    ded_tbl = _casillas_table(
        cmap, ["28", "29", "30", "31", "36", "37", "45"], s, C, emphasis=("45",),
        pct_codes=_PCT_CASILLAS,
    )
    if ded_tbl is not None:
        el.append(ded_tbl)

    el += [
        Spacer(1, 5 * mm),
        _section_banner("Resultado de la autoliquidación", s),
        Spacer(1, 2 * mm),
    ]
    res_tbl = _casillas_table(
        cmap, ["46", "64", "65", "66", "67", "69", "71"], s, C, emphasis=("46", "71"),
        pct_codes=_PCT_CASILLAS,
    )
    if res_tbl is not None:
        el.append(res_tbl)

    resultado_71 = float(cmap["71"].valor) if "71" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado_71, s)]

    # Pie legal
    el += [
        Spacer(1, 8 * mm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C["LINE"])),
        Spacer(1, 3 * mm),
        Paragraph(
            "Documento informativo (borrador) generado automáticamente. No sustituye "
            "la presentación oficial ante la AEAT. Las casillas marcadas como editables "
            "(p. ej. 28, 30, 67) pueden requerir ajuste manual antes de presentar.",
            ParagraphStyle(
                "AEATFooter", parent=s["styles"]["Normal"], fontSize=8,
                fontName="Helvetica-Bold", textColor=colors.HexColor(C["RED"]),
                alignment=TA_CENTER,
            ),
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            f"Generado por AutomatizaCore · {datetime.now(BUSINESS_TZ).strftime('%d/%m/%Y %H:%M')}",
            s["footer"],
        ),
    ]

    doc.build(el)
    return buffer.getvalue()
