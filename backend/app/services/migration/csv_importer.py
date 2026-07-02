"""Importador CSV genérico (MIG.1).

Fallback universal — cualquier ERP exporta a CSV o Excel. El usuario sube
un archivo y mapea sus columnas a los campos canónicos (`nif`, `name`,
`date`, `amount`, etc.). El wizard (MIG.3) usa este parser para previsualizar
las primeras 10 filas y persistir tras confirmación.

Soporta dos tipos de import en MVP:
- `clients` — clientes / proveedores.
- `invoices` — facturas emitidas (cabecera; las líneas no se importan en MVP).

Detección automática de:
- Separador (`,` o `;`).
- BOM UTF-8.
- Encoding (UTF-8 con fallback a Latin-1).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Literal

ImportKind = Literal["clients", "invoices"]


# Mapeo canónico → posibles cabeceras CSV. Detección case-insensitive y
# normalizada (sin acentos / espacios).
CANONICAL_HEADERS: dict[ImportKind, dict[str, tuple[str, ...]]] = {
    "clients": {
        "nif": ("nif", "cif", "dni", "tax_id", "vat_number", "cif_nif"),
        "name": ("name", "nombre", "razon_social", "company_name", "cliente"),
        "email": ("email", "correo", "e_mail"),
        "phone": ("phone", "telefono", "tel", "movil"),
        "address": ("address", "direccion", "domicilio"),
    },
    "invoices": {
        "invoice_number": ("invoice_number", "numero", "num", "n_factura", "number"),
        "date": ("date", "fecha", "fecha_emision"),
        "client_nif": ("client_nif", "nif_cliente", "cif_cliente", "cliente_nif"),
        "client_name": ("client_name", "nombre_cliente", "cliente"),
        "amount_base": ("amount_base", "base", "base_imponible", "subtotal"),
        "tax_amount": ("tax_amount", "iva", "tax", "impuesto"),
        "amount_total": ("amount_total", "total", "importe", "amount"),
    },
}


@dataclass
class ImportRow:
    """Una fila parseada del CSV. `raw` conserva el dict original para debug."""

    canonical: dict[str, str | Decimal | None]
    raw: dict[str, str]
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportPreview:
    kind: ImportKind
    detected_separator: str
    detected_encoding: str
    header_mapping: dict[str, str]  # canonical → CSV header detected
    unmapped_headers: list[str]
    total_rows: int
    rows_sample: list[ImportRow]
    errors_count: int


def _normalize_header(h: str) -> str:
    out = h.strip().lower()
    for a, b in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n")):
        out = out.replace(a, b)
    return out.replace(" ", "_").replace("-", "_")


def _detect_separator(sample: str) -> str:
    """Detecta `,` o `;` por mayor frecuencia en la primera línea."""
    first_line = sample.split("\n", 1)[0]
    return ";" if first_line.count(";") > first_line.count(",") else ","


def _decode_with_fallback(blob: bytes) -> tuple[str, str]:
    """Intenta UTF-8, cae a Latin-1. Devuelve (texto, encoding usado)."""
    if blob.startswith(b"\xef\xbb\xbf"):
        return blob[3:].decode("utf-8"), "utf-8-sig"
    try:
        return blob.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return blob.decode("latin-1"), "latin-1"


def _build_header_mapping(csv_headers: list[str], kind: ImportKind) -> tuple[dict[str, str], list[str]]:
    """Mapea cada cabecera CSV a un campo canónico (o no la mapea).

    Devuelve `(canonical_to_csv_header, unmapped_csv_headers)`.
    """
    catalog = CANONICAL_HEADERS[kind]
    norm_to_orig = {_normalize_header(h): h for h in csv_headers}
    mapping: dict[str, str] = {}
    for canonical, candidates in catalog.items():
        for cand in candidates:
            if cand in norm_to_orig:
                mapping[canonical] = norm_to_orig[cand]
                break
    unmapped = [h for n, h in norm_to_orig.items() if h not in mapping.values()]
    return mapping, unmapped


def _parse_decimal(value: str) -> Decimal | None:
    """Parsea string a Decimal — admite `1.234,56` y `1234.56`."""
    if not value or not value.strip():
        return None
    cleaned = value.strip().replace(" ", "")
    # Si tiene coma y punto: el último es separador decimal
    if "," in cleaned and "." in cleaned:
        if cleaned.rindex(",") > cleaned.rindex("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None


def parse_csv(blob: bytes, kind: ImportKind, *, max_rows: int | None = None) -> ImportPreview:
    """Parsea un blob CSV y devuelve un `ImportPreview` con primeras filas.

    Si `max_rows` se proporciona, solo se parsean las primeras N filas (útil
    para preview rápida del wizard, MIG.3). Si es `None`, parsea todas.
    """
    text, encoding = _decode_with_fallback(blob)
    separator = _detect_separator(text)

    reader = csv.DictReader(io.StringIO(text), delimiter=separator)
    csv_headers = reader.fieldnames or []
    mapping, unmapped = _build_header_mapping(csv_headers, kind)

    rows_sample: list[ImportRow] = []
    total = 0
    errors_count = 0

    for raw in reader:
        total += 1
        canonical: dict[str, str | Decimal | None] = {}
        errors: list[str] = []
        for cf, csv_header in mapping.items():
            value = (raw.get(csv_header) or "").strip()
            if cf.endswith("_amount") or cf == "amount_base" or cf == "amount_total" or cf == "tax_amount":
                parsed = _parse_decimal(value)
                if value and parsed is None:
                    errors.append(f"{cf}: no se puede parsear '{value}'")
                canonical[cf] = parsed
            else:
                canonical[cf] = value or None

        # Validaciones MIG.1 básicas
        if kind == "clients" and not canonical.get("nif") and not canonical.get("name"):
            errors.append("fila vacía o sin NIF ni nombre")
        if kind == "invoices" and not canonical.get("invoice_number"):
            errors.append("falta número de factura")

        if errors:
            errors_count += 1

        if max_rows is None or len(rows_sample) < max_rows:
            rows_sample.append(ImportRow(canonical=canonical, raw=raw, errors=errors))

    return ImportPreview(
        kind=kind,
        detected_separator=separator,
        detected_encoding=encoding,
        header_mapping=mapping,
        unmapped_headers=unmapped,
        total_rows=total,
        rows_sample=rows_sample,
        errors_count=errors_count,
    )
