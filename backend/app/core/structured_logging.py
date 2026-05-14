"""Logger JSON estructurado (CONT.LOG).

Logs en formato JSON line-per-event, rotados en `%APPDATA%/AutomatizaPyme/logs/`
(Windows) o `~/.local/share/AutomatizaPyme/logs/` (POSIX). Aplica
`telemetry_scrubber.scrub_text` a `message` y `exc_info` para evitar persistir
PII en disco.

Cada línea es un objeto JSON con:
    timestamp, level, logger, message, module, function, line, app_version,
    extra (campos arbitrarios pasados por el caller).

Uso:
    >>> from app.core.structured_logging import setup_structured_logging
    >>> setup_structured_logging()
    >>> import logging
    >>> logging.getLogger("billing").info("invoice created", extra={"invoice_id": "..."})

El bundle de diagnóstico (`/api/v1/system/diagnostic-bundle`) lee directamente
estos archivos JSONL y los empaqueta en un ZIP exportable.
"""

import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.telemetry_scrubber import scrub_text


class JSONFormatter(logging.Formatter):
    """Formatter que emite cada record como una línea JSON."""

    def __init__(self, app_version: str | None = None) -> None:
        super().__init__()
        self.app_version = app_version or "unknown"

    def format(self, record: logging.LogRecord) -> str:
        # Scrub el mensaje para evitar PII en disco.
        message = record.getMessage()
        message = scrub_text(message) or ""

        entry: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "app_version": self.app_version,
        }

        # Excepción: traza scrubbed.
        if record.exc_info:
            exc_text = self.formatException(record.exc_info)
            entry["exc_info"] = scrub_text(exc_text)

        # Campos extra que el caller haya pasado vía `extra={...}`.
        # No incluimos campos privados ni reservados del LogRecord.
        reserved = {
            "args", "asctime", "created", "exc_info", "exc_text", "filename",
            "funcName", "levelname", "levelno", "lineno", "message", "module",
            "msecs", "msg", "name", "pathname", "process", "processName",
            "relativeCreated", "stack_info", "thread", "threadName", "taskName",
        }
        extras = {
            key: scrub_text(value) if isinstance(value, str) else value
            for key, value in record.__dict__.items()
            if key not in reserved and not key.startswith("_")
        }
        if extras:
            entry["extra"] = extras

        return json.dumps(entry, ensure_ascii=False, default=str)


def get_log_dir() -> Path:
    """Devuelve el directorio de logs según el SO.

    - Windows: `%APPDATA%/AutomatizaPyme/logs/`
    - POSIX: `~/.local/share/AutomatizaPyme/logs/`

    Crea el directorio si no existe.
    """
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        log_dir = base / "AutomatizaPyme" / "logs"
    else:
        log_dir = Path.home() / ".local" / "share" / "AutomatizaPyme" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_structured_logging(
    *,
    app_version: str | None = None,
    log_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    filename: str = "automatizapyme.jsonl",
) -> Path:
    """Configura logger root con `RotatingFileHandler` JSON.

    Devuelve la ruta al archivo de log activo. Se llama desde el lifespan
    de la app — idempotente: si el handler ya está configurado, no se duplica.

    Mantiene `StreamHandler` (stdout) con formato humano para dev/uvicorn.
    """
    log_dir = get_log_dir()
    log_file = log_dir / filename

    formatter = JSONFormatter(app_version=app_version)
    handler = RotatingFileHandler(
        str(log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    handler.setLevel(log_level)
    handler.set_name("automatizapyme_jsonl")  # idempotencia

    root = logging.getLogger()
    # Evitar duplicar handler en hot-reload
    for existing in root.handlers:
        if existing.get_name() == "automatizapyme_jsonl":
            return log_file
    root.addHandler(handler)
    root.setLevel(min(root.level, log_level) if root.level else log_level)

    return log_file
