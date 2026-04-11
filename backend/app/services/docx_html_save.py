"""Persistir HTML editado en el navegador como .docx (htmldocx + python-docx).

La conversión es aproximada: estilos complejos del Word original pueden perderse.
Recomendado para ajustes de texto; ediciones profundas → «Abrir en Word».
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_HTML_BYTES = 6 * 1024 * 1024  # 6 MB


def save_html_as_docx(html: str, file_path: str) -> None:
    """Sobrescribe el .docx con el contenido generado desde HTML.

    Raises:
        ImportError: si htmldocx / python-docx no están instalados
        ValueError: HTML vacío o demasiado grande
        OSError: fallo de disco
    """
    if not html or not html.strip():
        raise ValueError("El HTML no puede estar vacío")

    raw = html.encode("utf-8")
    if len(raw) > MAX_HTML_BYTES:
        raise ValueError("HTML demasiado grande (máx. 6 MB)")

    try:
        from docx import Document
        from htmldocx import HtmlToDocx
    except ImportError as e:
        raise ImportError("htmldocx no disponible. Ejecuta: pip install htmldocx") from e

    path = Path(file_path)
    if path.suffix.lower() != ".docx":
        raise ValueError("Solo se puede guardar sobre archivos .docx")

    path.parent.mkdir(parents=True, exist_ok=True)

    # Copia de seguridad única antes de sobrescribir
    if path.is_file():
        try:
            shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
        except OSError as e:
            logger.warning("No se pudo crear .bak de %s: %s", path, e)

    document = Document()
    HtmlToDocx().add_html_to_document(html, document)
    document.save(str(path))
