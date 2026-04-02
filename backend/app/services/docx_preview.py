"""Vista previa de plantillas .docx → HTML (mammoth) + detección de variables docxtpl.

Solo lectura; no modifica el archivo. Si mammoth no está instalado, el endpoint
devolverá error 501 con mensaje claro.
"""
from __future__ import annotations

import re
from pathlib import Path

# Variables estilo docxtpl: {{ nombre_variable }}
_VAR_PATTERN = re.compile(r"\{\{([^}]+)\}\}")


def extract_variables_from_html(html: str) -> list[str]:
    """Devuelve nombres de variable únicos (sin llaves), ordenados."""
    found = _VAR_PATTERN.findall(html)
    # Normalizar espacios en claves
    cleaned = [f.strip() for f in found if f.strip()]
    return sorted(set(cleaned))


def highlight_variables_in_html(html: str) -> str:
    """Envuelve cada `{{...}}` en un span para resaltado en el cliente."""

    def _wrap(m: re.Match[str]) -> str:
        inner = m.group(0)
        return (
            '<span class="apx-docx-var" style="background:rgba(251,191,36,0.15);'
            "color:#fbbf24;font-family:ui-monospace,monospace;font-size:0.9em;"
            f'border-radius:3px;padding:0 2px;">{inner}</span>'
        )

    return _VAR_PATTERN.sub(_wrap, html)


def docx_to_preview_html(file_path: str) -> dict:
    """Convierte .docx a HTML y extrae variables.

    Returns:
        dict con keys: html (str), variables_detected (list[str]), warnings (list[str])

    Raises:
        ImportError: si mammoth no está instalado
        FileNotFoundError: si no existe el archivo
        ValueError: si la extensión no es .docx o la conversión falla
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(file_path)

    ext = path.suffix.lower()
    if ext != ".docx":
        raise ValueError(
            "La vista previa HTML solo está disponible para archivos .docx. "
            "Para .doc/.odt usa «Abrir en Word» (app escritorio)."
        )

    import mammoth

    with open(path, "rb") as f:
        result = mammoth.convert_to_html(f)

    html = result.value or ""
    warnings = [str(m) for m in (result.messages or [])]

    variables = extract_variables_from_html(html)
    html_highlighted = highlight_variables_in_html(html)

    return {
        "html": html_highlighted,
        "variables_detected": variables,
        "warnings": warnings,
    }
