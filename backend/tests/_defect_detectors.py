"""Detectores AST deterministas de familias de defecto (guardrail anti-regresion).

Portable (solo stdlib `ast`), barre todo el repo en segundos. Lo consume
`test_defect_families_guard.py` como check de CI: si reaparece una instancia de
una familia ya saneada, el build falla.

NO es un fichero de test en si mismo (sin prefijo `test_`), asi que pytest no lo
recolecta directamente.

Origen: familias mapeadas por el loop /forja. Cada una tiene su fix canonico:
  - info_disclosure_500: `detail=str(e)`/f-string en HTTP 500 -> genericizar detail + logger.
  - httpx_no_timeout: httpx.AsyncClient/Client sin timeout= -> anadir timeout.
  - stock_rmw: escribe *.stock_quantity sin .with_for_update() en la funcion
    (recall alto; tiene falsos positivos por path-sensitivity -> se usa con allowlist).
"""
from __future__ import annotations

import ast
import os

_HERE = os.path.dirname(__file__)
DEFAULT_ROOT = os.path.normpath(os.path.join(_HERE, "..", "app"))


def _rel(path: str, root: str) -> str:
    return os.path.relpath(path, root).replace("\\", "/")


def _is_500(v: ast.AST) -> bool:
    if isinstance(v, ast.Constant) and v.value == 500:
        return True
    return isinstance(v, ast.Attribute) and "500" in v.attr


def _http_status_is_500(call: ast.Call) -> bool:
    if call.args and _is_500(call.args[0]):
        return True
    for kw in call.keywords:
        if kw.arg == "status_code":
            return _is_500(kw.value)
    return False


def _detail_leaks(val: ast.AST) -> bool:
    # str(<name>)
    if isinstance(val, ast.Call) and isinstance(val.func, ast.Name) and val.func.id == "str":
        return True
    # f-string que interpola un Name (posible fuga de variable/excepcion)
    if isinstance(val, ast.JoinedStr):
        return any(
            isinstance(p, ast.FormattedValue) and isinstance(p.value, ast.Name)
            for p in val.values
        )
    return False


def _httpx_no_timeout(call: ast.Call) -> bool:
    f = call.func
    if isinstance(f, ast.Attribute) and f.attr in ("AsyncClient", "Client"):
        recv = getattr(f, "value", None)
        if isinstance(recv, ast.Name) and recv.id == "httpx":
            return not any(kw.arg == "timeout" for kw in call.keywords)
    return False


def _func_writes_stock(fn: ast.AST) -> int | None:
    for n in ast.walk(fn):
        if isinstance(n, (ast.Assign, ast.AugAssign)):
            targets = n.targets if isinstance(n, ast.Assign) else [n.target]
            for t in targets:
                if isinstance(t, ast.Attribute) and t.attr == "stock_quantity":
                    return n.lineno
    return None


def _func_has_for_update(fn: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "with_for_update"
        for n in ast.walk(fn)
    )


# Funciones que LEGITIMAMENTE fijan status sin guardar el estado origen
# (creacion/seed/setters parametrizados) -> se excluyen del detector de guard.
_STATE_EXCLUDE_PREFIX = ("create", "update", "seed", "build", "make", "new", "__init__", "_make")


def _func_status_write_unguarded(fn: ast.AST):
    """Devuelve (linea, valor) si la funcion asigna `<x>.status = <const-str>` y
    NO compara `.status` en ningun `if` (transicion sin guard de maquina de estados)."""
    writes: list[tuple[int, str]] = []
    has_status_compare = False
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Attribute) and t.attr == "status":
                    if isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                        writes.append((n.lineno, n.value.value))
        if isinstance(n, ast.Compare):
            sides = [n.left, *n.comparators]
            if any(isinstance(s, ast.Attribute) and s.attr == "status" for s in sides):
                has_status_compare = True
    return writes[0] if (writes and not has_status_compare) else None


