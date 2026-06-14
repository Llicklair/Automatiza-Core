"""Render de informes PDF desde markdown (markdown-it → HTML → xhtml2pdf).

El LLM emite markdown; se convierte a HTML y se renderiza con xhtml2pdf usando un
stylesheet corporativo embebido (portada, H2 con underline, tablas zebra,
blockquotes coloreados según prefijo).
"""

from __future__ import annotations

import html as _html
import io
import os
import re as _re

_PDF_STYLESHEET = """
@page {
  size: A4;
  margin: 28mm 18mm 22mm 18mm;
  @frame header_frame {
    -pdf-frame-content: header_content;
    left: 18mm; right: 18mm; top: 12mm; height: 10mm;
  }
  @frame footer_frame {
    -pdf-frame-content: footer_content;
    left: 18mm; right: 18mm; bottom: 8mm; height: 10mm;
  }
}
@page first_page {
  size: A4;
  margin: 22mm 18mm 22mm 18mm;
  @frame footer_frame_cover {
    -pdf-frame-content: footer_content;
    left: 18mm; right: 18mm; bottom: 8mm; height: 10mm;
  }
}
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.55; color: #1e293b; }

/* Portada */
.cover { -pdf-page-template: first_page; padding-top: 38mm;
         page-break-after: always; }
.cover .logo { margin-bottom: 14mm; }
.cover .logo img { max-width: 56mm; max-height: 24mm; }
.cover .badge { display: inline; color: #6366f1; font-size: 8.5pt;
                font-weight: bold; letter-spacing: 2pt;
                background: #eef2ff; padding: 4pt 10pt;
                border-radius: 2pt; }
.cover h1 { font-size: 28pt; color: #1e293b; font-weight: bold;
            margin: 14pt 0 6pt 0; padding-bottom: 10pt;
            border-bottom: 1.4pt solid #6366f1;
            line-height: 1.15; }
.cover .subtitle { color: #64748b; font-size: 14pt; font-style: italic;
                   margin: 0 0 30pt 0; }
.cover .meta { color: #64748b; font-size: 10pt; line-height: 1.8;
               background: #f8fafc; padding: 14pt 16pt;
               border-left: 2.5pt solid #6366f1; }
.cover .meta b { color: #1e293b; }
.cover .footnote { position: absolute; bottom: 0;
                   color: #94a3b8; font-size: 8pt; font-style: italic;
                   margin-top: 30mm; }

/* Header de páginas interiores */
.page-header { color: #94a3b8; font-size: 8pt;
               border-bottom: 0.3pt solid #e2e8f0;
               padding-bottom: 3pt; }
.page-header b { color: #6366f1; }

/* Cuerpo */
h1 { font-size: 19pt; color: #1e293b; margin-top: 14pt;
     margin-bottom: 6pt; }
h2 { font-size: 15pt; color: #1e293b; margin-top: 22pt;
     margin-bottom: 6pt; padding-bottom: 4pt;
     border-bottom: 0.6pt solid #e2e8f0; }
h3 { font-size: 12pt; color: #6366f1; margin-top: 14pt;
     margin-bottom: 4pt; }
p { margin: 0 0 8pt 0; text-align: justify; }
strong, b { color: #1e293b; }

/* Listas */
ul, ol { padding-left: 22pt; margin: 4pt 0 12pt 0; }
li { margin-bottom: 4pt; }

/* Tablas — xhtml2pdf no soporta border-collapse ni :nth-child;
   se usan padding y borders en cada celda. */
table { width: 100%; margin: 10pt 0 16pt 0; }
thead th { background: #f8fafc; color: #64748b; font-weight: bold;
           font-size: 9pt; padding: 8pt 10pt;
           border-bottom: 1.2pt solid #64748b;
           text-align: left; }
tbody td { padding: 7pt 10pt;
           border-bottom: 0.3pt solid #e2e8f0;
           font-size: 9.5pt; vertical-align: middle; }

/* Blockquotes — callouts coloreados según prefijo del primer párrafo:
   "Nota:" → azul info, "Aviso:" → ámbar warning, "Recomendación:" → verde,
   "Importante:" → rojo. Default → ámbar. */
blockquote { border-left: 3pt solid #f59e0b; background: #fffbeb;
             padding: 8pt 12pt; margin: 10pt 0;
             color: #92400e; font-style: italic; }
blockquote.info { border-left-color: #3b82f6; background: #eff6ff;
                  color: #1e40af; }
blockquote.success { border-left-color: #10b981; background: #ecfdf5;
                     color: #065f46; }
blockquote.danger { border-left-color: #ef4444; background: #fef2f2;
                    color: #991b1b; }
blockquote p { margin: 0; }

/* Línea horizontal */
hr { background-color: #e2e8f0; height: 0.4pt; margin: 16pt 0;
     border: none; }

/* Code inline */
code { font-family: Courier; background: #f1f5f9;
       padding: 1pt 3pt; font-size: 9pt; }

/* Footer */
.footer-content { padding-top: 4pt;
                  border-top: 0.3pt solid #e2e8f0;
                  text-align: center;
                  color: #94a3b8; font-size: 7.5pt; }
.footer-content .accent { color: #6366f1; font-weight: bold; }
"""


def _classify_blockquotes(html_body: str) -> str:
    """Detecta el tipo de callout en cada blockquote según el prefijo del texto.
    Añade class="info|warning|success|danger" para que el CSS lo coloree.
    """
    pattern = _re.compile(r"<blockquote>(.*?)</blockquote>", _re.DOTALL)

    def repl(m: _re.Match) -> str:
        body = m.group(1)
        plain = _re.sub(r"<[^>]+>", "", body).strip().lower()
        if plain.startswith(("nota:", "info:", "información:", "informacion:")):
            cls = "info"
        elif plain.startswith(("aviso:", "atención:", "atencion:", "warning:")):
            cls = ""  # default ámbar ya
        elif plain.startswith(("recomendación:", "recomendacion:", "consejo:", "tip:")):
            cls = "success"
        elif plain.startswith(("importante:", "peligro:", "riesgo:", "alerta:")):
            cls = "danger"
        else:
            cls = ""
        if cls:
            return f'<blockquote class="{cls}">{body}</blockquote>'
        return m.group(0)

    return pattern.sub(repl, html_body)


def render_markdown_report(
    title: str,
    body: str,
    author: str = "Asistente IA",
    subtitle: str | None = None,
    tenant_name: str = "",
    logo_path: str | None = None,
) -> bytes:
    """Renderiza un PDF a partir de un body en markdown usando xhtml2pdf + CSS.

    Args:
        title: título del informe (aparece en portada).
        body: cuerpo en markdown estándar (CommonMark).
        author: firma del informe.
        subtitle: subtítulo opcional bajo el título de la portada.
        tenant_name: nombre de la empresa (aparece en portada y footer).
        logo_path: ruta absoluta a una imagen (PNG/JPG); si existe, se dibuja
                   en la portada.
    """
    try:
        from markdown_it import MarkdownIt
        from xhtml2pdf import pisa
    except ImportError as e:
        raise RuntimeError(
            "Falta dependencia para PDF (markdown-it-py o xhtml2pdf): " + str(e)
        ) from e

    from datetime import date as _date

    # commonmark base + tablas GFM. Sin linkify (no instalado).
    md = MarkdownIt("commonmark", {"html": False, "breaks": False, "linkify": False}).enable("table")
    body_html = md.render(body or "")
    body_html = _classify_blockquotes(body_html)

    today = _date.today().strftime("%d/%m/%Y")

    # Sanitizar campos del usuario (escape HTML en strings de portada)
    safe_title = _html.escape(title or "Informe")
    safe_subtitle = _html.escape(subtitle or "") if subtitle else ""
    safe_author = _html.escape(author or "Asistente IA")
    safe_tenant = _html.escape(tenant_name or "")

    logo_html = ""
    if logo_path and os.path.exists(logo_path):
        # Path absoluto entre comillas; xhtml2pdf lo resuelve via link_callback
        logo_html = f'<div class="logo"><img src="{_html.escape(logo_path)}" /></div>'

    subtitle_html = f'<p class="subtitle">{safe_subtitle}</p>' if safe_subtitle else ""

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>{_PDF_STYLESHEET}</style>
</head>
<body>
  <div id="header_content">
    <div class="page-header">
      <b>{safe_title}</b>
    </div>
  </div>
  <div id="footer_content">
    <div class="footer-content">
      {safe_tenant + ' &middot; ' if safe_tenant else ''}<span class="accent">P&aacute;gina <pdf:pagenumber/></span> &middot; Generado por {safe_author}
    </div>
  </div>

  <div class="cover">
    {logo_html}
    <p><span class="badge">INFORME</span></p>
    <h1>{safe_title}</h1>
    {subtitle_html}
    <p class="meta">
      <b>Empresa:</b> {safe_tenant or 'AutomatizaCore'}<br/>
      <b>Autor:</b> {safe_author}<br/>
      <b>Fecha:</b> {today}
    </p>
  </div>

  {body_html}
</body>
</html>
"""

    def _link_callback(uri: str, rel: str) -> str:
        # xhtml2pdf llama a esto para resolver paths de imágenes/recursos.
        # Devolvemos el path tal cual si existe localmente.
        if os.path.exists(uri):
            return uri
        return uri

    buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        full_html,
        dest=buffer,
        encoding="utf-8",
        link_callback=_link_callback,
    )
    if pisa_status.err:
        raise RuntimeError(
            f"xhtml2pdf falló al generar el PDF ({pisa_status.err} errores)"
        )
    return buffer.getvalue()
