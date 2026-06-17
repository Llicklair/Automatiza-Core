"""Mapeo del cálculo agregado del Modelo 115 a las casillas oficiales AEAT.

Modelo 115 — Retenciones e ingresos a cuenta por arrendamiento de inmuebles
urbanos. Autoliquidación trimestral. Casillas verificadas (AEAT / getquipu /
infoautónomos): 01 nº perceptores, 02 base, 03 retenciones, 04 a deducir
(complementaria), 05 resultado a ingresar (= 03 − 04).
"""

from __future__ import annotations

from app.services.aeat._casilla import Casilla, round2

CASILLAS_115 = {
    "01": "Número de perceptores",
    "02": "Base de las retenciones e ingresos a cuenta",
    "03": "Retenciones e ingresos a cuenta",
    "04": "A deducir (exclusivamente si es declaración complementaria)",
    "05": "Resultado a ingresar",
}


def build_casillas_115(data: dict) -> list[Casilla]:
    c01 = round2(data.get("num_arrendadores"))
    c02 = round2(data.get("total_base_retenciones"))
    c03 = round2(data.get("total_retencion_practicada"))
    c04 = round2(data.get("a_deducir_complementaria"))
    c05 = round2(c03 - c04)

    def _c(cod, val, **kw):
        return Casilla(cod, CASILLAS_115[cod], val, **kw)

    return [
        _c("01", c01, formato="numero"),
        _c("02", c02),
        _c("03", c03),
        _c("04", c04, editable=True, nota="Solo en declaración complementaria del mismo período."),
        _c("05", c05),
    ]
