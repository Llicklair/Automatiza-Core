"""Mapeo del cálculo agregado del Modelo 111 a las casillas oficiales AEAT.

Modelo 111 — Retenciones e ingresos a cuenta del IRPF (rendimientos del trabajo y
de actividades económicas, premios…). Autoliquidación trimestral.

Se incluyen los dos bloques que usa una pyme/autónomo típico: rendimientos del
trabajo (casillas 01-03, rellenas desde nóminas) y rendimientos de actividades
económicas/profesionales (07-09, editables: dependen de facturas con retención de
profesionales), más el Total liquidación (28-30). Los bloques poco habituales
(en especie, premios, ganancias forestales, derechos de imagen) se omiten por
defecto. La casilla 28 suma las retenciones de los bloques incluidos.

Casillas verificadas contra instrucciones AEAT + Orden EHA/586/2011.
"""

from __future__ import annotations

from app.services.aeat._casilla import Casilla, round2

CASILLAS_111 = {
    "01": "Rendimientos del trabajo · Dinerarios: N.º de perceptores",
    "02": "Rendimientos del trabajo · Dinerarios: Importe de las percepciones",
    "03": "Rendimientos del trabajo · Dinerarios: Importe de las retenciones",
    "07": "Rendimientos de actividades económicas · Dinerarios: N.º de perceptores",
    "08": "Rendimientos de actividades económicas · Dinerarios: Importe de las percepciones",
    "09": "Rendimientos de actividades económicas · Dinerarios: Importe de las retenciones",
    "28": "Total liquidación: Suma de retenciones e ingresos a cuenta",
    "29": "Total liquidación: A deducir (exclusivamente si es declaración complementaria)",
    "30": "Total liquidación: Resultado a ingresar",
}


def build_casillas_111(data: dict) -> list[Casilla]:
    nperc = data.get("num_perceptores")
    if nperc is None:
        nperc = len(data.get("perceptores_trabajo_personal") or [])

    c01 = round2(nperc)
    c02 = round2(data.get("total_base_retenciones"))
    c03 = round2(data.get("total_retencion_practicada"))

    # Actividades económicas (profesionales): el MVP no las separa → editables a 0.
    c07 = round2(data.get("num_perceptores_actividades"))
    c08 = round2(data.get("base_actividades_economicas"))
    c09 = round2(data.get("retenciones_actividades_economicas"))

    c28 = round2(c03 + c09)  # suma de las retenciones de los bloques incluidos
    c29 = round2(data.get("a_deducir_complementaria"))
    c30 = round2(c28 - c29)

    def _c(cod, val, **kw):
        return Casilla(cod, CASILLAS_111[cod], val, **kw)

    return [
        _c("01", c01, formato="numero"),
        _c("02", c02),
        _c("03", c03),
        _c(
            "07",
            c07,
            editable=True,
            formato="numero",
            nota="Perceptores de actividades económicas (profesionales) con retención en sus facturas.",
        ),
        _c("08", c08, editable=True, nota="Importe de las percepciones de actividades económicas."),
        _c("09", c09, editable=True, nota="Retenciones de actividades económicas (entran en la casilla 28)."),
        _c("28", c28),
        _c("29", c29, editable=True, nota="Solo en declaración complementaria del mismo período."),
        _c("30", c30),
    ]
