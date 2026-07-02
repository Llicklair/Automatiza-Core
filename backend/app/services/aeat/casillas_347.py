"""Mapeo del resumen del Modelo 347 a las casillas oficiales de la hoja-resumen.

Modelo 347 — Declaración anual de operaciones con terceras personas. Informativa
basada en un listado de contrapartes con operaciones que superan los 3.005,06 €
(IVA incluido) en el ejercicio. La HOJA-RESUMEN del impreso numera cuatro casillas:
01/02 para el total de operaciones y 03/04 para los arrendamientos de local de
negocio (que se cumplimentan aparte si procede).

Casillas verificadas (modelo oficial AEAT 347).
"""

from __future__ import annotations

from decimal import Decimal

from app.services.aeat._casilla import Casilla, round2

CASILLAS_347 = {
    "01": "Número total de personas y entidades declaradas",
    "02": "Importe total anual de las operaciones (IVA incluido)",
    "03": "Número total de inmuebles en arrendamiento de local de negocio",
    "04": "Importe total de las operaciones de arrendamiento de local de negocio",
}


def build_casillas_347(data: dict) -> list[Casilla]:
    declarables = data.get("declarables") or []

    num = data.get("num_declarables")
    c01 = round2(num if num is not None else len(declarables))

    total = data.get("importe_total_operaciones")
    if total is None:
        total = sum(
            (round2(d.get("importe_emitidas")) + round2(d.get("importe_recibidas")) for d in declarables),
            Decimal("0"),
        )
    c02 = round2(total)

    # Arrendamientos de local de negocio: el builder no los desglosa; se muestran a
    # 0 y editables para cumplimentar manualmente si procede (no inventar importes).
    return [
        Casilla("01", CASILLAS_347["01"], c01, formato="numero"),
        Casilla("02", CASILLAS_347["02"], c02),
        Casilla(
            "03",
            CASILLAS_347["03"],
            round2(0),
            editable=True,
            formato="numero",
            nota="Arrendamientos de local de negocio: cumplimentar si procede.",
        ),
        Casilla(
            "04",
            CASILLAS_347["04"],
            round2(0),
            editable=True,
            nota="Importe de arrendamientos de local de negocio: cumplimentar si procede.",
        ),
    ]
