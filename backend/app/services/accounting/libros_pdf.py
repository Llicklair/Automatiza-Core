"""Generadores PDF de Libros Contables Oficiales: Diario, Mayor, Balance, P&G.

Reusa los helpers de `app.services.documents._pdf_base`. Diseño sobrio
orientado a presentar/legalizar (no diseño comercial).
"""

from __future__ import annotations

import io
import logging
from collections import OrderedDict
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.accounting import JournalEntry, JournalLine
from app.db.models.models import Tenant

_log = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:  # pragma: no cover
    REPORTLAB_AVAILABLE = False


# ─── Helpers comunes ────────────────────────────────────────────────────────


def _fmt_eur(v) -> str:
    if v is None:
        return ""
    try:
        n = float(v)
    except (TypeError, ValueError):
        return str(v)
    if abs(n) < 0.005:
        return ""
    return f"{n:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _fmt_date(d) -> str:
    if d is None:
        return ""
    if hasattr(d, "strftime"):
        return d.strftime("%d/%m/%Y")
    return str(d)


async def _load_tenant(db: AsyncSession, tenant_id: UUID) -> tuple[str, str]:
    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    t = res.scalar_one_or_none()
    if t is None:
        return ("Mi Empresa", "B00000000")
    return (t.name or "Mi Empresa", t.nif or "B00000000")


async def _entries_in_range(
    db: AsyncSession, tenant_id: UUID, start: date, end: date
) -> list[JournalEntry]:
    res = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(
            and_(
                JournalEntry.tenant_id == tenant_id,
                func.date(JournalEntry.date) >= start,
                func.date(JournalEntry.date) <= end,
            )
        )
        .order_by(JournalEntry.date.asc(), JournalEntry.created_at.asc())
    )
    return list(res.scalars().unique().all())


def _header_block(title: str, tenant_name: str, tenant_nif: str, periodo: str, styles):
    h = styles["Title"]
    sub = styles["Normal"]
    return [
        Paragraph(title, h),
        Paragraph(
            f"<b>{tenant_name}</b> · NIF {tenant_nif} · Periodo: {periodo}",
            sub,
        ),
        Spacer(1, 6 * mm),
    ]


# ─── Libro Diario ───────────────────────────────────────────────────────────