def _scan_model_uniques(models_root: str) -> dict[str, bool]:
    """{NombreModelo: tiene_algun_unique} parseando los modelos ORM."""
    res: dict[str, bool] = {}
    if not os.path.isdir(models_root):
        return res
    for dp, _d, files in os.walk(models_root):
        if "__pycache__" in dp:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            try:
                tree = ast.parse(open(os.path.join(dp, fn), encoding="utf-8").read())
            except (SyntaxError, UnicodeDecodeError):
                continue
            for cls in ast.walk(tree):
                if not isinstance(cls, ast.ClassDef):
                    continue
                has_unique = False
                for sub in ast.walk(cls):
                    if isinstance(sub, ast.Call):
                        nm = sub.func.attr if isinstance(sub.func, ast.Attribute) else getattr(sub.func, "id", None)
                        if nm == "UniqueConstraint":
                            has_unique = True
                        elif nm == "Column":
                            for kw in sub.keywords:
                                if kw.arg == "unique" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                                    has_unique = True
                res[cls.name] = has_unique
    return res


def _func_select_then_add_no_unique(fn: ast.AST, model_uniques: dict[str, bool]):
    """Modelos que la funcion SELECTea Y añade (db.add(Model(...))) y que NO tienen
    ningun UNIQUE -> guard a nivel app (if not exists) sin respaldo de constraint en
    BD -> carrera de doble-insercion concurrente."""
    selected: set[str] = set()
    added: set[str] = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            nm = n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", None)
            if nm == "select" and n.args:
                a0 = n.args[0]
                if isinstance(a0, ast.Name):
                    selected.add(a0.id)
                elif isinstance(a0, ast.Attribute) and isinstance(a0.value, ast.Name):
                    selected.add(a0.value.id)
            elif nm == "add" and n.args and isinstance(n.args[0], ast.Call):
                ctor = n.args[0].func
                if isinstance(ctor, ast.Name):
                    added.add(ctor.id)
    flagged = sorted(m for m in (selected & added) if m in model_uniques and not model_uniques[m])
    return ", ".join(flagged) if flagged else None


def scan(root: str = DEFAULT_ROOT) -> dict[str, list[str]]:
    """Devuelve {familia: [ "fichero:linea[ extra]" ]} sobre todo `root`."""
    out: dict[str, list[str]] = {
        "info_disclosure_500": [],
        "httpx_no_timeout": [],
        "stock_rmw": [],
        "missing_state_guard": [],  # candidatos (FP-prone): transicion sin guard
        "div_by_len": [],           # candidatos (FP-prone): / len(...) sin zero-guard
        "select_then_add_no_unique": [],  # candidatos: upsert app-level sin UNIQUE en BD
    }
    model_uniques = _scan_model_uniques(os.path.join(root, "db", "models"))
    for dirpath, _dirs, files in os.walk(root):
        if "__pycache__" in dirpath:
            continue
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
            except (SyntaxError, UnicodeDecodeError):
                continue
            rp = _rel(path, root)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", None)
                    if name == "HTTPException" and _http_status_is_500(node):
                        for kw in node.keywords:
                            if kw.arg == "detail" and _detail_leaks(kw.value):
                                out["info_disclosure_500"].append(f"{rp}:{node.lineno}")
                    if _httpx_no_timeout(node):
                        out["httpx_no_timeout"].append(f"{rp}:{node.lineno}")
                if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv)):
                    r = node.right
                    if isinstance(r, ast.Call) and isinstance(r.func, ast.Name) and r.func.id == "len":
                        out["div_by_len"].append(f"{rp}:{node.lineno}")
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    wl = _func_writes_stock(node)
                    if wl and not _func_has_for_update(node):
                        out["stock_rmw"].append(f"{rp}:{wl} {node.name}")
                    fname_lc = node.name.lower()
                    if not any(fname_lc.startswith(p) for p in _STATE_EXCLUDE_PREFIX):
                        sw = _func_status_write_unguarded(node)
                        if sw:
                            out["missing_state_guard"].append(f"{rp}:{sw[0]} {node.name} (->{sw[1]})")
                    sa = _func_select_then_add_no_unique(node, model_uniques)
                    if sa:
                        out["select_then_add_no_unique"].append(f"{rp}:{node.lineno} {node.name} ({sa})")
    for v in out.values():
        v.sort()
    return out


if __name__ == "__main__":
    import json
    import sys

    res = scan(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT)
    for fam, hits in res.items():
        print(f"\n### {fam}: {len(hits)}")
        for h in hits:
            print("  " + h)
    print("\n" + json.dumps({k: len(v) for k, v in res.items()}))
