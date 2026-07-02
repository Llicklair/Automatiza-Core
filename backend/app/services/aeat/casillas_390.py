"""Mapeo del cálculo agregado del Modelo 390 a las casillas oficiales AEAT.

Modelo 390 — Resumen anual del IVA. El formulario completo tiene ~190 casillas;
aquí cubrimos las CLAVE del régimen general que se rellenan automáticamente desde
los importes agregados del ejercicio (devengado por tipo, total devengado,
deducible de operaciones interiores corrientes y resultado de la liquidación).
Recargo de equivalencia, ISP, bienes de inversión, importaciones y prorrata se
omiten o quedan a 0 (ajuste manual antes de presentar).

Casillas verificadas (AEAT / BOE de la orden del modelo 390).
"""

from __future__ import annotations

from decimal import Decimal

from app.services.aeat._casilla import Casilla, round2

CASILLAS_390 = {
    "01": "IVA devengado · Régimen general · Base imponible al 4%",
    "02": "IVA devengado · Régimen general · Cuota al 4%",
    "03": "IVA devengado · Régimen general · Base imponible al 10%",
    "04": "IVA devengado · Régimen general · Cuota al 10%",
    "05": "IVA devengado · Régimen general · Base imponible al 21%",
    "06": "IVA devengado · Régimen general · Cuota al 21%",
    "33": "Total bases IVA devengado",
    "34": "Total cuotas IVA devengado",
    "47": "Total cuota devengada",
    "48": "IVA deducible · Operaciones interiores corrientes · Base imponible",
    "49": "IVA deducible · Operaciones interiores corrientes · Cuota deducible",
    "64": "Suma de deducciones (Total a deducir)",
    "65": "Resultado del régimen general (casilla 47 − casilla 64)",
    "84": "Suma de resultados",
    "86": "Resultado de la liquidación anual",
}


def _sum(rows: list, key: str) -> Decimal:
    return round2(sum((round2(r.get(key)) for r in rows), Decimal("0")))


def build_casillas_390(data: dict) -> list[Casilla]:
    dev = data.get("iva_devengado") or []
    ded = data.get("iva_deducible") or []
    by_rate = {round(float(r.get("rate", 0) or 0)): r for r in dev}

    def _base(rate):
        return round2((by_rate.get(rate) or {}).get("base"))

    def _cuota(rate):
        return round2((by_rate.get(rate) or {}).get("quota"))

    c01, c02 = _base(4), _cuota(4)
    c03, c04 = _base(10), _cuota(10)
    c05, c06 = _base(21), _cuota(21)
    c33 = _sum(dev, "base")
    tot_dev = data.get("total_devengado")
    c34 = round2(tot_dev) if tot_dev is not None else _sum(dev, "quota")
    c47 = c34
    c48 = _sum(ded, "base")
    tot_ded = data.get("total_deducible")
    c49 = round2(tot_ded) if tot_ded is not None else _sum(ded, "quota")
    c64 = c49
    c65 = round2(c47 - c64)
    c84 = c65
    res = data.get("resultado_anual")
    c86 = round2(res) if res is not None else c84

    def _c(cod, val, **kw):
        return Casilla(cod, CASILLAS_390[cod], val, **kw)

    return [
        _c("01", c01),
        _c("02", c02),
        _c("03", c03),
        _c("04", c04),
        _c("05", c05),
        _c("06", c06),
        _c("33", c33),
        _c("34", c34),
        _c("47", c47),
        _c("48", c48),
        _c("49", c49),
        _c("64", c64),
        _c("65", c65),
        _c("84", c84),
        _c("86", c86),
    ]
