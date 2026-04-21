"""Operaciones de archivo: validación, clasificación, guardado y extracción ZIP."""

import io
import mimetypes
import os
import uuid
import zipfile

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".odt",
    ".txt",
    ".md",
    ".xlsx",
    ".xls",
    ".csv",
    ".ods",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".bmp",
    ".tiff",
    ".tif",
    ".eml",
    ".msg",
    ".zip",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# ── Clasificación automática ─────────────────────────────────────────────────

_EXT_CATEGORY_MAP: dict[str, str] = {
    ".xlsx": "excels",
    ".xls": "excels",
    ".csv": "excels",
    ".ods": "excels",
    ".pdf": "facturas",
    ".docx": "otros",
    ".doc": "otros",
    ".odt": "otros",
    ".png": "otros",
    ".jpg": "otros",
    ".jpeg": "otros",
    ".webp": "otros",
    ".gif": "otros",
    ".bmp": "otros",
    ".tiff": "otros",
    ".tif": "otros",
    ".txt": "otros",
    ".md": "otros",
    ".eml": "correos",
    ".msg": "correos",
}

_MIME_CATEGORY_MAP: dict[str, str] = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excels",
    "application/vnd.ms-excel": "excels",
    "text/csv": "excels",
    "application/pdf": "facturas",
    "message/rfc822": "correos",
    "application/vnd.ms-outlook": "correos",
}


def auto_classify_category(filename: str, content_type: str | None) -> str:
    """Clasifica la categoría inicial de un archivo por extensión y MIME."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in _EXT_CATEGORY_MAP:
        return _EXT_CATEGORY_MAP[ext]
    if content_type and content_type in _MIME_CATEGORY_MAP:
        return _MIME_CATEGORY_MAP[content_type]
    if content_type and content_type.startswith("image/"):
        return "otros"
    return "otros"


def validate_upload(filename: str, size: int) -> str:
    """Valida extensión y tamaño. Retorna la extensión. Lanza ValueError si falla."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Extensión '{ext}' no permitida")
    if size > MAX_FILE_SIZE:
        raise ValueError("Archivo demasiado grande (máx. 50MB)")
    return ext


def save_file_to_disk(contents: bytes, ext: str) -> str:
    """Guarda bytes en disco con nombre único. Retorna la ruta absoluta."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    with open(file_path, "wb") as f:
        f.write(contents)
    return file_path


def extract_zip_entries(contents: bytes) -> list[tuple[str, bytes, str | None]]:
    """Extrae archivos de un ZIP. Retorna lista de (filename, data, mime_type).

    Raises zipfile.BadZipFile si el ZIP es inválido.
    """
    entries = []
    with zipfile.ZipFile(io.BytesIO(contents)) as z:
        for info in z.infolist():
            if (
                info.is_dir()
                or info.filename.startswith("__MACOSX")
                or info.filename.startswith(".")
            ):
                continue
            original_name = os.path.basename(info.filename)
            if not original_name:
                continue
            extracted_data = z.read(info.filename)
            mime_type, _ = mimetypes.guess_type(original_name)
            entries.append((original_name, extracted_data, mime_type))
    return entries