async def generate_libro_diario_pdf(
    db: AsyncSession, tenant_id: UUID, start: date, end: date,
) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab no instalado")

    tenant_name, tenant_nif = await _load_tenant(db, tenant_id)
    entries = await _entries_in_range(db, tenant_id, start, end)
    periodo = f"{start.isoformat()} – {end.isoformat()}"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Libro Diario {periodo}",
    )
    styles = getSampleStyleSheet()
    story: list = []
    story += _header_block("LIBRO DIARIO", tenant_name, tenant_nif, periodo, styles)

    rows = [["Nº", "Fecha", "Cuenta", "Descripción", "Debe", "Haber"]]
    total_debe = Decimal("0")
    total_haber = Decimal("0")
    for i, e in enumerate(entries, start=1):
        first = True
        for line in e.lines:
            debe = Decimal(str(line.debit or 0))
            haber = Decimal(str(line.credit or 0))
            total_debe += debe
            total_haber += haber
            rows.append([
                str(i) if first else "",
                _fmt_date(e.date) if first else "",
                f"{line.account_code} {line.account_name or ''}".strip(),
                e.description if first else "",
                _fmt_eur(debe),
                _fmt_eur(haber),
            ])
            first = False
    rows.append(["", "", "", "TOTALES", _fmt_eur(total_debe), _fmt_eur(total_haber)])

    col_widths = [12 * mm, 22 * mm, 40 * mm, 60 * mm, 26 * mm, 26 * mm]
    table = Table(rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (4, 1), (5, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(table)
    story.append(Spacer(1, 6 * mm))

    descuadre = total_debe - total_haber
    if abs(descuadre) > Decimal("0.01"):
        story.append(Paragraph(
            f'<font color="red"><b>⚠ Descuadre: {_fmt_eur(descuadre)}</b></font>',
            styles["Normal"],
        ))
    else:
        story.append(Paragraph(
            f"Cuadrado: Debe = Haber = {_fmt_eur(total_debe)}",
            styles["Normal"],
        ))

    doc.build(story)
    return buffer.getvalue()


# ─── Libro Mayor ────────────────────────────────────────────────────────────


async def generate_libro_mayor_pdf(
    db: AsyncSession, tenant_id: UUID, start: date, end: date,
) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab no instalado")

    tenant_name, tenant_nif = await _load_tenant(db, tenant_id)
    entries = await _entries_in_range(db, tenant_id, start, end)
    periodo = f"{start.isoformat()} – {end.isoformat()}"

    # Agrupar líneas por cuenta
    by_account: dict[str, list[tuple[JournalEntry, JournalLine]]] = OrderedDict()
    for e in entries:
        for line in e.lines:
            code = line.account_code or "(sin cuenta)"
            by_account.setdefault(code, []).append((e, line))

    # Ordenar cuentas
    by_account = OrderedDict(sorted(by_account.items(), key=lambda x: x[0]))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Libro Mayor {periodo}",
    )
    styles = getSampleStyleSheet()
    story: list = []
    story += _header_block("LIBRO MAYOR", tenant_name, tenant_nif, periodo, styles)

    for i, (code, lines_for_acc) in enumerate(by_account.items()):
        if i > 0:
            story.append(Spacer(1, 5 * mm))
        account_name = next(
            (ln.account_name for _, ln in lines_for_acc if ln.account_name),
            "",
        )
        story.append(Paragraph(
            f"<b>Cuenta {code}</b> · {account_name}",
            styles["Heading4"],
        ))

        rows = [["Fecha", "Descripción", "Debe", "Haber", "Saldo"]]
        saldo = Decimal("0")
        tot_d, tot_h = Decimal("0"), Decimal("0")
        # Ordenar dentro de la cuenta por fecha
        sorted_lines = sorted(lines_for_acc, key=lambda x: x[0].date)
        for e, line in sorted_lines:
            debe = Decimal(str(line.debit or 0))
            haber = Decimal(str(line.credit or 0))
            tot_d += debe
            tot_h += haber
            saldo += debe - haber
            rows.append([
                _fmt_date(e.date),
                (e.description or "")[:80],
                _fmt_eur(debe),
                _fmt_eur(haber),
                _fmt_eur(saldo),
            ])
        rows.append(["", "TOTAL CUENTA", _fmt_eur(tot_d), _fmt_eur(tot_h), _fmt_eur(saldo)])

        col_widths = [22 * mm, 80 * mm, 26 * mm, 26 * mm, 26 * mm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (2, 1), (4, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        story.append(t)

    if not by_account:
        story.append(Paragraph("No hay movimientos en el periodo.", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()


# ─── Balance + P&G (cuentas anuales abreviadas) ──────────────────────────────

# Agrupación PGC PYME por dígito inicial
PGC_GROUPS = {
    "1": ("Patrimonio neto y pasivo no corriente", "pn"),
    "2": ("Activo no corriente", "anc"),
    "3": ("Existencias", "ac"),
    "4": ("Deudores / Acreedores", "mixed"),
    "5": ("Tesorería y financieros corto plazo", "ac"),
    "6": ("Gastos", "g"),
    "7": ("Ingresos", "i"),
}


async def generate_balance_pyg_pdf(
    db: AsyncSession, tenant_id: UUID, start: date, end: date,
) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab no instalado")

    tenant_name, tenant_nif = await _load_tenant(db, tenant_id)
    entries = await _entries_in_range(db, tenant_id, start, end)
    periodo = f"{start.isoformat()} – {end.isoformat()}"

    # Acumular saldos por cuenta
    saldos: dict[str, Decimal] = {}
    for e in entries:
        for line in e.lines:
            code = line.account_code or "(sin cuenta)"
            debe = Decimal(str(line.debit or 0))
            haber = Decimal(str(line.credit or 0))
            saldos[code] = saldos.get(code, Decimal("0")) + debe - haber

    # Agrupar por dígito inicial
    grupos: dict[str, list[tuple[str, Decimal]]] = {k: [] for k in PGC_GROUPS}
    for code, saldo in saldos.items():
        d1 = code[:1]
        if d1 in grupos:
            grupos[d1].append((code, saldo))
    for g in grupos.values():
        g.sort(key=lambda x: x[0])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=f"Cuentas Anuales {periodo}",
    )
    styles = getSampleStyleSheet()
    story: list = []
    story += _header_block(
        "CUENTAS ANUALES ABREVIADAS — BALANCE Y P&G",
        tenant_name, tenant_nif, periodo, styles,
    )

    # P&G primero (cuentas 6 y 7)
    total_ingresos = -sum((s for _, s in grupos.get("7", [])), Decimal("0"))  # Ingresos son haber → saldo negativo en debe-haber
    total_gastos = sum((s for _, s in grupos.get("6", [])), Decimal("0"))
    resultado = total_ingresos - total_gastos

    story.append(Paragraph("<b>Cuenta de Pérdidas y Ganancias</b>", styles["Heading3"]))
    pyg_rows = [["Concepto", "Importe"]]
    pyg_rows.append(["Ingresos de explotación (cuentas 7)", _fmt_eur(total_ingresos)])
    pyg_rows.append(["Gastos de explotación (cuentas 6)", f"({_fmt_eur(total_gastos)})"])
    pyg_rows.append(["RESULTADO DEL EJERCICIO", _fmt_eur(resultado)])
    t1 = Table(pyg_rows, colWidths=[110 * mm, 50 * mm])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(t1)
    story.append(Spacer(1, 8 * mm))

    # Balance abreviado (activo / pasivo)
    story.append(Paragraph("<b>Balance de Situación</b>", styles["Heading3"]))

    activo_no_corriente = sum((s for _, s in grupos.get("2", [])), Decimal("0"))
    existencias = sum((s for _, s in grupos.get("3", [])), Decimal("0"))
    deudores = sum((s for _, s in grupos.get("4", []) if s > 0), Decimal("0"))
    tesoreria = sum((s for _, s in grupos.get("5", []) if s > 0), Decimal("0"))
    total_activo = activo_no_corriente + existencias + deudores + tesoreria

    patrimonio = -sum((s for _, s in grupos.get("1", [])), Decimal("0"))  # cuentas grupo 1 son haber
    acreedores = -sum((s for _, s in grupos.get("4", []) if s < 0), Decimal("0"))
    financiero_cp = -sum((s for _, s in grupos.get("5", []) if s < 0), Decimal("0"))
    total_pasivo_pn = patrimonio + acreedores + financiero_cp + resultado

    balance_rows = [
        ["ACTIVO", "Importe", "PATRIMONIO NETO Y PASIVO", "Importe"],
        ["A) Activo no corriente (2)", _fmt_eur(activo_no_corriente),
         "A) Patrimonio neto (1) + Rdo. ejercicio", _fmt_eur(patrimonio + resultado)],
        ["B) Existencias (3)", _fmt_eur(existencias),
         "B) Pasivo no corriente", _fmt_eur(0)],
        ["C) Deudores (4 deudor)", _fmt_eur(deudores),
         "C) Acreedores (4 acreedor)", _fmt_eur(acreedores)],
        ["D) Tesorería (5 deudor)", _fmt_eur(tesoreria),
         "D) Deuda corto plazo (5 acreedor)", _fmt_eur(financiero_cp)],
        ["TOTAL ACTIVO", _fmt_eur(total_activo),
         "TOTAL PN + PASIVO", _fmt_eur(total_pasivo_pn)],
    ]
    t2 = Table(balance_rows, colWidths=[55 * mm, 30 * mm, 55 * mm, 30 * mm])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("ALIGN", (3, 1), (3, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#fef3c7")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ]))
    story.append(t2)

    desc = total_activo - total_pasivo_pn
    if abs(desc) > Decimal("0.01"):
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(
            f'<font color="red"><b>⚠ Descuadre balance: {_fmt_eur(desc)}</b></font>',
            styles["Normal"],
        ))

    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph(
        '<font size="7" color="#6b7280">Cálculo abreviado a partir del libro diario. '
        "Para depósito en el Registro Mercantil pueden requerirse ajustes (clasificación funcional, "
        "amortizaciones, ECPN, EFE, memoria). Consulta con tu asesor antes de depositar.</font>",
        styles["Normal"],
    ))

    doc.build(story)
    return buffer.getvalue()
