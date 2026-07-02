"""Mapeo del cálculo agregado del Modelo 200 a las casillas oficiales AEAT.

Modelo 200 — Impuesto sobre Sociedades. El formulario completo tiene >1000
casillas; aquí cubrimos las CLAVE de la liquidación (preview) que se rellenan
automáticamente desde los importes agregados del ejercicio.

Casillas verificadas (Manual práctico de Sociedades 2024 de la AEAT). Notas de
línea roja:
- Las correcciones al resultado contable NO tienen una casilla-resumen única
  (van en el rango 00355–00414); no se inventa un número agregado.
- Las retenciones e ingresos a cuenta tampoco tienen casilla única (rango
  01785–01799); se omiten del preview.
- La cuota líquida (00592) en este borrador, sin deducciones, coincide con la
  cuota íntegra: se marca editable para ajuste manual.
"""

from __future__ import annotations

from app.services.aeat._casilla import Casilla, round2

CASILLAS_200 = {
    "00500": "Resultado de la cuenta de pérdidas y ganancias",
    "00552": "Base imponible",
    "00558": "Tipo de gravamen",
    "00562": "Cuota íntegra",
    "00592": "Cuota líquida",
    "00601": "Pagos fraccionados",
    "00621": "Líquido a ingresar o a devolver",
}


def build_casillas_200(data: dict) -> list[Casilla]:
    resultado_contable = round2(data.get("resultado_contable"))
    base_imponible = round2(data.get("base_imponible"))
    tipo = round2(data.get("tipo_impositivo_pct"))
    cuota_integra = round2(data.get("cuota_integra"))
    pagos = round2(data.get("pagos_fraccionados_pagados"))
    resultado = round2(data.get("resultado_declaracion"))

    return [
        Casilla("00500", CASILLAS_200["00500"], resultado_contable),
        Casilla("00552", CASILLAS_200["00552"], base_imponible),
        Casilla("00558", CASILLAS_200["00558"], tipo, formato="porcentaje"),
        Casilla("00562", CASILLAS_200["00562"], cuota_integra),
        Casilla(
            "00592",
            CASILLAS_200["00592"],
            cuota_integra,
            editable=True,
            nota="En este borrador, sin deducciones, coincide con la cuota íntegra. Ajústala si procede.",
        ),
        Casilla(
            "00601",
            CASILLAS_200["00601"],
            pagos,
            editable=True,
            nota="Pagos fraccionados estimados (Modelo 202); revísalos antes de presentar.",
        ),
        Casilla("00621", CASILLAS_200["00621"], resultado),
    ]
