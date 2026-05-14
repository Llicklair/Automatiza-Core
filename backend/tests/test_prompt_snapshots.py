"""QA.PRM — snapshot tests de prompts.

Cada prompt se hashea con SHA-256 y se compara contra una baseline
versionada en `tests/fixtures/prompt_snapshots.json`. Si un prompt cambia
intencionalmente, el dev debe regenerar la baseline:

    python backend/scripts/update_prompt_snapshots.py

El test falla con un diff legible si el prompt actual no coincide con
el snapshot — esto previene cambios de prompt no revisados que afecten
el comportamiento del agente en producción (AI.GOV gobernanza).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).parent.parent
_SNAPSHOT_FILE = _BACKEND_ROOT / "tests" / "fixtures" / "prompt_snapshots.json"


def _collect_prompts() -> dict[str, str]:
    """Localiza todos los archivos de prompts del repo y devuelve {path_relativo: sha256}."""
    targets: list[Path] = []
    targets.extend((_BACKEND_ROOT / "app" / "prompts").glob("*.txt"))
    targets.extend((_BACKEND_ROOT / "app" / "agents").rglob("prompts.py"))

    out: dict[str, str] = {}
    for path in sorted(targets):
        rel = path.relative_to(_BACKEND_ROOT).as_posix()
        content = path.read_bytes()
        # Normalizamos line endings (CRLF/LF) para que el snapshot sea OS-agnóstico.
        content = content.replace(b"\r\n", b"\n")
        out[rel] = hashlib.sha256(content).hexdigest()
    return out


def _load_snapshot() -> dict[str, str]:
    if not _SNAPSHOT_FILE.exists():
        return {}
    return json.loads(_SNAPSHOT_FILE.read_text(encoding="utf-8"))


class TestPromptSnapshots:
    def test_existe_baseline(self):
        """Si no existe la baseline, regenerarla con el script update."""
        if not _SNAPSHOT_FILE.exists():
            pytest.skip(
                "Baseline ausente — ejecutar "
                "`python backend/scripts/update_prompt_snapshots.py`",
            )
        assert _SNAPSHOT_FILE.exists()

    def test_baseline_cubre_todos_los_prompts(self):
        if not _SNAPSHOT_FILE.exists():
            pytest.skip("Baseline ausente.")

        current = _collect_prompts()
        baseline = _load_snapshot()

        missing = sorted(set(current) - set(baseline))
        assert not missing, (
            f"Prompts nuevos sin baseline: {missing}. "
            "Regenera con `python backend/scripts/update_prompt_snapshots.py`."
        )

    def test_baseline_no_referencia_prompts_inexistentes(self):
        if not _SNAPSHOT_FILE.exists():
            pytest.skip("Baseline ausente.")

        current = _collect_prompts()
        baseline = _load_snapshot()

        stale = sorted(set(baseline) - set(current))
        assert not stale, (
            f"Baseline referencia prompts eliminados: {stale}. "
            "Regenera con el script update."
        )

    def test_hashes_coinciden_con_baseline(self):
        if not _SNAPSHOT_FILE.exists():
            pytest.skip("Baseline ausente.")

        current = _collect_prompts()
        baseline = _load_snapshot()
        diffs: list[str] = []
        for path in sorted(set(current) & set(baseline)):
            if current[path] != baseline[path]:
                diffs.append(
                    f"  - {path}\n      expected={baseline[path][:16]}…  got={current[path][:16]}…"
                )
        assert not diffs, (
            "Prompts modificados sin actualizar baseline:\n"
            + "\n".join(diffs)
            + "\n\nSi el cambio es intencional, regenera con "
            "`python backend/scripts/update_prompt_snapshots.py`."
        )

    def test_descubre_prompts_de_ambos_directorios(self):
        prompts = _collect_prompts()
        # Detección sanity: tiene prompts .txt y prompts.py
        assert any(p.endswith(".txt") for p in prompts)
        assert any(p.endswith("prompts.py") for p in prompts)
