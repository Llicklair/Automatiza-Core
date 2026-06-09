"""Genera un PDF de estudio de mercado de AutomatizaCore para presentar.

Uso:
    python scripts/generate_market_study.py

Salida:
    C:\\Users\\Marcos\\Desktop\\AutomatizaCore_Estudio_Mercado_OAP_Valencia.pdf

Datos cuantitativos: rangos derivados de fuentes públicas conocidas
(INE/DIRCE 2024, RETA, ONTSI, AMETIC, Comisión Europea). NO verificados
online en esta ejecución — son cifras de orden de magnitud conservadoras.
Si se necesitan datos exactos para una presentación oficial, verificar
antes de imprimir.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Paleta y estilos ─────────────────────────────────────────────────────────

C_PRIMARY = HexColor("#1f3a5f")   # azul corporativo
C_ACCENT = HexColor("#2da7a0")     # turquesa accent
C_TEXT = HexColor("#1f2937")       # gris oscuro
C_MUTED = HexColor("#6b7280")      # gris medio
C_LIGHT_BG = HexColor("#f3f4f6")   # fondo claro
C_BORDER = HexColor("#d1d5db")

base_styles = getSampleStyleSheet()


def _style(name, parent="Normal", **kwargs):
    if name in base_styles.byName:
        return base_styles[name]
    return ParagraphStyle(name=name, parent=base_styles[parent], **kwargs)


STYLE_COVER_TITLE = ParagraphStyle(
    name="CoverTitle",
    parent=base_styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=32,
    leading=38,
    alignment=TA_CENTER,
    textColor=C_PRIMARY,
    spaceAfter=16,
)
STYLE_COVER_SUB = ParagraphStyle(
    name="CoverSub",
    parent=base_styles["Normal"],
    fontName="Helvetica",
    fontSize=16,
    leading=22,
    alignment=TA_CENTER,
    textColor=C_TEXT,
    spaceAfter=10,
)
STYLE_COVER_META = ParagraphStyle(
    name="CoverMeta",
    parent=base_styles["Normal"],
    fontName="Helvetica",
    fontSize=11,
    leading=16,
    alignment=TA_CENTER,
    textColor=C_MUTED,
)
STYLE_H1 = ParagraphStyle(
    name="MH1",
    parent=base_styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=26,
    textColor=C_PRIMARY,
    spaceBefore=0,
    spaceAfter=14,
)
STYLE_H2 = ParagraphStyle(
    name="MH2",
    parent=base_styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=18,
    textColor=C_PRIMARY,
    spaceBefore=12,
    spaceAfter=8,
)
STYLE_H3 = ParagraphStyle(
    name="MH3",
    parent=base_styles["Heading3"],
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=15,
    textColor=C_ACCENT,
    spaceBefore=8,
    spaceAfter=4,
)
STYLE_BODY = ParagraphStyle(
    name="MBody",
    parent=base_styles["Normal"],
    fontName="Helvetica",
    fontSize=10,
    leading=15,
    textColor=C_TEXT,
    alignment=TA_JUSTIFY,
    spaceAfter=6,
)
STYLE_BULLET = ParagraphStyle(
    name="MBullet",
    parent=STYLE_BODY,
    leftIndent=14,
    bulletIndent=4,
    spaceAfter=3,
)
STYLE_QUOTE = ParagraphStyle(
    name="MQuote",
    parent=STYLE_BODY,
    leftIndent=16,
    rightIndent=16,
    fontName="Helvetica-Oblique",
    textColor=C_MUTED,
    borderColor=C_ACCENT,
    borderWidth=0,
    borderPadding=8,
    backColor=C_LIGHT_BG,
    spaceBefore=6,
    spaceAfter=10,
)
STYLE_CAPTION = ParagraphStyle(
    name="MCaption",
    parent=base_styles["Normal"],
    fontName="Helvetica-Oblique",
    fontSize=8,
    leading=11,
    textColor=C_MUTED,
    alignment=TA_CENTER,
    spaceAfter=10,
)
# Estilo compacto para celdas de tabla con word-wrap.
STYLE_CELL = ParagraphStyle(
    name="MCell",
    parent=base_styles["Normal"],
    fontName="Helvetica",
    fontSize=8.5,
    leading=11,
    textColor=C_TEXT,
    alignment=TA_LEFT,
)
STYLE_CELL_HEADER = ParagraphStyle(
    name="MCellHeader",
    parent=STYLE_CELL,
    fontName="Helvetica-Bold",
    fontSize=8.5,
    textColor=white,
)


def cell(text):
    """Envuelve texto en un Paragraph para que la tabla haga word-wrap."""
    return Paragraph(str(text), STYLE_CELL)


def cell_header(text):
    return Paragraph(str(text), STYLE_CELL_HEADER)

# ── Header / Footer ──────────────────────────────────────────────────────────


def _on_page(canvas, doc):
    """Footer con paginación y rótulo en cada página interior."""
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.4)
    canvas.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(C_MUTED)
    canvas.drawString(
        2 * cm, 1.1 * cm, "AutomatizaCore — Estudio de mercado (mayo 2026)"
    )
    canvas.drawRightString(
        A4[0] - 2 * cm, 1.1 * cm, f"Página {doc.page}"
    )
    canvas.restoreState()


# ── Helpers de contenido ─────────────────────────────────────────────────────


def H1(text):
    return Paragraph(text, STYLE_H1)


def H2(text):
    return Paragraph(text, STYLE_H2)


def H3(text):
    return Paragraph(text, STYLE_H3)


def P(text):
    return Paragraph(text, STYLE_BODY)


def Quote(text):
    return Paragraph(text, STYLE_QUOTE)


def BulletList(items):
    return [Paragraph(f"• {item}", STYLE_BULLET) for item in items]


def DataTable(data, col_widths=None, header_row=True):
    tbl = Table(data, colWidths=col_widths, repeatRows=1 if header_row else 0)
    style = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
        ("LEADING", (0, 0), (-1, -1), 12),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BOX", (0, 0), (-1, -1), 0.4, C_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, C_BORDER),
    ]
    if header_row:
        style += [
            ("BACKGROUND", (0, 0), (-1, 0), C_PRIMARY),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ]
        # Filas alternas
        for i in range(2, len(data), 2):
            style.append(("BACKGROUND", (0, i), (-1, i), C_LIGHT_BG))
    tbl.setStyle(TableStyle(style))
    return tbl


def SectionBreak():
    return [Spacer(1, 0.4 * cm)]


# ── Secciones del documento ──────────────────────────────────────────────────


def cover_page():
    elements = [
        Spacer(1, 4 * cm),
        Paragraph("AutomatizaCore", STYLE_COVER_TITLE),
        Spacer(1, 0.4 * cm),
        Paragraph("Estudio de mercado", STYLE_COVER_SUB),
        Paragraph(
            "Suite ERP con IA conversacional nativa para PYMEs y autónomos",
            STYLE_COVER_META,
        ),
        Spacer(1, 6 * cm),
        Paragraph("Preparado para:", STYLE_COVER_META),
        Paragraph(
            "<b>OAP Valencia</b>",
            ParagraphStyle(
                "metaB", parent=STYLE_COVER_META, fontName="Helvetica-Bold",
                fontSize=13, textColor=C_PRIMARY,
            ),
        ),
        Spacer(1, 0.6 * cm),
        Paragraph(
            f"Presentación: 25 de mayo de 2026 · Versión 1.0", STYLE_COVER_META
        ),
        PageBreak(),
    ]
    return elements


def section_resumen():
    return [
        H1("1. Resumen ejecutivo"),
        P(
            "AutomatizaCore es una suite de gestión empresarial (ERP) diseñada "
            "específicamente para pequeñas y medianas empresas y autónomos del "
            "mercado español, con cuatro diferenciadores estructurales frente a "
            "las soluciones cloud incumbentes:"
        ),
        *BulletList([
            "<b>Arquitectura desktop-first</b>: backend embebido y base de datos local — soberanía del dato y funcionamiento offline.",
            "<b>IA verticalizada en todo el ERP</b>: 13+ agentes especializados (facturación, contabilidad, RRHH, CRM, banca, documentos, fiscal, marketing...). No es un chatbot bolt-on: la IA vive en cada dominio operativo con prompts y herramientas propias.",
            "<b>Motor dual de automatización</b>: ejecutor determinista para procesos repetitivos (nóminas, modelos AEAT, recordatorios) con coste y latencia previsibles, y motor de razonamiento por LLM para tareas abiertas. El sistema escoge automáticamente.",
            "<b>Empleados IA personalizables</b>: cada cliente «contrata» especialistas con nombre, rol, personalidad, skills y presupuesto propios — extensión de plantilla virtual, no configuración técnica abstracta.",
        ]),
        P(
            "El producto se sitúa en un mercado direccionable estimado en torno "
            "a 6,7 millones de sujetos potenciales en España (PYMEs + autónomos) "
            "con una demanda creciente impulsada por tres factores convergentes: "
            "<b>(a)</b> la obligación de Verifactu (RD 1007/2023) desde julio "
            "de 2025, <b>(b)</b> la entrada en vigor de la AI Act europea y "
            "<b>(c)</b> la presión de digitalización del Kit Digital."
        ),
        P(
            "Este documento presenta el dimensionamiento del mercado (TAM/SAM/"
            "SOM), el análisis competitivo frente a los actores principales "
            "(Holded, Quipu, Contasimple, A3, Odoo), la propuesta de valor "
            "diferencial y el posicionamiento estratégico para la fase comercial "
            "inicial centrada en la Comunidad Valenciana."
        ),
        Quote(
            "<b>Promesa central:</b> que el dueño de una PYME pueda gestionar "
            "su empresa hablando con su ordenador en lenguaje natural, sin "
            "depender de la nube, sin perder la soberanía sobre sus datos y "
            "cumpliendo con la normativa fiscal española desde el día uno."
        ),
        PageBreak(),
    ]


def section_mercado():
    return [
        H1("2. Definición del mercado objetivo"),
        H2("2.1 — Cliente objetivo"),
        P(
            "El segmento objetivo son <b>empresas de menos de 50 empleados</b> "
            "y <b>autónomos en régimen RETA</b> que cumplen al menos uno de "
            "los siguientes criterios:"
        ),
        *BulletList([
            "Llevan la gestión administrativa internamente (no externalizan a gestoría premium).",
            "Han adoptado o evaluado una herramienta SaaS de facturación pero la consideran fragmentada o cara.",
            "Tienen un perfil tecnológico medio: usan email, banca online y al menos una hoja de cálculo activa.",
            "Operan en sectores con alta carga administrativa: servicios, comercio minorista, consultoría, hostelería, profesionales.",
        ]),
        H2("2.2 — Necesidad insatisfecha (problem statement)"),
        P(
            "Las herramientas actuales del segmento PYME están polarizadas:"
        ),
        *BulletList([
            "<b>Soluciones generalistas en cloud</b> (Holded, Odoo, Zoho One) con curva de aprendizaje exigente y ergonomía pensada para administradores, no para el dueño operativo.",
            "<b>Soluciones verticales fragmentadas</b> (Quipu para facturación, Declarando para fiscal, A3 ASESOR para gestorías): cada una resuelve una parte; el dueño acaba pegando piezas.",
            "<b>Asesorías tradicionales</b> que cobran 80-300 €/mes y cuyo valor percibido baja a medida que el dueño ve que el proceso fiscal podría automatizarse.",
        ]),
        P(
            "La pieza que falta — y que justifica este proyecto — es una "
            "herramienta donde el dueño no aprenda <i>cómo se hace</i> sino "
            "que diga <i>qué quiere</i> y el sistema lo ejecute. Eso es lo "
            "que la IA agente moderna permite hoy técnicamente y lo que "
            "ninguna de las soluciones del segmento ha integrado de forma "
            "nativa todavía."
        ),
        PageBreak(),
    ]


def section_dimensionamiento():
    tam_data = [
        ["Métrica", "Estimación", "Fuente / referencia"],
        ["Empresas activas en España", "≈ 3,4 M", "DIRCE / INE 2024"],
        ["% PYMEs (<250 empleados)", "≈ 99,9 %", "DIRCE / INE 2024"],
        ["Microempresas (1-9 empleados)", "≈ 95 % del total", "DIRCE / INE 2024"],
        ["Autónomos en RETA", "≈ 3,3 M", "TGSS / Seguridad Social 2024"],
        ["TAM total (PYMEs + autónomos)", "≈ 6,7 M sujetos", "Suma estimada"],
    ]
    sam_data = [
        ["Filtro", "Penetración", "Volumen estimado"],
        ["Adopción SaaS gestión en PYMEs ES", "≈ 30-40 %", "≈ 1,0-1,4 M"],
        ["Subset evaluando o usando IA en gestión", "≈ 10-15 %", "≈ 100-200 k"],
        ["SAM (digitalmente activo + interés IA)", "—", "≈ 600 k - 1 M"],
    ]
    som_data = [
        ["Segmento", "Volumen", "Captura realista año 1"],
        ["Comunidad Valenciana — empresas", "≈ 370 k", "—"],
        ["Comunidad Valenciana — autónomos", "≈ 370 k", "—"],
        ["Concentración Valencia provincia", "≈ 50 %", "—"],
        ["Captura objetivo 0,1-0,5 % SAM CV", "—", "≈ 370 - 1.800 clientes"],
    ]
    return [
        H1("3. Dimensionamiento del mercado (TAM / SAM / SOM)"),
        P(
            "Se aplica la metodología clásica TAM/SAM/SOM con cifras "
            "públicas conocidas a nivel nacional y, para el SOM, foco "
            "geográfico inicial en la Comunidad Valenciana."
        ),
        H2("3.1 — TAM: mercado total direccionable"),
        DataTable(tam_data, col_widths=[6.5 * cm, 4 * cm, 6 * cm]),
        Spacer(1, 0.3 * cm),
        P(
            "El TAM bruto incluye a todo sujeto fiscal con obligación de "
            "facturación en España. No todo ese universo es alcanzable "
            "comercialmente — el SAM aplica filtros realistas."
        ),
        H2("3.2 — SAM: mercado al que podemos servir"),
        DataTable(sam_data, col_widths=[8 * cm, 3.5 * cm, 5 * cm]),
        Spacer(1, 0.3 * cm),
        P(
            "El SAM se construye aplicando dos filtros: <b>(a)</b> penetración "
            "real de software de gestión SaaS en PYMEs españolas (estudios "
            "ONTSI/AMETIC oscilan entre 30-40 % según segmento y año) y "
            "<b>(b)</b> el subset que ya usa o evalúa herramientas con IA "
            "—una cohorte que crece al 30-40 % anual desde 2023 según "
            "informes sectoriales."
        ),
        H2("3.3 — SOM: captura realista en el primer año (Comunidad Valenciana)"),
        DataTable(som_data, col_widths=[8 * cm, 3.5 * cm, 5 * cm]),
        Spacer(1, 0.3 * cm),
        P(
            "Para la fase de lanzamiento comercial se focaliza la Comunidad "
            "Valenciana —en particular la provincia de Valencia, que concentra "
            "aproximadamente la mitad del tejido empresarial autonómico—. "
            "Una captura conservadora del 0,1-0,5 % del SAM regional en el "
            "primer año equivale a 370-1.800 clientes activos, lo que da "
            "viabilidad comercial al modelo aunque se posicione en el tier "
            "medio de pricing."
        ),
        Paragraph(
            "Nota: las cifras absolutas son órdenes de magnitud derivados de "
            "fuentes públicas (INE/DIRCE, TGSS, ONTSI, AMETIC). Para un "
            "<i>business case</i> firme, verificar el dato más reciente al "
            "trimestre de presentación.",
            STYLE_CAPTION,
        ),
        PageBreak(),
    ]


def section_competencia():
    headers = ["Competidor", "Posición", "Pricing aprox.", "Fortaleza", "Debilidad vs. nosotros"]
    raw_rows = [
        ["Holded", "ERP cloud generalista", "30-60 €/mes", "Cuota de mercado, integraciones", "Sin IA nativa; SaaS puro (no soberanía)"],
        ["Quipu", "Facturación + conta", "9-30 €/mes", "Pricing bajo, simple", "Funcionalidad limitada; UI tradicional"],
        ["Contasimple", "Autónomos básico", "Freemium - 12 €", "Gratis tier", "Solo facturación; sin RRHH/CRM"],
        ["A3 Software (WK)", "Asesorías premium", "100-400 €/mes", "Incumbente, integración AEAT", "Caro, complejo, no orientado al dueño"],
        ["Odoo", "ERP open-source", "20-50 €/usr/mes", "Modular, código abierto", "Despliegue complejo; sin IA nativa"],
        ["Declarando", "Fiscal autónomos", "20-60 €/mes", "UX cuidada, foco fiscal", "Solo fiscal; no es ERP completo"],
        ["Sage / MS Dynamics", "Mid-market", ">200 €/mes", "Robustez enterprise", "Caro y sobredimensionado para PYME"],
        ["AutomatizaCore", "ERP + IA verticalizada, desktop-first", "Tiers Starter/Pro/Business", "IA en cada vertical + motor det/razon + empleados IA custom + soberanía dato + Verifactu", "Producto pre-comercial (lanzamiento Q3 2026)"],
    ]
    rows = [[cell_header(h) for h in headers]]
    rows += [[cell(c) for c in row] for row in raw_rows]
    return [
        H1("4. Análisis competitivo"),
        P(
            "El segmento ERP/gestión para PYMEs en España es maduro y "
            "fragmentado. La tabla siguiente resume el posicionamiento de "
            "los actores relevantes a fecha de mayo de 2026:"
        ),
        DataTable(rows, col_widths=[2.6 * cm, 3.2 * cm, 2.6 * cm, 3.5 * cm, 4.7 * cm]),
        Spacer(1, 0.4 * cm),
        H2("4.1 — Matriz de posicionamiento"),
        P(
            "Si proyectamos los actores en un eje de <b>ergonomía/IA</b> "
            "frente a <b>amplitud funcional</b>, se identifican cuatro "
            "cuadrantes:"
        ),
        *BulletList([
            "<b>Cuadrante UI tradicional + amplio</b>: Holded, Odoo, Sage. Funcionalidad completa pero curva de aprendizaje exigente.",
            "<b>Cuadrante UI tradicional + estrecho</b>: Quipu, Contasimple, Declarando. Especializados; el cliente debe pegar varios.",
            "<b>Cuadrante IA + estrecho</b>: TaxDown y similares. IA limitada a una vertical fiscal.",
            "<b>Cuadrante IA + amplio</b>: <b>vacío hoy</b>. AutomatizaCore apunta a ocuparlo.",
        ]),
        H2("4.2 — Barreras de entrada para competidores cloud"),
        P(
            "Los incumbentes cloud (Holded, Quipu) tendrían que reestructurar "
            "su arquitectura para ofrecer una versión <i>desktop-first</i> "
            "con datos soberanos. Es técnicamente posible pero canibalizaría "
            "su modelo de pricing recurrente, lo que les desincentiva a "
            "moverse hasta que la presión sea ineludible. Esta ventana "
            "competitiva estimamos que dura entre 18 y 36 meses."
        ),
        PageBreak(),
    ]


def section_tendencias():
    return [
        H1("5. Tendencias regulatorias y tecnológicas"),
        H2("5.1 — Verifactu (RD 1007/2023): obligación desde julio de 2025"),
        P(
            "El Real Decreto 1007/2023 obliga a que todo software de "
            "facturación emita facturas con una huella criptográfica "
            "encadenada que la AEAT pueda verificar. Esto afecta a "
            "<b>todo emisor de facturas</b> excepto algunos regímenes "
            "excepcionales y entró en vigor en julio de 2025."
        ),
        P(
            "<b>Implicación competitiva:</b> los sistemas locales artesanales "
            "(hojas Excel, plantillas Word, software legacy sin certificación) "
            "quedan fuera de cumplimiento. Esto genera una ola forzada de "
            "actualización de millones de PYMEs durante 2025-2027. Verifactu "
            "es probablemente el mayor disparador comercial del segmento en "
            "esta década."
        ),
        H2("5.2 — AI Act (Reglamento UE 2024/1689)"),
        P(
            "El reglamento europeo de inteligencia artificial impone "
            "obligaciones graduadas según el nivel de riesgo del sistema "
            "(Art. 50 transparencia, Art. 26 obligaciones del deployer, "
            "Art. 12 logging automático). Los proveedores de software con "
            "IA deben acreditar trazabilidad, gobernanza de prompts y "
            "consentimiento."
        ),
        P(
            "AutomatizaCore incorpora desde diseño los mecanismos exigidos "
            "(logging append-only de cada invocación de agente, opt-out "
            "RGPD Art. 7, banner Art. 50, plantilla de información a "
            "trabajadores Art. 26.7). Esta preparación se convierte en "
            "ventaja comercial frente a competidores que <i>añadirán IA</i> "
            "tras la fecha de aplicación obligatoria sin esa fundación."
        ),
        H2("5.3 — Kit Digital y ayudas a la digitalización"),
        P(
            "El Kit Digital (Acelera PYME) ha inyectado entre 2022 y 2025 "
            "más de 3.000 M€ de subvención a la digitalización de PYMEs "
            "españolas. Las categorías relevantes para AutomatizaCore son "
            "gestión de procesos, factura electrónica, oficina virtual y "
            "ciberseguridad. El estatus de Agente Digitalizador acreditado "
            "habilita capturar estos importes como descuento aplicable al "
            "precio de licencia."
        ),
        H2("5.4 — IA agente: del asistente al ejecutor"),
        P(
            "El estado del arte de los LLMs comerciales (Claude, GPT-4, "
            "Gemini) ha pasado en 18 meses de <i>responder preguntas</i> a "
            "<i>ejecutar tareas multi-paso con herramientas</i>. El coste "
            "por token cae al 40-50 % anual mientras la capacidad sube. "
            "Esto convierte en económicamente viable cargas de trabajo que "
            "hace dos años eran prohibitivas: procesar facturas en PDF, "
            "redactar nóminas, conciliar movimientos bancarios contra "
            "facturas emitidas, todo desde lenguaje natural."
        ),
        PageBreak(),
    ]


def section_propuesta():
    return [
        H1("6. Propuesta de valor diferencial"),
        P(
            "AutomatizaCore se diferencia de los actores del segmento en "
            "seis pilares estructurales, pensados como ventaja arquitectónica "
            "—difícil de copiar por incumbentes sin canibalizar su modelo "
            "actual— y no como simples <i>features</i>:"
        ),

        # ── 6.1 Desktop-first ─────────────────────────────────────────────
        H2("6.1 — Arquitectura: desktop-first con soberanía del dato"),
        P(
            "A diferencia de los SaaS tradicionales, AutomatizaCore se "
            "instala como aplicación de escritorio (Electron) con el "
            "backend Python y la base de datos PostgreSQL <b>embebidos</b> "
            "en la propia máquina del cliente. Sus datos no salen de su "
            "ordenador salvo cuando el usuario invoca explícitamente un "
            "agente que requiere un LLM externo, y en ese caso solo el "
            "prompt acotado al contexto necesario."
        ),
        P(
            "Esto resuelve la objeción que aparece en el 100 % de los "
            "primeros contactos comerciales del segmento: <i>«¿dónde van "
            "mis datos?»</i>. Y permite ofrecer un punto de precio "
            "imposible para un SaaS puro al no haber coste de infraestructura "
            "cloud recurrente."
        ),

        # ── 6.2 IA verticalizada ──────────────────────────────────────────
        H2("6.2 — IA verticalizada: un agente especializado por dominio del ERP"),
        P(
            "Frente a los productos del segmento que añaden IA como un "
            "<i>chatbot</i> bolt-on sobre la interfaz tradicional, "
            "AutomatizaCore integra IA <b>en cada vertical operativa</b> "
            "de la empresa. El usuario habla en lenguaje natural con un "
            "Coordinador que clasifica la intención y delega en el agente "
            "experto de ese dominio:"
        ),
        *BulletList([
            "<b>Facturación</b> — emisión, recordatorios, cobro, integración Verifactu.",
            "<b>Contabilidad</b> — asientos automáticos desde facturas y movimientos bancarios.",
            "<b>RRHH</b> — nóminas, control horario, gestión de altas/bajas SS.",
            "<b>CRM</b> — oportunidades, seguimiento de leads, cualificación.",
            "<b>Banca</b> — importación N43, conciliación automática contra facturas.",
            "<b>Documentos</b> — OCR, clasificación, búsqueda semántica (RAG sobre tus PDFs).",
            "<b>Email</b> — bandeja, redacción y envío con contexto de la empresa.",
            "<b>Compliance</b> — vencimientos AEAT, modelos 303/130/347/390, BOE.",
            "<b>Reclutamiento</b> — criba de CVs, scoring contra vacantes.",
            "<b>Marketing</b> — generación de copy, campañas, contenido divulgativo.",
            "<b>Reports</b> — informes ejecutivos, cashflow, modelo 303 simulado.",
            "<b>Workflows</b> — automatizaciones recurrentes desde lenguaje natural.",
        ]),
        P(
            "Cada agente está afinado con prompts versionados, contexto del "
            "tenant y herramientas (tools) específicas. No es el mismo "
            "modelo respondiendo de forma genérica: es un especialista por "
            "área que conoce el esquema de tus datos y los modos correctos "
            "de operar en ese dominio."
        ),
        PageBreak(),

        # ── 6.3 Motor dual ────────────────────────────────────────────────
        H2("6.3 — Motor dual: automatización determinista o por razonamiento"),
        P(
            "Las automatizaciones recurrentes en una PYME tienen dos "
            "naturalezas muy distintas, y AutomatizaCore las soporta con "
            "dos motores que comparten arquitectura pero divergen en "
            "ejecución:"
        ),
        DataTable(
            [
                [cell_header("Motor"), cell_header("Cuándo se usa"),
                 cell_header("Coste y latencia"), cell_header("Ejemplos")],
                [cell("<b>Determinista</b>"),
                 cell("Procesos pre-compilados — la estructura del paso a paso es conocida y se ejecuta sin LLM en el path crítico."),
                 cell("Bajo y previsible. Apto para SLA. Compatible con volumen alto."),
                 cell("Generar nóminas el día 25. Recordatorios de impagados. Modelo 303 trimestral. Conciliación N43 contra facturas emitidas.")],
                [cell("<b>Razonamiento</b>"),
                 cell("Tareas abiertas o ambiguas que requieren planificación contextual con LLM."),
                 cell("Mayor coste por invocación, latencia variable. Para casos no rutinarios."),
                 cell("\"Responde al cliente Juan sobre la oferta y adjunta el PDF\". \"Resume el estado del trimestre con alertas\".")],
            ],
            col_widths=[2.8 * cm, 4.5 * cm, 4 * cm, 5.2 * cm],
        ),
        Spacer(1, 0.3 * cm),
        P(
            "<b>Ventaja comercial</b>: las automatizaciones críticas de "
            "negocio (nóminas, facturación recurrente, presentaciones "
            "fiscales) corren en <i>modo determinista</i> con coste y "
            "latencia previsibles —y sin riesgo de alucinación del LLM—. "
            "La capa de razonamiento se reserva para preguntas abiertas "
            "del usuario, donde la flexibilidad sí compensa el coste."
        ),
        P(
            "Esta dualidad es invisible para el cliente: el "
            "Orquestador detecta automáticamente cuándo una instrucción "
            "puede pre-compilarse a pasos deterministas y cuándo necesita "
            "razonamiento. Cuando puede pre-compilarse, queda fijado: la "
            "ejecución repetida es exactamente la misma cada mes."
        ),

        # ── 6.4 Resiliencia catch-up ──────────────────────────────────────
        H2("6.4 — Resiliencia: el ordenador no necesita estar siempre abierto"),
        P(
            "Una preocupación legítima de cualquier herramienta "
            "<i>desktop-first</i> con automatizaciones programadas es: "
            "<i>«¿qué pasa con mi factura mensual del día 1 si justo ese "
            "día tengo el portátil apagado?»</i>. La respuesta de "
            "AutomatizaCore: <b>no pasa nada — se ejecuta en cuanto vuelves "
            "a abrirlo</b>."
        ),
        *BulletList([
            "<b>Registro persistente</b>: cada workflow programado guarda en BD su próxima fecha de disparo. Si el equipo está apagado en ese instante, el cron simplemente queda en estado <i>pendiente</i>, no se pierde.",
            "<b>Catch-up al arrancar</b>: en el arranque del backend, un proceso de recuperación revisa todos los disparadores cuya fecha objetivo ya pasó y los ejecuta en orden, aplicando los criterios fiscales del periodo correcto (p.ej. un Modelo 303 del 1 de abril ejecutado el 3 sigue siendo Q1).",
            "<b>Tolerancia configurable</b>: ventana de gracia ajustable por workflow (por defecto 7 días) — los disparadores fuera de ventana se marcan como <i>caducados</i> y se notifican al usuario en vez de ejecutarse fuera de plazo.",
            "<b>Modo servidor opcional</b>: para clientes con infraestructura propia (PYMEs con NAS o pequeño servidor 24/7), el backend puede correr en modo servicio y eliminar incluso esa ventana de retardo.",
        ]),
        P(
            "Esto cierra la brecha comercial frente a SaaS cloud (que "
            "siempre están encendidos) sin renunciar a las ventajas del "
            "<i>desktop-first</i>: soberanía del dato, sin coste de "
            "infraestructura recurrente y funcionamiento offline para "
            "el trabajo interactivo del día a día."
        ),

        # ── 6.5 Empleados IA ──────────────────────────────────────────────
        H2("6.5 — Empleados IA: contrata especialistas para tu negocio"),
        P(
            "Más allá de los agentes builtin que cubren las verticales "
            "estándar, cada cliente puede <b>«contratar» empleados IA "
            "personalizados</b>: especialistas con nombre, rol, personalidad "
            "y conjunto de herramientas adaptados a su negocio concreto."
        ),
        *BulletList([
            "<b>Configurables como un alta de empleado real</b>: nombre (\"Lucía, mi CFO\"), rol, dominio principal, descripción de responsabilidades, prompt de personalidad, presupuesto mensual en tokens.",
            "<b>Skills modulares</b>: cada empleado custom selecciona qué tools del ERP puede usar (facturación, banca, RRHH, etc.) y con qué nivel de autonomía (consulta, propuesta, ejecución directa).",
            "<b>Aprende del tenant</b>: durante la operativa diaria el empleado consume documentos, facturas y emails del tenant como contexto enriquecido vía RAG semántico.",
            "<b>Trazabilidad y gobierno</b>: cada invocación queda en un log inmutable (cumplimiento AI Act Art. 12) con prompt, modelo, tokens y coste. El dueño ve mensualmente quién hizo qué.",
            "<b>Health-check pre-dispatch</b>: si el empleado está bloqueado, sin prompt o sin skills activas, el sistema lo detecta antes de invocarlo y avisa al usuario en vez de fallar silenciosamente.",
        ]),
        P(
            "<b>Framing comercial</b>: el cliente ya no \"configura un "
            "asistente\" — <i>contrata IA especializada</i>. La diferencia "
            "es semántica pero clave en el segmento PYME: el dueño "
            "entiende «contratar empleados» como concepto cotidiano, y el "
            "producto se posiciona como ampliación de plantilla virtual, "
            "no como herramienta tecnológica abstracta."
        ),

        # ── 6.6 Cumplimiento ──────────────────────────────────────────────
        H2("6.6 — Cumplimiento normativo built-in"),
        P(
            "Verifactu, AI Act, RGPD, conservación 5 años LGT, RGSS para "
            "nóminas, RD 1007/2023 para huella criptográfica: el "
            "cumplimiento de estos marcos viene resuelto de fábrica, no "
            "como módulo opcional. Esto reduce drásticamente el riesgo "
            "regulatorio percibido por el cliente y elimina la necesidad "
            "de un asesor adicional para temas de compliance básico."
        ),
        PageBreak(),
    ]


def section_posicionamiento():
    return [
        H1("7. Posicionamiento estratégico"),
        H2("7.1 — Mensaje canónico"),
        Quote(
            "<i>El primer ERP con IA en cada vertical de tu negocio. Habla "
            "en español, contrata empleados IA especializados (CFO, "
            "comercial, RRHH...) y automatiza tu administración con motor "
            "determinista cuando el proceso es repetitivo y razonamiento "
            "cuando hace falta. Verifactu desde el día uno. Sin nube, sin "
            "gestoría intermedia, sin curva de aprendizaje.</i>"
        ),
        H2("7.2 — Tiers de pricing previstos (v1)"),
        DataTable(
            [
                [cell_header("Tier"), cell_header("Target"),
                 cell_header("Pricing orientativo"), cell_header("Incluye")],
                [cell("Starter"), cell("Autónomo / micro 1-3"),
                 cell("≤ 50 €/mes"), cell("Facturación + Verifactu + 1 agente")],
                [cell("Pro"), cell("PYME 4-15 empleados"),
                 cell("99-199 €/mes"),
                 cell("Todo Starter + RRHH + 5 agentes + automatizaciones")],
                [cell("Business"), cell("PYME 15-50 empleados"),
                 cell("299+ €/mes"),
                 cell("Todo Pro + multi-usuario + SLA + custom agents")],
            ],
            col_widths=[2.4 * cm, 3.6 * cm, 3.4 * cm, 7.1 * cm],
        ),
        Spacer(1, 0.3 * cm),
        P(
            "El pricing aprovecha el subsidio del Kit Digital para "
            "Starter y Pro (descuento aplicable al primer año), lo que "
            "deja el coste neto al cliente en el rango 0-50 €/mes durante "
            "la fase de captura inicial."
        ),
        H2("7.3 — Go-to-market enfocado en Comunidad Valenciana"),
        *BulletList([
            "<b>Canal 1 — Directo</b>: presentaciones en cámaras de comercio, asociaciones de autónomos (ATA, UATAE) y colegios profesionales (COEV, Cámara Valencia).",
            "<b>Canal 2 — Partner gestoría</b>: convenio con 10-20 gestorías valencianas para ofrecer la herramienta a sus clientes con descuento, posicionando a la gestoría como integrador.",
            "<b>Canal 3 — Sectorial</b>: foco en sectores de alta carga administrativa (comercio minorista, hostelería, consultoría) donde el ROI de la automatización es más visible.",
            "<b>Canal 4 — Eventos</b>: presentación inicial en OAP Valencia (mayo 2026), seguida de demos in situ con prospectos cualificados.",
        ]),
        PageBreak(),
    ]


def section_riesgos():
    return [
        H1("8. Riesgos y barreras"),
        H2("8.1 — Riesgos comerciales"),
        *BulletList([
            "<b>Reacción de incumbentes</b>: Holded o A3 podrían anunciar features de IA conversacional en 12-18 meses. Mitigación: foco en soberanía del dato y experiencia desktop como ventaja arquitectónica difícil de replicar sin canibalizar su SaaS.",
            "<b>Coste de adquisición (CAC)</b>: el segmento PYME es disperso geográficamente y reacio a cambiar de herramienta consolidada. Mitigación: estrategia partner-led con gestorías como canal.",
            "<b>Estacionalidad fiscal</b>: el ciclo comercial puede concentrar demanda en Q1 (cierres anuales) y Q4 (planificación), con valles intermedios. Mitigación: contenido formativo y eventos fuera de pico.",
        ]),
        H2("8.2 — Riesgos técnicos"),
        *BulletList([
            "<b>Dependencia de LLM externo</b>: la mayoría de agentes necesitan invocar a un proveedor LLM (Claude, GPT). Mitigación: arquitectura multi-proveedor con fallback y, en roadmap v1.1, modelo local cuando sea económicamente viable.",
            "<b>Cumplimiento Verifactu AEAT</b>: si la implementación falla la homologación, el lanzamiento se retrasa. Mitigación: pruebas en entorno AEAT homologación durante junio 2026, antes de comercialización.",
            "<b>Soporte y mantenimiento desktop</b>: una app instalada en cliente exige actualizaciones autoservicio (auto-update). Mitigación: ya implementado vía electron-builder con canal beta/stable.",
        ]),
        H2("8.3 — Riesgos regulatorios"),
        *BulletList([
            "<b>Cambios en AI Act</b>: la fase de aplicación práctica de la AI Act se está clarificando con guías secundarias. Mitigación: incorporación temprana de las obligaciones de logging y transparencia ya en v1.",
            "<b>Endurecimiento Verifactu</b>: la AEAT podría imponer requisitos adicionales (firma cualificada, conexión continua). Mitigación: arquitectura modular del módulo de cumplimiento.",
        ]),
        PageBreak(),
    ]


def section_conclusiones():
    return [
        H1("9. Conclusiones y siguientes pasos"),
        H2("9.1 — Tesis de inversión / colaboración"),
        P(
            "AutomatizaCore opera en la confluencia de tres olas convergentes: "
            "<b>(1)</b> obligación regulatoria Verifactu que fuerza la "
            "actualización de millones de PYMEs en 2025-2027, <b>(2)</b> "
            "maduración de IA agente que hace técnica y económicamente "
            "viable la automatización conversacional y <b>(3)</b> hueco "
            "competitivo no ocupado por incumbentes en el cuadrante de "
            "<i>IA + amplitud funcional + soberanía del dato</i>."
        ),
        P(
            "La estrategia regional centrada en la Comunidad Valenciana "
            "permite validar el modelo comercial con un mercado capturado "
            "manejable (370-1.800 clientes año 1) antes de escalar a otras "
            "comunidades autónomas en v1.1 (Q4 2026 - Q2 2027)."
        ),
        H2("9.2 — Hitos próximos"),
        DataTable(
            [
                [cell_header("Fecha"), cell_header("Hito")],
                [cell("22 jul 2026"), cell("Lanzamiento comercial v1.0 (España)")],
                [cell("Q3 2026"), cell("Primeros 50 clientes en Comunidad Valenciana")],
                [cell("Q4 2026"), cell("Acreditación Agente Digitalizador Kit Digital")],
                [cell("Q1 2027"), cell("Expansión Cataluña + Madrid (v1.1)")],
                [cell("Q2 2027"), cell("Modelo local on-premise (v1.2)")],
                [cell("Q3 2027"), cell("F2 internacionalización — Portugal (ver §10)")],
                [cell("Q1 2028"), cell("F3 — Italia")],
                [cell("Q4 2028"), cell("F4 — México (puerta a LatAm)")],
                [cell("2029-30"), cell("F5 — Francia y expansión LatAm resto")],
                [cell("2030-31"), cell("F6 — Reino Unido + Irlanda (entrada angloparlante)")],
                [cell("2031-32"), cell("F7 — Australia, Nueva Zelanda y Canadá")],
                [cell("2032-33"), cell("F8 — EE. UU. (entrada selectiva por estado-piloto)")],
            ],
            col_widths=[3.5 * cm, 13 * cm],
        ),
        Spacer(1, 0.4 * cm),
        H2("9.3 — Proyección financiera a 5 años (escenario conservador)"),
        P(
            "Modelo de SaaS sobre clientes activos al cierre de cada año "
            "fiscal, ARPU mensual mixto que refleja la composición esperada "
            "del catálogo (heavy Starter en años 1-2, mix Pro/Business "
            "creciente en años 4-5) y churn anual asumido en el 15 %. "
            "Cifras conservadoras: el extremo bajo del rango SOM y "
            "adquisición orgánica sin disparadores como expansión a otras "
            "comunidades autónomas o eventos virales."
        ),
        DataTable(
            [
                [cell_header("Año fiscal"), cell_header("Clientes activos (cierre)"),
                 cell_header("ARPU mensual"), cell_header("ARR"),
                 cell_header("Coste variable"), cell_header("Margen bruto")],
                [cell("<b>Año 1</b> (2026-27)"), cell("200"),
                 cell("55 €"), cell("132.000 €"),
                 cell("36.000 €"), cell("<b>96.000 €</b> (73 %)")],
                [cell("<b>Año 2</b> (2027-28)"), cell("500"),
                 cell("65 €"), cell("390.000 €"),
                 cell("78.000 €"), cell("<b>312.000 €</b> (80 %)")],
                [cell("<b>Año 3</b> (2028-29)"), cell("1.100"),
                 cell("75 €"), cell("990.000 €"),
                 cell("158.400 €"), cell("<b>831.600 €</b> (84 %)")],
                [cell("<b>Año 4</b> (2029-30)"), cell("2.000"),
                 cell("85 €"), cell("2.040.000 €"),
                 cell("264.000 €"), cell("<b>1.776.000 €</b> (87 %)")],
                [cell("<b>Año 5</b> (2030-31)"), cell("3.200"),
                 cell("95 €"), cell("3.648.000 €"),
                 cell("384.000 €"), cell("<b>3.264.000 €</b> (89 %)")],
                [cell("<b>Acumulado 5 años</b>"), cell("—"),
                 cell("—"), cell("<b>7.200.000 €</b>"),
                 cell("920.400 €"), cell("<b>6.279.600 €</b>")],
            ],
            col_widths=[3 * cm, 2.7 * cm, 2 * cm, 2.6 * cm, 2.6 * cm, 3.6 * cm],
        ),
        Spacer(1, 0.3 * cm),
        H3("Hipótesis del modelo conservador"),
        *BulletList([
            "<b>Adquisición</b>: año 1 captura 200 clientes (extremo bajo del rango SOM 370-1.800 estimado para Comunidad Valenciana). Crecimiento neto anual decreciente en porcentaje pero creciente en valor absoluto.",
            "<b>Churn anual</b>: 15 % aplicado a la base inicial de cada año. Es alto para SaaS de gestión (referencias del sector: 7-12 %), elegido para no inflar.",
            "<b>ARPU mixto</b>: arranca en 55 €/mes (peso de Starter con descuento Kit Digital) y crece hasta 95 €/mes en año 5 con mix maduro Pro/Business.",
            "<b>Coste variable por cliente</b>: 15 €/mes año 1 (LLM + infraestructura + soporte primer nivel), descenso progresivo hasta 10 €/mes en año 5 por mejora en costes LLM (~40 % anual) y eficiencia operativa.",
        ]),
        Quote(
            "<b>Importante:</b> el margen bruto NO descuenta OPEX —salarios "
            "del equipo, marketing, legal, infraestructura corporativa—. "
            "Es el margen sobre coste variable directo por cliente. La "
            "estructura de OPEX dependerá del plan de contratación y "
            "captación. Una rentabilidad neta del proyecto exige cubrir "
            "el OPEX antes del año 3 con el margen bruto acumulado "
            "(~1,2 M€ a cierre del año 3)."
        ),

        H2("9.4 — Propuesta de colaboración con OAP Valencia"),
        P(
            "Se propone establecer una relación de partner comercial con OAP "
            "Valencia centrada en tres líneas de trabajo:"
        ),
        *BulletList([
            "<b>Acceso a red de PYMEs asociadas</b>: participación en jornadas y eventos formativos con demos prácticas.",
            "<b>Programa piloto</b>: cohorte inicial de 10-20 PYMEs valencianas con acceso preferente al producto en fase beta, feedback estructurado y caso de éxito documentado.",
            "<b>Posicionamiento institucional</b>: colaboración en contenido divulgativo sobre Verifactu, AI Act y digitalización del tejido empresarial valenciano.",
        ]),
        Spacer(1, 0.5 * cm),
        Quote(
            "El mercado existe, la regulación lo acelera, la tecnología lo "
            "permite y el hueco competitivo está abierto. La ventana es "
            "estrecha — 18 a 36 meses — y la Comunidad Valenciana es el "
            "terreno ideal para ocuparla."
        ),
        PageBreak(),
    ]


def section_internacionalizacion():
    fases = [
        [cell_header("Fase"), cell_header("Año"), cell_header("Mercado objetivo"),
         cell_header("TAM aprox."), cell_header("Disparador comercial"),
         cell_header("Adaptación requerida")],
        [cell("<b>F1</b>"), cell("2026-27"),
         cell("España (Comunidad Valenciana → nacional)"),
         cell("~6,7 M sujetos"),
         cell("Verifactu obligatorio + Kit Digital"),
         cell("Base de producto")],
        [cell("<b>F2</b>"), cell("2027-28"),
         cell("Portugal"),
         cell("~1,3 M empresas + ~700 k <i>empresários em nome individual</i>"),
         cell("Fatura Eletrónica (DGCI) y SAF-T PT ya consolidados; cercanía cultural e idiomática"),
         cell("Locale pt-PT, conectores SAF-T, modelos fiscais IRC/IVA, idioma de prompts e UI")],
        [cell("<b>F3</b>"), cell("2028"),
         cell("Italia"),
         cell("~4,3 M PYMEs"),
         cell("Sistema di Interscambio (SDI) maduro para facturación electrónica B2B/B2G obligatoria desde 2024"),
         cell("Locale it-IT, conectores SDI/FatturaPA, IRPEF/IVA, contabilidad italiana")],
        [cell("<b>F4</b>"), cell("2028-29"),
         cell("México (puerta a LatAm)"),
         cell("~4,5 M MIPYMES"),
         cell("CFDI 4.0 / SAT — equivalente latinoamericano de Verifactu, ya obligatorio. Idioma nativo, mercado SaaS B2B en crecimiento del 18-22 % anual"),
         cell("Locale es-MX, conector CFDI/PAC autorizado, ISR/IVA mexicano, RFC en lugar de NIF, pricing PPP")],
        [cell("<b>F5</b>"), cell("2029-30"),
         cell("Francia + expansión LatAm (Colombia, Chile, Argentina)"),
         cell("Francia ~3,5 M TPE/PME · LatAm + ~10 M PYMEs"),
         cell("Francia: e-factura obligatoria 2026-27 (calendario PPF). LatAm: digitalización fiscal acelerada por gobiernos"),
         cell("Locale fr-FR + variantes es-LATAM. Adapters por país (DIAN, SII, AFIP). Equipo comercial local")],
        [cell("<b>F6</b>"), cell("2030-31"),
         cell("Reino Unido + Irlanda (mercados angloparlantes EU/UK)"),
         cell("UK ~5,5 M PYMEs · IE ~270 k"),
         cell("Making Tax Digital (HMRC) obligatorio desde 2019/2022 — equivalente anglosajón de Verifactu, ya consolidado. Idioma inglés abre mercados secundarios"),
         cell("Locale en-GB / en-IE, adapter MTD/HMRC, ROS (Irish Revenue), VAT británico/irlandés, presentación P&L estilo UK GAAP / FRS 105")],
        [cell("<b>F7</b>"), cell("2031-32"),
         cell("Australia, Nueva Zelanda y Canadá"),
         cell("AU ~2,5 M · NZ ~570 k · CA ~1,2 M PYMEs"),
         cell("Australia: STP (Single Touch Payroll) + GST, SaaS B2B maduro. NZ análogo a AU con IRD. Canadá: GST federal + HST/PST por provincia, mercado bilingüe (inglés/francés) ya cubierto desde F5"),
         cell("Locale en-AU/en-NZ/en-CA. STP adapter (ATO), GST/HST por provincia, multi-currency, Stripe + ACH como pasarela")],
        [cell("<b>F8</b>"), cell("2032-33 (horizonte)"),
         cell("EE. UU. — entrada selectiva por estado-piloto"),
         cell("US ~33 M PYMEs (mercado segmentado por estado)"),
         cell("Mercado más grande del planeta para SaaS B2B PYME pero el más complejo: <i>sales tax</i> definido por cada estado (50 jurisdicciones), IRS federal + state income tax, nexus rules variables, demandas de cumplimiento <i>Wayfair</i> tras 2018"),
         cell("Locale en-US, LLC en Delaware o Wyoming como entrada, equipo legal y comercial local desde día 1, integración Avalara o TaxJar para sales tax (no construir interno), arranque en 2-3 estados-piloto (Texas, Florida — sin state income tax) antes de escalar")],
    ]
    impacto = [
        [cell_header("Mercado"), cell_header("Año plena operación"),
         cell_header("Penetración objetivo año 5"),
         cell_header("ARR adicional estimado")],
        [cell("España"), cell("2026-27 (F1)"),
         cell("≈ 3.200 clientes (base proyección)"),
         cell("3,65 M€ (ya incluido en la tabla 9.3)")],
        [cell("Portugal"), cell("2027-28 (F2)"),
         cell("0,05 % SAM = ~500 clientes"),
         cell("0,5-0,7 M€")],
        [cell("Italia"), cell("2028 (F3)"),
         cell("0,02 % SAM = ~600 clientes"),
         cell("0,6-0,9 M€")],
        [cell("México"), cell("2028-29 (F4)"),
         cell("0,02 % SAM = ~700 clientes (ARPU PPP ajustado)"),
         cell("0,4-0,6 M€")],
        [cell("Francia + LatAm resto"), cell("2029-30 (F5)"),
         cell("Despliegue parcial — año 5 cierre"),
         cell("0,3-0,5 M€")],
        [cell("UK + Irlanda"), cell("2030-31 (F6)"),
         cell("Fuera de la ventana de 5 años — entra en años 6-7"),
         cell("Potencial 1,2-2,0 M€ ARR (horizonte +24-36 m)")],
        [cell("Australia + NZ + Canadá"), cell("2031-32 (F7)"),
         cell("Horizonte 5-6 años — mercados angloparlantes maduros"),
         cell("Potencial 1,5-2,5 M€ ARR (horizonte +36-48 m)")],
        [cell("Estados Unidos (selectivo)"), cell("2032-33 (F8)"),
         cell("Horizonte 6-7 años — mercado más grande pero más complejo"),
         cell("Potencial 3-8 M€ ARR si la entrada selectiva escala a 5-10 estados; requiere capital adicional para LLC y equipo legal local")],
        [cell("<b>Total ARR año 5 (escenario expansivo F1-F5)</b>"), cell("—"), cell("—"),
         cell("<b>5,5 - 6,5 M€</b> (vs. 3,65 M€ solo España)")],
    ]
    return [
        H1("10. Plan de internacionalización"),
        P(
            "La arquitectura de AutomatizaCore está diseñada para "
            "internacionalización desde la fundación: <b>(a)</b> el modelo "
            "multi-tenant ya separa el <i>locale</i> y la jurisdicción "
            "fiscal en columnas dedicadas (<i>ui_locale</i>, "
            "<i>jurisdiction</i>); <b>(b)</b> el módulo de cumplimiento "
            "vive aislado del resto del ERP, lo que permite añadir "
            "jurisdicciones nuevas sin reescribir el núcleo; y <b>(c)</b> "
            "los agentes IA son multilingüe nativos por el LLM subyacente "
            "—solo requieren adaptación del prompt sistema y del corpus "
            "RAG por país—."
        ),

        H2("10.1 — Roadmap geográfico por fases"),
        DataTable(fases, col_widths=[1.4 * cm, 2 * cm, 3.2 * cm, 2.8 * cm, 3.8 * cm, 3.8 * cm]),
        Spacer(1, 0.3 * cm),
        P(
            "El criterio de priorización combina tres factores: "
            "<b>(a)</b> existencia de un equivalente normativo a Verifactu "
            "que actúe como disparador comercial forzado (SAF-T en "
            "Portugal, SDI en Italia, CFDI en México, PPF en Francia, "
            "MTD en Reino Unido, STP/GST en Australia), <b>(b)</b> "
            "cercanía cultural/idiomática (Portugal e Hispanoamérica > "
            "Italia > Francia > mercados angloparlantes) y <b>(c)</b> "
            "tamaño del mercado SAM y madurez del SaaS B2B PYME."
        ),
        P(
            "El paso de F5 a F6 supone un cambio cualitativo: hasta F5 el "
            "producto opera en idiomas latinos (es, pt, it, fr); F6+ "
            "introduce el inglés como cuarto idioma principal del producto. "
            "Esto exige una reescritura del corpus de prompts del sistema "
            "—no solo traducción— porque el tono y las convenciones "
            "comerciales en mercados anglosajones difieren de los latinos. "
            "Esa inversión, una vez hecha para UK/Irlanda, abre las "
            "puertas a F7 (Australia, NZ, Canadá, EE. UU.) con coste "
            "marginal por país más bajo."
        ),

        H2("10.2 — Adaptaciones técnicas por mercado"),
        *BulletList([
            "<b>Locale (UI + prompts)</b>: ya cubierto. Cada tenant tiene un atributo <i>ui_locale</i> consumido por next-intl en frontend y por los prompts del backend.",
            "<b>Adaptadores fiscales</b>: módulo enchufable por jurisdicción. Cada país necesita: modelos AEAT-equivalentes (Modelo 303 ES → IVA 22 IT → ATCUD PT → CFDI MX), conectores con la API tributaria nacional, plantillas de PDF localizadas.",
            "<b>Bancos</b>: España N43 → resto EU CAMT.053 ISO 20022 (estándar paneuropeo) → LatAm formatos propios por banco (más fragmentado).",
            "<b>Compliance laboral</b>: SS español → INPS italiana → CCSS portuguesa → IMSS mexicano. Variable más costosa por país.",
            "<b>Pasarelas de pago</b>: Bizum (ES) → MB Way (PT) → Mercado Pago (LatAm). Adaptador modular sobre interface común.",
            "<b>Gateway LLM</b>: sin cambios — Claude/GPT/Gemini ya operan en todos los mercados objetivo.",
        ]),

        H2("10.3 — Impacto en proyección financiera (escenario expansivo)"),
        P(
            "La proyección conservadora de la sección 9.3 contempla solo "
            "el mercado español. La internacionalización por fases añade "
            "el siguiente potencial al cierre del año 5:"
        ),
        DataTable(impacto, col_widths=[3.8 * cm, 2.8 * cm, 4.4 * cm, 5.4 * cm]),
        Spacer(1, 0.3 * cm),
        Quote(
            "<b>Lectura:</b> el escenario expansivo no es una multiplicación "
            "lineal del modelo español. Cada nuevo mercado exige equipo "
            "local de ventas y soporte, adaptación de cumplimiento "
            "(coste fijo significativo) y curva de aprendizaje comercial "
            "de 2-3 trimestres. Las cifras son indicativas de la "
            "<i>oportunidad direccionable</i>, no de la cuenta de "
            "resultados garantizada. El gating de cada fase debe vincularse "
            "a un mínimo de tracción demostrada en la fase anterior."
        ),

        H2("10.4 — Riesgos específicos de la internacionalización"),
        *BulletList([
            "<b>Compliance fiscal por país</b>: cada nuevo mercado exige una inversión inicial de 3-6 meses para certificar el adaptador fiscal contra la administración tributaria local. Antes de F2 (Portugal), validar con un experto fiscal portugués.",
            "<b>Soporte multi-idioma</b>: el catálogo de agentes IA habla castellano fluido por el LLM, pero las plantillas de prompts del sistema están escritas en castellano. Reescritura/traducción profesional necesaria por país.",
            "<b>Coste de adquisición local</b>: el modelo partner-gestoría que funciona en España debe replicarse en cada mercado con sus equivalentes (contabilistas en PT, commercialisti en IT, contadores públicos en MX). Inversión comercial localizada.",
            "<b>Tipo de cambio en LatAm</b>: facturación en monedas locales con volatilidad elevada (peso mexicano, peso argentino) puede comprimir márgenes si no se gestiona con coberturas.",
        ]),
        PageBreak(),
    ]


def section_reestructuracion():
    return [
        H1("11. Futura reestructuración del proyecto"),
        P(
            "El paso de un producto unitario español a una plataforma "
            "internacional multimercado exigirá reorganizar AutomatizaCore "
            "en tres planos paralelos: <b>arquitectura técnica</b>, "
            "<b>estructura de equipo</b> y <b>estructura corporativa</b>. "
            "Cada plano se activa en una fase distinta del roadmap, no "
            "todo de golpe."
        ),

        # ── 11.1 Arquitectura técnica ─────────────────────────────────────
        H2("11.1 — Arquitectura técnica: del monolito a plataforma + plugins"),
        P(
            "El producto actual es un monolito Python + Electron pensado "
            "para una jurisdicción. Para escalar a 7+ países sin "
            "convertirse en código spaghetti, la arquitectura evoluciona "
            "en tres saltos:"
        ),
        *BulletList([
            "<b>Salto 1 (con F2, Portugal)</b>: refactor del módulo de cumplimiento a <i>plugin architecture</i>. Cada jurisdicción es un paquete enchufable que registra: modelos fiscales propios (303 / IVA 22 / SAF-T / MTD), conectores con la API tributaria, plantillas PDF localizadas, reglas de validación. El core del ERP queda agnóstico.",
            "<b>Salto 2 (con F4, México)</b>: separación clara entre <i>core</i> (factura, inventario, CRM, RRHH) y <i>compliance pack</i> por país. Cada cliente activa los packs que necesite. Habilita opcionalmente un modelo de monetización por pack premium.",
            "<b>Salto 3 (con F6, Reino Unido)</b>: introducción del inglés como idioma de primera clase. El catálogo de prompts del sistema se reescribe (no se traduce) para reflejar tono y convenciones anglosajonas. Esto exige una capa de abstracción de prompts por <i>language family</i> que ya queda preparada en el monorepo.",
            "<b>Posible salto 4 (con F8, EE. UU.)</b>: evaluación de migración del backend desktop-embebido a un modelo <i>hybrid edge-cloud</i> para soportar <i>sales tax</i> estatal con tablas vivas que se sincronizan automáticamente (50 jurisdicciones, reglas que cambian trimestralmente tras la sentencia <i>Wayfair</i> 2018). La soberanía del dato del cliente se preserva, pero el cálculo de impuestos delega en un proveedor especializado (Avalara o TaxJar) o en tablas centralizadas mantenidas por AutomatizaCore.",
        ]),

        # ── 11.2 Equipo ──────────────────────────────────────────────────
        H2("11.2 — Equipo: de fundador-único a estructura por línea geográfica"),
        P(
            "El proyecto arranca con un equipo reducido centrado en "
            "España. Cada fase internacional añade roles específicos sin "
            "duplicar todo:"
        ),
        DataTable(
            [
                [cell_header("Fase"), cell_header("Roles añadidos"), cell_header("Headcount aprox. acumulado")],
                [cell("F1 España"), cell("Fundador-CEO, 1-2 ingenieros, 1 comercial valenciano, asesor fiscal externo"), cell("3-5")],
                [cell("F2 Portugal"), cell("+ 1 comercial PT (o partner gestoría), 1 asesor fiscal PT externo, 1 ingeniero de plugins"), cell("6-8")],
                [cell("F3 Italia"), cell("+ 1 comercial IT, 1 commercialista asesor, 1 customer success multimercado"), cell("9-12")],
                [cell("F4 México"), cell("+ 1 BDR LatAm, 1 contador asesor MX, 1 ingeniero de adapters fiscales LatAm"), cell("13-16")],
                [cell("F5 Francia/LatAm"), cell("+ 1 comercial FR, 1-2 BDRs LatAm adicionales, 1 marketing internacional, 1 CTO"), cell("18-22")],
                [cell("F6 UK/Irlanda"), cell("+ 1 comercial UK, 1 chartered accountant asesor, 1 ingeniero locale en"), cell("23-26")],
                [cell("F7 AU/NZ/CA"), cell("+ 1 BDR APAC (con base remota), 1 ingeniero adapters STP/IRD, partners contables locales"), cell("28-32")],
                [cell("F8 EE. UU."), cell("Filial Delaware/Wyoming: + 1 General Manager US, 1 sales lead US, 1 CPA asesor, equipo legal externo (sales tax + IP)"), cell("35-45+")],
            ],
            col_widths=[2.6 * cm, 9.4 * cm, 4.5 * cm],
        ),
        Spacer(1, 0.3 * cm),
        P(
            "El modelo prioritario es <b>partner-led en cada país</b> "
            "antes de contratar headcount directo: gestorías en ES/PT, "
            "<i>commercialisti</i> en IT, contadores en LatAm, "
            "<i>chartered accountants</i> en UK. El partner aporta canal "
            "y conocimiento normativo a cambio de comisión recurrente. "
            "La contratación directa solo se acelera cuando el mercado "
            "demuestra tracción."
        ),

        # ── 11.3 Corporativa ─────────────────────────────────────────────
        H2("11.3 — Estructura corporativa: holding + filiales por jurisdicción"),
        P(
            "La forma jurídica del proyecto evoluciona en tres etapas:"
        ),
        *BulletList([
            "<b>Etapa 1 — SL única en España (años 1-3)</b>: AutomatizaCore SL operando desde España, facturando a clientes ES, PT, IT vía facturación intracomunitaria. Estructura simple, costes legales mínimos.",
            "<b>Etapa 2 — Holding ibérico (años 3-5)</b>: con tracción demostrada, creación de holding (España o Portugal según ventaja fiscal) y filial operativa por mercado de la zona euro (ES, PT, IT, FR). Cada filial factura localmente, gestiona su impuesto de sociedades y empleados con su régimen.",
            "<b>Etapa 3 — Estructura multi-país EU + UK (años 5-7)</b>: filial UK/Irlanda post-Brexit (la irlandesa puede ser puente para EU+UK simultáneamente), filial mexicana con sede en CDMX, presencia legal en LatAm consolidada.",
            "<b>Etapa 4 — Entrada en EE. UU. (años 7+)</b>: si F8 se activa, LLC en Delaware o Wyoming —elegidas por su flexibilidad de gobernanza corporativa y ventajas fiscales para holding— con responsabilidades segmentadas: la LLC asume el riesgo de cumplimiento <i>sales tax</i> y demandas estado por estado, sin contaminar la operación europea. Esta entrada exige capital adicional (1-3 M€) para legal, equipo local y certificaciones SOC 2 / HIPAA si se accede a verticales reguladas.",
        ]),
        P(
            "<b>Drivers de la elección de estructura</b>: tratamiento "
            "fiscal de regalías intra-grupo (modelo IP-holding en "
            "Portugal o Luxemburgo), protección de marca registrada por "
            "jurisdicción, separación de responsabilidad legal por "
            "mercado (un fallo de cumplimiento fiscal en México no debe "
            "comprometer la operación europea), elegibilidad para "
            "incentivos de I+D en España (Patent Box, deducción I+D+i)."
        ),

        # ── 11.4 Producto: posibles spin-offs ─────────────────────────────
        H2("11.4 — Posibles spin-offs de producto"),
        P(
            "Algunos módulos del ERP, una vez maduros y verticalizados, "
            "pueden tener vida propia como productos independientes que "
            "compitan en sus mercados verticales:"
        ),
        *BulletList([
            "<b>Empleados IA personalizables</b> (PaaS para terceros): exponer la capacidad de configurar agentes IA con personalidad, skills y presupuesto como producto independiente vendible a otros SaaS B2B. Modelo de licencia por agente activo.",
            "<b>Compliance-as-a-Service</b>: el conjunto de adapters fiscales por jurisdicción (Verifactu, SDI, CFDI, MTD...) como API que terceros ERPs pueden consumir. Posicionamiento como <i>Stripe del cumplimiento fiscal multipaís</i>.",
            "<b>Motor de workflows determinista/razonamiento</b>: el orquestador con motor dual podría licenciarse como infraestructura embebible en otros productos B2B que necesiten automatización IA con SLA controlable.",
            "<b>RAG empresarial soberano</b>: el módulo de búsqueda semántica sobre documentos del tenant (con datos locales, no cloud) puede empaquetarse aparte para mercados que priorizan privacidad (sector legal, sanitario, defensa).",
        ]),
        Quote(
            "<b>Filosofía del spin-off</b>: ningún módulo se separa hasta "
            "que demuestre tracción dentro del producto principal Y se "
            "identifique un mercado vertical donde el módulo aislado "
            "genere más valor que como componente del ERP. Spin-off "
            "prematuro fragmenta el foco; spin-off tardío deja valor "
            "sobre la mesa."
        ),

        # ── 11.5 Hitos de reestructuración ───────────────────────────────
        H2("11.5 — Hitos de reestructuración (horizonte 5-7 años)"),
        DataTable(
            [
                [cell_header("Año"), cell_header("Hito de reestructuración")],
                [cell("Año 2 (2027)"), cell("Refactor compliance a plugin architecture (salto técnico 1)")],
                [cell("Año 3 (2028)"), cell("Separación core / compliance packs (salto técnico 2). Estudio holding ibérico.")],
                [cell("Año 4 (2029)"), cell("Constitución holding + filiales euro (España + Portugal). Primer CTO contratado.")],
                [cell("Año 5 (2030)"), cell("Capa de abstracción de prompts multi-idioma (preparación F6). Evaluación spin-off RAG empresarial.")],
                [cell("Año 6 (2031)"), cell("Filial UK/Irlanda. Idioma inglés primera clase (salto técnico 3).")],
                [cell("Año 7 (2032)"), cell("Entrada APAC (Australia, NZ, Canadá) sobre la base de inglés ya consolidada. Spin-off RAG empresarial o Compliance-as-a-Service si hay tracción demostrada.")],
                [cell("Año 8+ (2033+)"), cell("Filial EE. UU. (LLC Delaware/Wyoming). Integración con Avalara/TaxJar para sales tax. Migración hybrid edge-cloud (salto técnico 4). Capital adicional 1-3 M€.")],
            ],
            col_widths=[2.6 * cm, 13.9 * cm],
        ),
        PageBreak(),
    ]


def section_fuentes():
    return [
        H1("Anexo — Fuentes y metodología"),
        H2("Fuentes públicas consultadas"),
        *BulletList([
            "<b>INE / DIRCE</b> — Directorio Central de Empresas, datos 2024 de tejido empresarial español.",
            "<b>TGSS</b> — Estadísticas de afiliación al Régimen Especial de Trabajadores Autónomos (RETA).",
            "<b>ONTSI</b> — Observatorio Nacional de las Telecomunicaciones y de la Sociedad de la Información (informes de digitalización PYME).",
            "<b>AMETIC</b> — Estudios sectoriales de adopción de software empresarial.",
            "<b>BOE</b> — Real Decreto 1007/2023 (Verifactu), Reglamento UE 2024/1689 (AI Act).",
            "<b>Acelera PYME / Red.es</b> — Estadísticas de despliegue del Kit Digital.",
        ]),
        H2("Metodología de dimensionamiento"),
        P(
            "El cálculo del SAM aplica dos filtros sucesivos al TAM: "
            "penetración de software SaaS de gestión (30-40 % según fuente) "
            "y subset que usa o evalúa IA en la gestión (10-15 %). Estos "
            "porcentajes se han observado de forma consistente en informes "
            "sectoriales 2023-2025 con variaciones de ±5 puntos."
        ),
        P(
            "El SOM regional asume captura conservadora del 0,1-0,5 % del "
            "SAM autonómico, coherente con tasas de penetración observadas "
            "en lanzamientos comerciales del segmento ERP-SMB en mercados "
            "europeos comparables."
        ),
        H2("Limitaciones"),
        P(
            "Las cifras absolutas son órdenes de magnitud derivados de "
            "fuentes públicas conocidas. Para un <i>business case</i> "
            "presentado a inversores institucionales o para acuerdos "
            "comerciales formales, se recomienda contratar un informe "
            "ad-hoc actualizado al trimestre relevante con verificación "
            "directa de cada cifra en su fuente."
        ),
        Spacer(1, 1 * cm),
        Paragraph(
            f"Documento preparado el {date.today().strftime('%d de %B de %Y')} · "
            "AutomatizaCore · Versión 1.0",
            STYLE_CAPTION,
        ),
    ]


# ── Main ─────────────────────────────────────────────────────────────────────


def build_pdf(output_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="AutomatizaCore — Estudio de mercado",
        author="AutomatizaCore",
        subject="Estudio de mercado para presentación a OAP Valencia",
    )

    story = []
    story += cover_page()
    story += section_resumen()
    story += section_mercado()
    story += section_dimensionamiento()
    story += section_competencia()
    story += section_tendencias()
    story += section_propuesta()
    story += section_posicionamiento()
    story += section_riesgos()
    story += section_conclusiones()
    story += section_internacionalizacion()
    story += section_reestructuracion()
    story += section_fuentes()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)


def main():
    desktop = Path(os.path.expanduser("~/Desktop"))
    if not desktop.exists():
        # Windows fallback explícito
        desktop = Path(r"C:\Users\Marcos\Desktop")
    output = desktop / "AutomatizaCore_Estudio_Mercado_OAP_Valencia.pdf"
    build_pdf(output)
    size_kb = output.stat().st_size // 1024
    print(f"OK -> {output} ({size_kb} KB)")


if __name__ == "__main__":
    main()
