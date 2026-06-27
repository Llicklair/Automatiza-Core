"""Guardrail anti-regresion de familias de defecto (motor: `_defect_detectors`).

Si reaparece una fuga `detail=str(e)` en un HTTP 500, o un cliente httpx sin
timeout, el build FALLA. Estas familias fueron saneadas al 100% por el loop
/forja -> baseline = 0 (ratchet: el suelo de calidad solo sube).

`stock_rmw` se controla por ALLOWLIST: el detector intra-funcion tiene falsos
positivos por path-sensitivity (el lock puede estar en el llamador), asi que solo
fallan sitios NUEVOS que escriban stock sin lock.
"""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location(
    "_defect_detectors", os.path.join(os.path.dirname(__file__), "_defect_detectors.py")
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_RESULTS = _mod.scan()

# Sitios stock-RMW conocidos (FP por lock-en-llamador, o ya en inbox para revision).
# Solo se permite ESTE conjunto; un sitio NUEVO que escriba stock sin lock falla.
# Clave = "fichero func" (sin numero de linea, que es volatil).
STOCK_RMW_ALLOWLIST = {
    "services/inventory/batch_service.py batch_adjust_stock",
    "services/inventory/lot_service.py create_lot",
    "services/inventory/stock_service.py add_to_warehouse",
    "services/sales/commands.py create_stock_movement",
    "services/sales/commands.py _deduct_stock_for_albaran",
    "services/sales/commands.py _revert_stock_for_albaran",
    "services/sales/pos.py checkout",
}


def _file_func(entry: str) -> str:
    loc, _, func = entry.partition(" ")
    return f"{loc.rsplit(':', 1)[0]} {func}"


def test_no_info_disclosure_in_500():
    hits = _RESULTS["info_disclosure_500"]
    assert hits == [], (
        "Fuga de info en HTTP 500 (detail=str(e)/f-string). Genericiza el detail y "
        "loguea el error completo (logger.exception/error). Sitios:\n  " + "\n  ".join(hits)
    )


def test_no_httpx_client_without_timeout():
    hits = _RESULTS["httpx_no_timeout"]
    assert hits == [], (
        "Cliente httpx sin timeout= (puede colgar indefinidamente). Anade timeout=. "
        "Sitios:\n  " + "\n  ".join(hits)
    )


def test_no_new_unlocked_stock_writes():
    found = {_file_func(h) for h in _RESULTS["stock_rmw"]}
    nuevos = found - STOCK_RMW_ALLOWLIST
    assert not nuevos, (
        "Escritura de stock_quantity SIN with_for_update en sitio NUEVO. Anade lock "
        "de fila (patron stock_service.transfer) o justificalo en la allowlist:\n  "
        + "\n  ".join(sorted(nuevos))
    )
