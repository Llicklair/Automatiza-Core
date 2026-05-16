"""Inspector ligero del trace JSONL escrito por LLMTraceCallback.

Uso:
    python backend/scripts/llm_log_tail.py                         # últimas 20 entradas de hoy
    python backend/scripts/llm_log_tail.py -n 50 --errors          # últimos 50 errores
    python backend/scripts/llm_log_tail.py --run-id abc-123        # toda la traza de un run
    python backend/scripts/llm_log_tail.py --day 2026-05-08        # log de un día concreto
    python backend/scripts/llm_log_tail.py --grouped               # agrupa start+end+error por run_id

Si no hay log y esperabas que lo hubiera, asegúrate de que arrancaste
el backend con LLM_TRACE_ENABLED=true (env var). El log se escribe en
logs/llm/{YYYY-MM-DD}.jsonl (override con LLM_TRACE_DIR).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path


def _load(file: Path) -> list[dict]:
    if not file.exists():
        return []
    items: list[dict] = []
    for line in file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return items


def _print_grouped(items: list[dict]) -> None:
    by_run: dict[str, list[dict]] = defaultdict(list)
    for it in items:
        run = it.get("run_id") or "unknown"
        by_run[run].append(it)
    for run_id, events in by_run.items():
        events.sort(key=lambda e: e.get("ts", ""))
        start = next((e for e in events if e.get("event") in ("chat_start", "llm_start")), None)
        end = next((e for e in events if e.get("event") == "chat_end"), None)
        err = next((e for e in events if e.get("event") == "chat_error"), None)
        status = "OK" if end else ("ERROR" if err else "INCOMPLETE")
        latency = (end or err or {}).get("latency_s")
        model = (start or {}).get("model", "?")
        tags = (start or {}).get("tags") or []
        first_msg = ""
        if start and start.get("messages"):
            first_msg = (start["messages"][-1].get("content") or "")[:140]
        tool_calls_done: list[str] = []
        if end:
            for g in end.get("generations", []):
                for tc in g.get("tool_calls") or []:
                    tool_calls_done.append(tc.get("name") or "?")
        print(
            f"[{status:^9}] {run_id[:8]} | {model:>30s} | "
            f"{latency:>6.2f}s | tags={tags} | tools_called={tool_calls_done}"
            if isinstance(latency, int | float)
            else f"[{status:^9}] {run_id[:8]} | {model:>30s} | {'':>7s} | tags={tags} | tools_called={tool_calls_done}"
        )
        if first_msg:
            print(f"            ↳ último msg: {first_msg!r}")
        if err:
            print(f"            ↳ error: {err.get('error_type')}: {err.get('error', '')[:200]}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", default="logs/llm", help="directorio raíz de los JSONL")
    p.add_argument("-n", type=int, default=20, help="cuántas entradas mostrar (cuando no se agrupa)")
    p.add_argument("--errors", action="store_true", help="solo eventos chat_error")
    p.add_argument("--run-id", help="filtrar por run_id (parcial)")
    p.add_argument("--day", help="día YYYY-MM-DD (default hoy UTC)")
    p.add_argument("--grouped", action="store_true", help="agrupa start+end+error por run_id")
    args = p.parse_args()

    log_dir = Path(args.dir)
    day = args.day or datetime.now(UTC).date().isoformat()
    file = log_dir / f"{day}.jsonl"

    items = _load(file)
    if not items:
        print(f"[llm-trace] sin entradas en {file}", file=sys.stderr)
        return 1

    if args.errors:
        items = [i for i in items if i.get("event") == "chat_error"]
    if args.run_id:
        items = [i for i in items if (i.get("run_id") or "").startswith(args.run_id)]

    if args.grouped:
        _print_grouped(items)
        return 0

    for item in items[-args.n:]:
        print(json.dumps(item, ensure_ascii=False, indent=2))
        print("---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
