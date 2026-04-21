"""
Generación de PDF: Modelo 303 — Autoliquidación IVA trimestral.
"""

import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

from app.services.documents._pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _make_doc,
    _table_header_style,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )


# ---------------------------------------------------------------------------
# Modelo 303 — helpers internos
# ---------------------------------------------------------------------------


def _modelo303_info_header(tenant: dict, quarter: int, year: int, s, C) -> list:
    """Cabecera del Modelo 303: badge BORRADOR + tabla informativa + separador."""
    quarter_labels = {
        1: "1T (Enero - Marzo)",
        2: "2T (Abril - Junio)",
        3: "3T (Julio - Septiembre)",
        4: "4T (Octubre - Diciembre)",
    }
    elements = [Paragraph("Modelo 303 — Autoliquidación IVA", s["title"]), Spacer(1, 3 * mm)]

    draft_table = Table(
        [
            [
                Paragraph(
                    "BORRADOR — NO VÁLIDO PARA PRESENTACIÓN",
                    ParagraphStyle(
                        "DraftBadge",
                        parent=s["styles"]["Normal"],
                        fontSize=10,
                        fontName="Helvetica-Bold",
                        textColor=colors.HexColor(C["AMBER"]),
                    ),
                )
            ]
        ],
        colWidths=[175 * mm],
    )
    draft_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(C["AMBER"])),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(draft_table)
    elements.append(Spacer(1, 5 * mm))

    info_data = [
        [
            Paragraph("Empresa:", s["header"]),
            Paragraph(tenant.get("name", "—"), s["body"]),
            Paragraph("NIF:", s["header"]),
            Paragraph(tenant.get("nif", "—"), s["body"]),
        ],
        [
            Paragraph("Período:", s["header"]),
            Paragraph(quarter_labels.get(quarter, ""), s["body"]),
            Paragraph("Ejercicio:", s["header"]),
            Paragraph(str(year), s["body"]),
        ],
    ]
    info_table = Table(info_data, colWidths=[22 * mm, 65 * mm, 22 * mm, 65 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elements.extend(
        [
            info_table,
            Spacer(1, 5 * mm),
            HRFlowable(width="100%", thickness=2, color=colors.HexColor(C["INDIGO"])),
            Spacer(1, 5 * mm),
        ]
    )
    return elements


def _modelo303_vat_table(rows: list, total_label: str, bg_color: str, s, C) -> tuple:
    """Tabla de filas IVA (devengado o deducible). Retorna (Table, total_base, total_quota)."""
    col_widths = [50 * mm, 45 * mm, 45 * mm]
    table_data = [
        [
            Paragraph("Tipo IVA", s["header"]),
            Paragraph("Base imponible", s["header"]),
            Paragraph("Cuota", s["header"]),
        ]
    ]
    total_base = 0.0
    total_quota = 0.0
    for row in rows:
        base_v = float(row.get("base", 0))
        quota_v = float(row.get("quota", 0))
        total_base += base_v
        total_quota += quota_v
        table_data.append(
            [
                Paragraph(f"{float(row.get('rate', 0)):.0f}%", s["body"]),
                Paragraph(f"{base_v:.2f} €", s["right"]),
                Paragraph(f"{quota_v:.2f} €", s["right"]),
            ]
        )
    table_data.append(
        [
            Paragraph(
                total_label,
                ParagraphStyle(
                    "VatTotalLbl",
                    parent=s["styles"]["Normal"],
                    fontSize=9,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(C["SLATE"]),
                ),
            ),
            Paragraph(f"{total_base:.2f} €", s["right_bold"]),
            Paragraph(f"{total_quota:.2f} €", s["right_bold"]),
        ]
    )
    tbl = Table(table_data, colWidths=col_widths)
    tbl.setStyle(
        TableStyle(
            _table_header_style()
            + [
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.HexColor(C["LINE"])),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(bg_color)),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    return tbl, total_base, total_quota


def _modelo303_resultado(total_devengado: float, total_deducible: float, s, C) -> list:
    """Bloque de resultado: A ingresar o a compensar."""
    resultado = total_devengado - total_deducible
    result_label = "A INGRESAR" if resultado >= 0 else "A COMPENSAR"
    result_color = C["RED"] if resultado >= 0 else C["EMERALD"]
    sty = s["styles"]["Normal"]

    result_data = [
        [
            Paragraph("IVA devengado (A):", s["right"]),
            Paragraph(f"{total_devengado:.2f} €", s["right_bold"]),
        ],
        [
            Paragraph("IVA deducible (B):", s["right"]),
            Paragraph(f"{total_deducible:.2f} €", s["right_bold"]),
        ],
        [
            Paragraph(
                f"RESULTADO ({result_label}):",
                ParagraphStyle(
                    "ResLabel",
                    parent=sty,
                    fontSize=12,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(result_color),
                    alignment=TA_RIGHT,
                ),
            ),
            Paragraph(
                f"{abs(resultado):.2f} €",
                ParagraphStyle(
                    "ResVal",
                    parent=sty,
                    fontSize=14,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(result_color),
                    alignment=TA_RIGHT,
                ),
            ),
        ],
    ]
    result_table = Table(result_data, colWidths=[130 * mm, 40 * mm], hAlign="RIGHT")
    result_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEABOVE", (0, 2), (-1, 2), 2, colors.HexColor(result_color)),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#f8fafc")),
            ]
        )
    )
    return [result_table, Spacer(1, 10 * mm)]


