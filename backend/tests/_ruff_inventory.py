"""Inventario determinista de defectos via ruff — la RED ANCHA del loop detector.

Sustituye la mirilla de 6 patrones hechos a mano por los rulesets de ruff que cazan
BUGS reales (no estilo): cientos de reglas mantenidas, deterministas, ~0 tokens LLM.
El LLM solo triagea y arregla los hits reales (misma filosofia barata del detector).

Complementa — no reemplaza — a `_defect_detectors.py`, que cubre patrones de DOMINIO
que ruff no conoce (stock read-modify-write, select-then-add sin UNIQUE, info_disclosure_500).

Uso:
    python tests/_ruff_inventory.py            # inventario clasificado (conteos + hotspots + criticos)
    python tests/_ruff_inventory.py --json     # hits crudos JSON (para el triaje por subagente)
    python tests/_ruff_inventory.py --new <ledger.json>  # solo lo NUEVO vs un baseline previo
"""

from __future__ import annotations

import collections
import json
import subprocess
import sys

ROOT = "app"

# Familias que se piden a ruff. Traen reglas de bug; el ruido se filtra abajo.
SELECT = "B,BLE,DTZ,ASYNC,RUF006,RUF013,S,TRY004,PERF401"
# B008 = Depends()/Query() en defaults de FastAPI -> FP conocido. S101 = assert en tests.
IGNORE = "B008,S101"

# Mapa code -> categoria. SOLO estas reglas se consideran bug real; el resto se reporta
# aparte como "sin_clasificar" para que NUNCA se descarte algo en silencio.
CATEGORY: dict[str, str] = {
    # seguridad (cada hit = revision individual)
    "S608": "security", "S105": "security", "S107": "security", "S108": "security",
    "S324": "security", "S311": "security", "S603": "security", "S320": "security",
    "S314": "security", "S110": "security", "S112": "security", "S301": "security",
    "S306": "security", "S307": "security", "S506": "security",
    # correctitud / fiabilidad de errores
    "BLE001": "errores",   # except ciego que se traga el fallo
    "B904": "errores",     # raise sin `from` -> pierde el traceback original
    "TRY004": "errores",   # comprobacion de tipo que deberia lanzar TypeError
    # bugs varios de bugbear
    "B006": "bug", "B007": "bug", "B009": "bug", "B902": "bug", "B905": "bug",
    "B017": "bug", "B023": "bug", "B024": "bug",
    # async
    "ASYNC230": "async", "ASYNC220": "async", "ASYNC109": "async", "ASYNC210": "async",
    "ASYNC251": "async", "RUF006": "async",  # RUF006 = task de asyncio colgada (GC la mata)
    # tipos
    "RUF013": "tipos",     # Optional implicito
    # rendimiento
    "PERF401": "perf",
    # datetime sin timezone (bug real en facturacion/scheduling)
    "DTZ001": "datetime", "DTZ003": "datetime", "DTZ005": "datetime",
    "DTZ006": "datetime", "DTZ007": "datetime", "DTZ011": "datetime",
}

# Orden de severidad para el reporte.
CAT_ORDER = ["security", "async", "errores", "datetime", "bug", "tipos", "perf", "sin_clasificar"]


def run_ruff() -> list[dict]:
    out = subprocess.run(
        ["python", "-m", "ruff", "check", ROOT,
         "--select", SELECT, "--ignore", IGNORE, "--output-format", "json"],
        capture_output=True, text=True,
    )
    if not out.stdout.strip():
        return []
    return json.loads(out.stdout)


def key(h: dict) -> str:
    loc = h.get("location") or {}
    return f"{h.get('filename','')}:{loc.get('row','')}:{h.get('code','')}"


def main() -> None:
    args = sys.argv[1:]
    hits = run_ruff()

    if "--new" in args:
        baseline = set(json.load(open(args[args.index("--new") + 1])))
        hits = [h for h in hits if key(h) not in baseline]

    if "--json" in args:
        print(json.dumps(hits))
        return

    by_cat: dict[str, int] = collections.Counter()
    by_rule: dict[str, int] = collections.Counter()
    by_file: dict[str, int] = collections.Counter()
    critical: list[str] = []
    rule_cat: dict[str, str] = {}

    for h in hits:
        code = h.get("code") or "???"
        cat = CATEGORY.get(code, "sin_clasificar")
        by_cat[cat] += 1
        by_rule[code] += 1
        rule_cat[code] = cat
        fn = (h.get("filename") or "").replace("\\", "/").split("/app/")[-1]
        by_file[fn] += 1
        if cat in ("security", "async"):
            row = (h.get("location") or {}).get("row", "?")
            critical.append(f"  [{cat:8}] {code:8} {fn}:{row}  {h.get('message','')[:70]}")

    print(f"# Inventario ruff (bug-classes) — total: {len(hits)} hits  (B008/S101 excluidos como FP)\n")
    print("## Por categoria")
    for cat in CAT_ORDER:
        if by_cat.get(cat):
            print(f"  {cat:16} {by_cat[cat]:5}")
    print("\n## Por regla (code | n | categoria)")
    for code, n in sorted(by_rule.items(), key=lambda kv: -kv[1]):
        print(f"  {code:10} {n:5}  {rule_cat.get(code,'?')}")
    print("\n## Hotspots (top 12 ficheros)")
    for fn, n in by_file.most_common(12):
        print(f"  {n:4}  {fn}")
    print(f"\n## CRITICOS (security + async) — listado completo: {len(critical)}")
    for line in sorted(critical):
        print(line)
    print("\n" + json.dumps({"total": len(hits), "by_cat": dict(by_cat)}))


if __name__ == "__main__":
    main()
