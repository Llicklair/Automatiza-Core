"""
Chunking inteligente basado en estructura del documento.

A diferencia del chunking mecánico (cortar cada N chars), este módulo:
- Respeta límites de secciones (headings)
- Mantiene tablas como chunks atómicos (nunca se cortan)
- Preserva metadata por chunk (página, tipo, bounding box)
"""

import logging
from dataclasses import dataclass, field

from app.services.pdf.parser import ParsedElement

logger = logging.getLogger(__name__)

MAX_CHUNK_SIZE = 2000  # chars por chunk
MIN_CHUNK_SIZE = 100  # no crear chunks triviales


@dataclass
class Chunk:
    """Un chunk listo para embeddings con metadata."""

    text: str
    page_number: int = 0
    element_type: str = "mixed"  # paragraph, table, heading, mixed
    bounding_box: list = field(default_factory=list)


def smart_chunk(elements: list[ParsedElement], max_chunk_size: int = MAX_CHUNK_SIZE) -> list[Chunk]:
    """
    Crea chunks inteligentes a partir de elementos estructurados del PDF.

    Reglas:
    1. Tablas → siempre un chunk propio (nunca se cortan)
    2. Headings → inician un nuevo chunk
    3. Párrafos consecutivos → se agrupan hasta max_chunk_size
    4. Elementos muy largos → se dividen respetando saltos de línea

    Args:
        elements: Lista de ParsedElement del parser.
        max_chunk_size: Tamaño máximo por chunk en caracteres.

    Returns:
        Lista de Chunk con texto y metadata.
    """
    if not elements:
        return []

    chunks: list[Chunk] = []
    buffer_text = ""
    buffer_page = 0
    buffer_type = "mixed"
    buffer_bbox = []

    def flush_buffer():
        nonlocal buffer_text, buffer_page, buffer_type, buffer_bbox
        text = buffer_text.strip()
        if len(text) >= MIN_CHUNK_SIZE:
            chunks.append(
                Chunk(
                    text=text,
                    page_number=buffer_page,
                    element_type=buffer_type,
                    bounding_box=buffer_bbox,
                )
            )
        buffer_text = ""
        buffer_bbox = []

    for elem in elements:
        text = elem.text.strip()
        if not text:
            continue

        # Tablas: siempre chunk propio
        if elem.element_type == "table":
            flush_buffer()
            # Si la tabla es muy grande, la dividimos por filas
            if len(text) > max_chunk_size:
                for sub in _split_large_text(text, max_chunk_size):
                    chunks.append(
                        Chunk(
                            text=sub,
                            page_number=elem.page_number,
                            element_type="table",
                            bounding_box=elem.bounding_box,
                        )
                    )
            else:
                chunks.append(
                    Chunk(
                        text=text,
                        page_number=elem.page_number,
                        element_type="table",
                        bounding_box=elem.bounding_box,
                    )
                )
            continue

        # Headings: inician nuevo chunk
        if elem.element_type == "heading" or elem.heading_level > 0:
            flush_buffer()
            buffer_text = text + "\n"
            buffer_page = elem.page_number
            buffer_type = "heading"
            buffer_bbox = elem.bounding_box
            continue

        # Párrafos y otros: agrupar hasta max_chunk_size
        if len(buffer_text) + len(text) + 1 > max_chunk_size:
            flush_buffer()

        if not buffer_text:
            buffer_page = elem.page_number
            buffer_type = elem.element_type
            buffer_bbox = elem.bounding_box

        buffer_text += text + "\n"

    flush_buffer()

    # Si no se generaron chunks (ej: todos los elementos muy cortos), crear uno con todo
    if not chunks and elements:
        full_text = "\n".join(e.text.strip() for e in elements if e.text.strip())
        if full_text:
            for sub in _split_large_text(full_text, max_chunk_size):
                chunks.append(Chunk(text=sub, page_number=elements[0].page_number))

    return chunks


def _split_large_text(text: str, max_size: int) -> list[str]:
    """Divide texto largo respetando saltos de línea cuando es posible."""
    if len(text) <= max_size:
        return [text]

    parts = []
    lines = text.split("\n")
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > max_size:
            if current.strip():
                parts.append(current.strip())
            # Si una línea sola es mayor que max_size, cortarla
            if len(line) > max_size:
                for i in range(0, len(line), max_size):
                    parts.append(line[i : i + max_size])
                current = ""
            else:
                current = line + "\n"
        else:
            current += line + "\n"

    if current.strip():
        parts.append(current.strip())

    return parts