# ---------------------------------------------------------------------------
# Modelo 303 — Autoliquidación IVA
# ---------------------------------------------------------------------------


def generate_modelo_303_pdf(data: dict) -> bytes:
    """
    Genera PDF borrador del Modelo 303 (liquidación trimestral IVA).

    data:
    - tenant: dict con name, nif
    - quarter: int (1-4)
    - year: int
    - vat_collected: list of dict con rate, base, quota  (IVA devengado / ventas)
    - vat_deducted: list of dict con rate, base, quota   (IVA deducible / compras)
    """
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 303 BORRADOR Q{data.get('quarter')}/{data.get('year')}\n".encode("utf-8")

    s = _common_styles()
    C = s["C"]
    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    elements = []

    # ── CABECERA ──
    elements.extend(
        _modelo303_info_header(
            data.get("tenant", {}), int(data.get("quarter", 1)), int(data.get("year", 2026)), s, C
        )
    )

    # ── SECCIÓN A: IVA DEVENGADO ──
    elements.append(
        Paragraph("A) IVA DEVENGADO (Ventas y prestaciones de servicios)", s["section"])
    )
    vat_table, _, total_col_quota = _modelo303_vat_table(
        data.get("vat_collected", []), "TOTAL IVA DEVENGADO", "#f0fdf4", s, C
    )
    elements.extend([vat_table, Spacer(1, 6 * mm)])

    # ── SECCIÓN B: IVA DEDUCIBLE ──
    elements.append(Paragraph("B) IVA DEDUCIBLE (Compras y gastos)", s["section"]))
    ded_table, _, total_ded_quota = _modelo303_vat_table(
        data.get("vat_deducted", []), "TOTAL IVA DEDUCIBLE", "#fef2f2", s, C
    )
    elements.extend([ded_table, Spacer(1, 8 * mm)])

    # ── RESULTADO ──
    elements.extend(_modelo303_resultado(total_col_quota, total_ded_quota, s, C))

    # ── PIE ──
    elements.extend(
        [
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C["LINE"])),
            Spacer(1, 3 * mm),
            Paragraph(
                "Documento informativo generado automáticamente. No sustituye la presentación oficial ante la AEAT.",
                ParagraphStyle(
                    "AEATFooter",
                    parent=s["styles"]["Normal"],
                    fontSize=8,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(C["RED"]),
                    alignment=TA_CENTER,
                ),
            ),
            Spacer(1, 2 * mm),
            Paragraph(
                f"Generado por AutomatizaPyme · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                s["footer"],
            ),
        ]
    )

    doc.build(elements)
    return buffer.getvalue()
