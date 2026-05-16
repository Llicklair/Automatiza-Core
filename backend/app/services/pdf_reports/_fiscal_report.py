"""
Generación de PDF: Informe Fiscal (IVA + IRPF + IS) y persistencia en BD.
"""

import io
import logging
import os
import uuid
from datetime import UTC, datetime

_logger = logging.getLogger(__name__)

from app.services.documents._pdf_base import (
    REPORTLAB_AVAILABLE,
    _fmt_eur,
)

if REPORTLAB_AVAILABLE:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

# ---------------------------------------------------------------------------
# Paleta de colores compartida
# ---------------------------------------------------------------------------

_FISCAL_COLORS: dict = {}


def _fc() -> dict:
    """Lazy-init de colores (solo cuando REPORTLAB_AVAILABLE)."""
    if _FISCAL_COLORS:
        return _FISCAL_COLORS
    _FISCAL_COLORS.update(
        INDIGO=colors.HexColor("#6366f1"),
        EMERALD=colors.HexColor("#10b981"),
        RED=colors.HexColor("#ef4444"),
        AMBER=colors.HexColor("#f59e0b"),
        BLUE=colors.HexColor("#3b82f6"),
        SLATE=colors.HexColor("#1e293b"),
        GRAY=colors.HexColor("#64748b"),
        LIGHT=colors.HexColor("#f8fafc"),
        LINE=colors.HexColor("#e2e8f0"),
        FOOTER=colors.HexColor("#94a3b8"),
    )
    return _FISCAL_COLORS


def _fiscal_styles() -> dict:
    """Crea los estilos usados en el informe fiscal."""
    styles = getSampleStyleSheet()
    C = _fc()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    return {
        "company": sty("FCo", fontSize=20, fontName="Helvetica-Bold", textColor=C["SLATE"]),
        "badge": sty("FBa", fontSize=9, fontName="Helvetica-Bold", textColor=C["RED"]),
        "period": sty(
            "FPe", fontSize=13, fontName="Helvetica-Bold", textColor=C["SLATE"], alignment=TA_RIGHT
        ),
        "generated": sty(
            "FGe", fontSize=7, fontName="Helvetica", textColor=C["FOOTER"], alignment=TA_RIGHT
        ),
        "section": sty(
            "FSe",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=C["GRAY"],
            spaceBefore=6,
            spaceAfter=4,
        ),
        "resumen": sty(
            "FRe",
            fontSize=9,
            fontName="Helvetica",
            textColor=colors.HexColor("#334155"),
            leading=13,
            spaceBefore=4,
        ),
        "kpi_lbl": sty(
            "FKl", fontSize=7, fontName="Helvetica", textColor=C["GRAY"], alignment=TA_CENTER
        ),
        "footer": sty(
            "FFo", fontSize=7, fontName="Helvetica", textColor=C["FOOTER"], alignment=TA_CENTER
        ),
        "row_lbl": sty("FRl", fontSize=8, fontName="Helvetica", textColor=C["GRAY"]),
        "row_val": sty(
            "FRv", fontSize=8, fontName="Helvetica-Bold", textColor=C["SLATE"], alignment=TA_RIGHT
        ),
        "row_val_em": sty(
            "FRve", fontSize=8, fontName="Helvetica-Bold", textColor=C["INDIGO"], alignment=TA_RIGHT
        ),
        "row_val_red": sty(
            "FRvr", fontSize=8, fontName="Helvetica-Bold", textColor=C["RED"], alignment=TA_RIGHT
        ),
        "_sty": sty,  # factory para estilos one-off
    }


# ---------------------------------------------------------------------------
# Informe Fiscal — secciones internas
# ---------------------------------------------------------------------------


