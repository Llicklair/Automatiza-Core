"""Mapeo del resumen del Modelo 190 a las casillas oficiales de la hoja-resumen.

Modelo 190 — Resumen anual de retenciones e ingresos a cuenta del IRPF. Es una
declaración informativa basada en un listado de perceptores; la HOJA-RESUMEN del
impreso oficial sólo numera tres casillas (recuento y totales, con independencia
de claves/subclaves de percepción).

Casillas verificadas (Orden EHA/3127/2009, BOE-A-2009-18567).
"""

from __future__ import annotations

from decimal import Decimal

from app.services.aeat._casilla import Casilla, round2

CASILLAS_190 = {
    "01": "Número total de perceptores relacionados",
    "02": "Importe total de las percepciones íntegras",
    "03": "Importe total de las retenciones e ingresos a cuenta",
}


def _sum(rows: list, key: str) -> Decimal:
    return round2(sum((round2(r.get(key)) for r in rows), Decimal("0")))


def build_casillas_190(data: dict) -> list[Casilla]:
    perceptores = data.get("perceptores") or []

    num = data.get("num_perceptores")
    c01 = round2(num if num is not None else len(perceptores))

    total_perc = data.get("total_percepcion_integra")
    c02 = round2(total_perc) if total_perc is not None else _sum(perceptores, "percepcion_integra")

    total_ret = data.get("total_retencion_practicada")
    c03 = round2(total_ret) if total_ret is not None else _sum(perceptores, "retencion_practicada")

    return [
        Casilla("01", CASILLAS_190["01"], c01, formato="numero"),
        Casilla("02", CASILLAS_190["02"], c02),
        Casilla("03", CASILLAS_190["03"], c03),
    ]
