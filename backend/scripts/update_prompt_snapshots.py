"""Regenera la baseline de snapshots de prompts (QA.PRM).

Uso intencional cuando un prompt cambia tras review:
    python backend/scripts/update_prompt_snapshots.py

Genera `backend/tests/fixtures/prompt_snapshots.json` con:
    { "app/prompts/banking_agent.txt": "<sha256>", ... }
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

_BACKEND_ROOT = Path(__file__).parent.parent
_SNAPSHOT_FILE = _BACKEND_ROOT / "tests" / "fixtures" / "prompt_snapshots.json"


def collect() -> dict[str, str]:
    targets: list[Path] = []
    targets.extend((_BACKEND_ROOT / "app" / "prompts").glob("*.txt"))
    targets.extend((_BACKEND_ROOT / "app" / "agents").rglob("prompts.py"))

    out: dict[str, str] = {}
    for path in sorted(targets):
        rel = path.relative_to(_BACKEND_ROOT).as_posix()
        content = path.read_bytes().replace(b"\r\n", b"\n")
        out[rel] = hashlib.sha256(content).hexdigest()
    return out


def main() -> int:
    _SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    snapshot = collect()
    _SNAPSHOT_FILE.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Baseline actualizada: {len(snapshot)} prompts -> {_SNAPSHOT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