def _fiscal_header(company_name: str, period_label: str, st: dict) -> list:
    """Cabecera + resumen ejecutivo badge."""
    C = _fc()
    header_data = [
        [
            [
                Paragraph(company_name, st["company"]),
                Spacer(1, 5),
                Paragraph("INFORME FISCAL", st["badge"]),
            ],
            [
                Paragraph(period_label, st["period"]),
                Spacer(1, 5),
                Paragraph(
                    f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", st["generated"]
                ),
            ],
        ]
    ]
    header_table = Table(header_data, colWidths=[110 * mm, 65 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return [
        header_table,
        Spacer(1, 7 * mm),
        HRFlowable(width="100%", thickness=2, color=C["RED"]),
        Spacer(1, 6 * mm),
    ]


def _fiscal_resumen(resumen: str, st: dict) -> list:
    """Sección resumen ejecutivo."""
    C = _fc()
    resumen_box = Table([[Paragraph(resumen, st["resumen"])]], colWidths=[175 * mm])
    resumen_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
                ("LINEABOVE", (0, 0), (-1, 0), 2, C["RED"]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return [
        Paragraph("RESUMEN EJECUTIVO", st["section"]),
        resumen_box,
        Spacer(1, 6 * mm),
    ]


def _fiscal_kpis(iva: dict, irpf: dict, is_: dict, st: dict) -> list:
    """Tarjetas KPI: resultado IVA, IRPF, IS, total."""
    C = _fc()
    sty = st["_sty"]

    resultado_iva = float(iva.get("resultado_iva", 0))
    total_irpf = float(irpf.get("total_retenciones", 0))
    cuota_is = float(is_.get("cuota_estimada", 0))
    saldo_fiscal = resultado_iva + total_irpf + cuota_is
    iva_color = C["RED"] if resultado_iva > 0 else C["EMERALD"]

    kpi_data = [
        [
            [
                Paragraph(
                    _fmt_eur(resultado_iva),
                    sty(
                        "fkv1",
                        fontSize=14,
                        fontName="Helvetica-Bold",
                        textColor=iva_color,
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph("Resultado IVA", st["kpi_lbl"]),
            ],
            [
                Paragraph(
                    _fmt_eur(total_irpf),
                    sty(
                        "fkv2",
                        fontSize=14,
                        fontName="Helvetica-Bold",
                        textColor=C["AMBER"],
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph("IRPF Retenciones", st["kpi_lbl"]),
            ],
            [
                Paragraph(
                    _fmt_eur(cuota_is),
                    sty(
                        "fkv3",
                        fontSize=14,
                        fontName="Helvetica-Bold",
                        textColor=C["BLUE"],
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph("IS Estimado", st["kpi_lbl"]),
            ],
            [
                Paragraph(
                    _fmt_eur(saldo_fiscal),
                    sty(
                        "fkv4",
                        fontSize=14,
                        fontName="Helvetica-Bold",
                        textColor=C["SLATE"],
                        alignment=TA_CENTER,
                    ),
                ),
                Paragraph("Total obligaciones", st["kpi_lbl"]),
            ],
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[44 * mm] * 4)
    kpi_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.5, iva_color),
                ("BOX", (1, 0), (1, 0), 0.5, C["AMBER"]),
                ("BOX", (2, 0), (2, 0), 0.5, C["BLUE"]),
                ("BOX", (3, 0), (3, 0), 0.5, C["SLATE"]),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    colors.HexColor("#fef2f2") if resultado_iva > 0 else colors.HexColor("#f0fdf4"),
                ),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fffbeb")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#eff6ff")),
                ("BACKGROUND", (3, 0), (3, 0), C["LIGHT"]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return [kpi_table, Spacer(1, 6 * mm)]


def _fiscal_iva_section(iva: dict, st: dict) -> list:
    """Sección 1: tabla IVA + gráfico de barras."""
    C = _fc()
    sty = st["_sty"]

    rep_21 = float(iva.get("repercutido_21", 0))
    rep_10 = float(iva.get("repercutido_10", 0))
    rep_4 = float(iva.get("repercutido_4", 0))
    sop_21 = float(iva.get("soportado_21", 0))
    sop_10 = float(iva.get("soportado_10", 0))
    sop_4 = float(iva.get("soportado_4", 0))
    total_rep = float(iva.get("total_repercutido", 0))
    total_sop = float(iva.get("total_soportado", 0))
    resultado_iva = float(iva.get("resultado_iva", 0))

    iva_detail = [
        [
            Paragraph("Tipo", st["row_lbl"]),
            Paragraph("Repercutido", st["row_val"]),
            Paragraph("Soportado", st["row_val"]),
            Paragraph("Diferencia", st["row_val"]),
        ],
        [
            Paragraph("General (21%)", st["row_lbl"]),
            Paragraph(_fmt_eur(rep_21), st["row_val"]),
            Paragraph(_fmt_eur(sop_21), st["row_val"]),
            Paragraph(_fmt_eur(rep_21 - sop_21), st["row_val"]),
        ],
        [
            Paragraph("Reducido (10%)", st["row_lbl"]),
            Paragraph(_fmt_eur(rep_10), st["row_val"]),
            Paragraph(_fmt_eur(sop_10), st["row_val"]),
            Paragraph(_fmt_eur(rep_10 - sop_10), st["row_val"]),
        ],
        [
            Paragraph("Superreducido (4%)", st["row_lbl"]),
            Paragraph(_fmt_eur(rep_4), st["row_val"]),
            Paragraph(_fmt_eur(sop_4), st["row_val"]),
            Paragraph(_fmt_eur(rep_4 - sop_4), st["row_val"]),
        ],
        [
            Paragraph(
                "TOTAL", sty("FTot", fontSize=8, fontName="Helvetica-Bold", textColor=C["SLATE"])
            ),
            Paragraph(_fmt_eur(total_rep), st["row_val_em"]),
            Paragraph(_fmt_eur(total_sop), st["row_val_red"]),
            Paragraph(
                _fmt_eur(resultado_iva),
                sty(
                    "FResV",
                    fontSize=8,
                    fontName="Helvetica-Bold",
                    textColor=C["RED"] if resultado_iva > 0 else C["EMERALD"],
                    alignment=TA_RIGHT,
                ),
            ),
        ],
    ]
    iva_tbl = Table(iva_detail, colWidths=[45 * mm, 38 * mm, 38 * mm, 38 * mm])
    iva_tbl.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, C["LINE"]),
                ("LINEBELOW", (0, -2), (-1, -2), 0.3, colors.HexColor("#f1f5f9")),
                ("BACKGROUND", (0, 0), (-1, 0), C["LIGHT"]),
                (
                    "BACKGROUND",
                    (0, -1),
                    (-1, -1),
                    colors.HexColor("#fef2f2") if resultado_iva > 0 else colors.HexColor("#f0fdf4"),
                ),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )

    elems = [
        Paragraph("1. IMPUESTO SOBRE EL VALOR AÑADIDO (IVA)", st["section"]),
        iva_tbl,
    ]

    if total_rep > 0 or total_sop > 0:
        d = Drawing(160 * mm, 50 * mm)
        chart = VerticalBarChart()
        chart.x = 35
        chart.y = 15
        chart.width = 150 * mm - 50
        chart.height = 50 * mm - 25
        chart.data = [[total_rep, total_sop, abs(resultado_iva)]]
        chart.categoryAxis.categoryNames = ["Repercutido", "Soportado", "Resultado"]
        chart.categoryAxis.labels.fontSize = 7
        chart.categoryAxis.labels.fontName = "Helvetica"
        chart.categoryAxis.labels.fillColor = C["GRAY"]
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.labels.fontName = "Helvetica"
        chart.valueAxis.labels.fillColor = C["GRAY"]
        chart.valueAxis.visibleGrid = True
        chart.valueAxis.gridStrokeColor = colors.HexColor("#f1f5f9")
        chart.valueAxis.gridStrokeWidth = 0.5
        chart.valueAxis.forceZero = True
        chart.bars[0].fillColor = C["INDIGO"]
        chart.bars[(0, 0)].fillColor = C["EMERALD"]
        chart.bars[(0, 1)].fillColor = C["RED"]
        chart.bars[(0, 2)].fillColor = C["AMBER"]
        d.add(chart)
        elems.extend([Spacer(1, 3 * mm), d])

    elems.extend(
        [
            Spacer(1, 5 * mm),
            HRFlowable(width="100%", thickness=0.5, color=C["LINE"]),
            Spacer(1, 3 * mm),
        ]
    )
    return elems


def _fiscal_irpf_section(irpf: dict, st: dict) -> list:
    """Sección 2: tabla IRPF."""
    C = _fc()
    sty = st["_sty"]

    irpf_nominas = float(irpf.get("retenciones_nominas", 0))
    irpf_facturas = float(irpf.get("retenciones_facturas", 0))
    total_irpf = float(irpf.get("total_retenciones", 0))

    irpf_detail = [
        [Paragraph("Concepto", st["row_lbl"]), Paragraph("Importe", st["row_val"])],
        [
            Paragraph("Retenciones en nominas", st["row_lbl"]),
            Paragraph(_fmt_eur(irpf_nominas), st["row_val"]),
        ],
        [
            Paragraph("Retenciones en facturas profesionales", st["row_lbl"]),
            Paragraph(_fmt_eur(irpf_facturas), st["row_val"]),
        ],
        [
            Paragraph(
                "TOTAL RETENCIONES",
                sty("FIrpfT", fontSize=8, fontName="Helvetica-Bold", textColor=C["SLATE"]),
            ),
            Paragraph(_fmt_eur(total_irpf), st["row_val_em"]),
        ],
    ]
    irpf_tbl = Table(irpf_detail, colWidths=[120 * mm, 45 * mm])
    irpf_tbl.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, C["LINE"]),
                ("LINEBELOW", (0, -2), (-1, -2), 0.3, colors.HexColor("#f1f5f9")),
                ("BACKGROUND", (0, 0), (-1, 0), C["LIGHT"]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fffbeb")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    return [
        Paragraph("2. RETENCIONES IRPF", st["section"]),
        irpf_tbl,
        Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=0.5, color=C["LINE"]),
        Spacer(1, 3 * mm),
    ]


def _fiscal_is_section(is_: dict, st: dict) -> list:
    """Sección 3: tabla Impuesto de Sociedades."""
    C = _fc()
    sty = st["_sty"]

    ingresos_b = float(is_.get("ingresos_brutos", 0))
    gastos_d = float(is_.get("gastos_deducibles", 0))
    base_imp = float(is_.get("base_imponible", 0))
    tipo_is = float(is_.get("tipo_estimado", 25))
    cuota_is = float(is_.get("cuota_estimada", 0))

    is_detail = [
        [Paragraph("Concepto", st["row_lbl"]), Paragraph("Importe", st["row_val"])],
        [
            Paragraph("Ingresos brutos (base imponible ventas)", st["row_lbl"]),
            Paragraph(_fmt_eur(ingresos_b), st["row_val"]),
        ],
        [
            Paragraph("Gastos deducibles (compras + nominas)", st["row_lbl"]),
            Paragraph(_fmt_eur(gastos_d), st["row_val_red"]),
        ],
        [
            Paragraph(
                "Base imponible",
                sty("FIsBI", fontSize=8, fontName="Helvetica-Bold", textColor=C["SLATE"]),
            ),
            Paragraph(_fmt_eur(base_imp), st["row_val_em"]),
        ],
        [
            Paragraph(f"Tipo impositivo ({tipo_is:.0f}%)", st["row_lbl"]),
            Paragraph(f"{tipo_is:.0f}%", st["row_val"]),
        ],
        [
            Paragraph(
                "CUOTA ESTIMADA IS",
                sty("FIsQ", fontSize=9, fontName="Helvetica-Bold", textColor=C["SLATE"]),
            ),
            Paragraph(
                _fmt_eur(cuota_is),
                sty(
                    "FIsQV",
                    fontSize=9,
                    fontName="Helvetica-Bold",
                    textColor=C["BLUE"],
                    alignment=TA_RIGHT,
                ),
            ),
        ],
    ]
    is_tbl = Table(is_detail, colWidths=[120 * mm, 45 * mm])
    is_tbl.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, C["LINE"]),
                ("LINEBELOW", (0, 2), (-1, 2), 0.3, colors.HexColor("#f1f5f9")),
                ("LINEBELOW", (0, -2), (-1, -2), 0.5, C["LINE"]),
                ("BACKGROUND", (0, 0), (-1, 0), C["LIGHT"]),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#eff6ff")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )
    return [
        Paragraph("3. IMPUESTO DE SOCIEDADES (ESTIMACION)", st["section"]),
        is_tbl,
    ]


def _fiscal_footer(st: dict) -> list:
    """Disclaimer + timestamp."""
    C = _fc()
    sty = st["_sty"]
    return [
        Spacer(1, 8 * mm),
        HRFlowable(width="100%", thickness=0.5, color=C["LINE"]),
        Spacer(1, 3 * mm),
        Paragraph(
            "Este informe es una estimacion orientativa generada automaticamente. "
            "No sustituye el asesoramiento fiscal profesional ni las declaraciones oficiales ante la AEAT.",
            sty("FDisc", fontSize=7, fontName="Helvetica", textColor=C["RED"], alignment=TA_CENTER),
        ),
        Spacer(1, 3 * mm),
        Paragraph(
            f"Generado por AutomatizaPyme \u00b7 {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            st["footer"],
        ),
    ]


# ---------------------------------------------------------------------------
# Informe Fiscal principal
# ---------------------------------------------------------------------------


def generate_fiscal_report_pdf(snap: dict, company_name: str, period: str) -> bytes:
    """
    Genera el informe fiscal PDF con secciones IVA, IRPF e IS.

    snap: dict con estructura FiscalSnapshot:
      snap["iva"], snap["irpf"], snap["impuesto_sociedades"], snap["resumen_ejecutivo"]
    """
    if not REPORTLAB_AVAILABLE:
        return f"Informe Fiscal {period}\n{snap.get('resumen_ejecutivo', '')}".encode()

    iva = snap.get("iva", {})
    irpf = snap.get("irpf", {})
    is_ = snap.get("impuesto_sociedades", {})
    resumen = snap.get("resumen_ejecutivo", "")
    period_label = snap.get("period_label", period)

    st = _fiscal_styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    elements = []
    elements.extend(_fiscal_header(company_name, period_label, st))
    elements.extend(_fiscal_resumen(resumen, st))
    elements.extend(_fiscal_kpis(iva, irpf, is_, st))
    elements.extend(_fiscal_iva_section(iva, st))
    elements.extend(_fiscal_irpf_section(irpf, st))
    elements.extend(_fiscal_is_section(is_, st))
    elements.extend(_fiscal_footer(st))

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Persist fiscal report PDF as a TenantDocument
# ---------------------------------------------------------------------------

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))


async def save_fiscal_report_to_db(
    pdf_bytes: bytes,
    period: str,
    resumen_ejecutivo: str,
    tenant_id,
    uploaded_by,
    db,
):
    """Guarda el PDF del informe fiscal en disco y crea el registro TenantDocument."""
    from app.db.models.models import TenantDocument

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_period = period.replace("-", "_")
    file_name = f"fiscal_{safe_period}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as fh:
        fh.write(pdf_bytes)

    doc = TenantDocument(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        uploaded_by=uploaded_by,
        file_name=file_name,
        file_type="application/pdf",
        file_path=file_path,
        file_size=len(pdf_bytes),
        status="processed",
        parsed_content=resumen_ejecutivo,
        category="informes",
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc
