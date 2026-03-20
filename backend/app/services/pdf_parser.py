"""
Servicio de parsing de PDFs con OpenDataLoader.

Usa OpenDataLoader como parser principal (mejor extracción de tablas, OCR, estructura).
Fallback automático a pypdf si OpenDataLoader no está disponible (ej: JVM ausente).
"""
import io
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ParsedElement:
    """Un elemento extraído del PDF (párrafo, tabla, heading, etc.)."""
    text: str
    element_type: str = "paragraph"  # paragraph, table, heading, list, image, formula
    page_number: int = 0
    heading_level: int = 0
    bounding_box: list = field(default_factory=list)  # [left, bottom, right, top]


@dataclass
class ParsedDocument:
    """Resultado del parsing de un PDF."""
    markdown: str  # Texto completo en markdown
    elements: list[ParsedElement] = field(default_factory=list)
    total_pages: int = 0
    parser_used: str = "unknown"  # "opendataloader" o "pypdf"


def _ensure_java():
    """Configura JAVA_HOME si el JRE portable de Electron está disponible."""
    if os.environ.get("JAVA_HOME"):
        return True
    # Buscar JRE portable en APPDATA (descargado por jre-manager.js)
    appdata = os.environ.get("APPDATA", "")
    jre_path = os.path.join(appdata, "AutomatizaPyme", "jre")
    java_exe = os.path.join(jre_path, "bin", "java.exe")
    if os.path.exists(java_exe):
        os.environ["JAVA_HOME"] = jre_path
        os.environ["PATH"] = os.path.join(jre_path, "bin") + os.pathsep + os.environ.get("PATH", "")
        return True
    return False


def _parse_with_opendataloader(file_path: str) -> ParsedDocument | None:
    """Intenta parsear con OpenDataLoader. Retorna None si no disponible."""
    if not _ensure_java():
        logger.info("Java no disponible, usando fallback pypdf")
        return None
    try:
        import opendataloader_pdf
    except ImportError:
        logger.info("opendataloader-pdf no instalado, usando fallback pypdf")
        return None

    tmp_dir = tempfile.mkdtemp(prefix="odl_")
    try:
        opendataloader_pdf.convert(
            input_path=[file_path],
            output_dir=tmp_dir,
            format="markdown,json",
        )

        # Buscar archivos generados
        tmp_path = Path(tmp_dir)
        md_files = list(tmp_path.rglob("*.md"))
        json_files = list(tmp_path.rglob("*.json"))

        if not md_files:
            logger.warning("OpenDataLoader no generó archivo markdown")
            return None

        markdown_text = md_files[0].read_text(encoding="utf-8")
        elements = []
        total_pages = 0

        # Parsear JSON para metadata estructurada
        if json_files:
            try:
                raw_json = json.loads(json_files[0].read_text(encoding="utf-8"))
                items = raw_json if isinstance(raw_json, list) else raw_json.get("elements", raw_json.get("items", []))
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    content = item.get("content", item.get("text", "")).strip()
                    if not content:
                        continue
                    page = item.get("page_number", item.get("page", 0))
                    if page > total_pages:
                        total_pages = page
                    elements.append(ParsedElement(
                        text=content,
                        element_type=item.get("type", "paragraph"),
                        page_number=page,
                        heading_level=item.get("heading_level", 0),
                        bounding_box=item.get("bounding_box", item.get("bbox", [])),
                    ))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning("Error parseando JSON de OpenDataLoader: %s", e)

        # Si no se pudo parsear JSON, crear elementos desde markdown
        if not elements and markdown_text.strip():
            elements.append(ParsedElement(text=markdown_text, element_type="paragraph"))

        return ParsedDocument(
            markdown=markdown_text,
            elements=elements,
            total_pages=total_pages or max((e.page_number for e in elements), default=1),
            parser_used="opendataloader",
        )
    except Exception as e:
        logger.warning("Error en OpenDataLoader: %s — usando fallback pypdf", e)
        return None
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _parse_with_pypdf(file_path: str = None, file_bytes: bytes = None) -> ParsedDocument:
    """Fallback: parsea con pypdf (sin límite de 8 páginas)."""
    from pypdf import PdfReader

    if file_bytes:
        reader = PdfReader(io.BytesIO(file_bytes))
    else:
        reader = PdfReader(file_path)

    elements = []
    pages_text = []

    for i, page in enumerate(reader.pages, 1):
        text = (page.extract_text() or "").strip()
        if text:
            pages_text.append(text)
            elements.append(ParsedElement(
                text=text,
                element_type="paragraph",
                page_number=i,
            ))

    return ParsedDocument(
        markdown="\n\n".join(pages_text),
        elements=elements,
        total_pages=len(reader.pages),
        parser_used="pypdf",
    )


def parse_pdf(file_path: str = None, file_bytes: bytes = None) -> ParsedDocument:
    """
    Parsea un PDF usando OpenDataLoader (preferido) o pypdf (fallback).

    Args:
        file_path: Ruta al archivo PDF en disco.
        file_bytes: Bytes del PDF (alternativa a file_path).

    Returns:
        ParsedDocument con markdown, elementos estructurados y metadata.
    """
    # Intentar OpenDataLoader (necesita archivo en disco)
    if file_path and os.path.exists(file_path):
        result = _parse_with_opendataloader(file_path)
        if result:
            return result

    # Si solo tenemos bytes y OpenDataLoader no funcionó, guardar temporalmente
    if file_bytes and not file_path:
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            tmp.write(file_bytes)
            tmp.close()
            result = _parse_with_opendataloader(tmp.name)
            if result:
                return result
        finally:
            os.unlink(tmp.name)

    # Fallback a pypdf
    try:
        return _parse_with_pypdf(file_path=file_path, file_bytes=file_bytes)
    except Exception as e:
        logger.error("Error en pypdf fallback: %s", e)
        return ParsedDocument(markdown="", elements=[], total_pages=0, parser_used="error")
