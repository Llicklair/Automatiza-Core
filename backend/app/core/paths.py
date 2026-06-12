"""Directorio de datos de la app (fuente única de verdad).

El instalador desktop guarda Postgres portable, Python, JRE, licencia, backups,
logs y uploads bajo `%APPDATA%/AutomatizaPyme` (Windows) — ver
`desktop/postgres-manager.js` (`APPDATA_DIR`). Históricamente el backend
hardcodeaba "AutomatizaCore" (nombre antiguo del proyecto), por lo que buscaba
binarios/ficheros en una carpeta inexistente (p. ej. pg_dump → backups que no se
generaban). Este módulo centraliza el nombre para evitar esa divergencia.

Overrides por entorno (los fija el desktop si hace falta):
  - `AUTOMATIZA_DATA_DIR`  → ruta absoluta completa del directorio de datos.
  - `AUTOMATIZA_APPDIR`    → solo el nombre de la subcarpeta (default AutomatizaPyme).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Nombre de la subcarpeta de datos. DEBE coincidir con `APPDATA_DIR` del desktop.
APP_DIR_NAME = os.environ.get("AUTOMATIZA_APPDIR", "AutomatizaPyme")


def app_data_dir(*parts: str) -> Path:
    """Devuelve el directorio de datos de la app (+ subpartes opcionales).

    Windows → `%APPDATA%/<APP_DIR_NAME>`; POSIX → `$XDG_DATA_HOME` o
    `~/.local/share/<APP_DIR_NAME>`. Respeta `AUTOMATIZA_DATA_DIR` si está.
    """
    override = os.environ.get("AUTOMATIZA_DATA_DIR")
    if override:
        base = Path(override)
    elif sys.platform == "win32":
        appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        base = Path(appdata) / APP_DIR_NAME
    else:
        xdg = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        base = Path(xdg) / APP_DIR_NAME
    return base.joinpath(*parts) if parts else base
