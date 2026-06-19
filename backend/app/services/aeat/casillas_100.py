"""Mapeo del cálculo agregado del Modelo 100 a las casillas oficiales AEAT.

Modelo 100 — IRPF, Declaración de la Renta. El formulario tiene >2000 casillas;
aquí cubrimos las CLAVE de la liquidación (preview) que se rellenan desde los
importes agregados de la actividad económica.

Casillas verificadas para Renta 2024/2025 (zona de liquidación 500–700, estable
entre ambos ejercicios). Notas de línea roja:
- Las casillas del Modelo 100 PUEDEN cambiar de un ejercicio a otro: este mapeo es
  válido para 2024/2025. Revísalo si la AEAT renumera.
- La cuota íntegra se desglosa oficialmente en estatal (0545) + autonómica (0546);
  en este preview, sin deducciones, se muestra agregada en 0595.
- Las retenciones separan trabajo (0596) y actividades económicas (0599); aquí se
  muestran agregadas en 0596 (editable).
"""

from __future__ import annotations

from app.services.aeat._casilla import Casilla, round2

CASILLAS_100 = {
    "0224": "Rendimiento neto de actividades económicas",
    "0500": "Base liquidable general",
    "0519": "Suma del mínimo personal y familiar",
    "0595": "Cuota resultante de la autoliquidación",
    "0596": "Retenciones e ingresos a cuenta",
    "0604": "Pagos fraccionados (Modelo 130)",
    "0670": "Resultado de la declaración",
}


def build_casillas_100(data: dict) -> list[Casilla]:
    rendimiento = round2(data.get("rendimiento_neto"))
    base_liquidable = round2(data.get("base_liquidable"))
    minimo = round2(data.get("minimo_personal"))
    cuota_integra = round2(data.get("cuota_integra"))
    retenciones = round2(data.get("retenciones_soportadas"))
    pagos = round2(data.get("pagos_fraccionados_pagados"))
    resultado = round2(data.get("resultado_declaracion"))

    return [
        Casilla("0224", CASILLAS_100["0224"], rendimiento,
                nota="Estimación directa; importe agregado de la actividad económica."),
        Casilla("0500", CASILLAS_100["0500"], base_liquidable),
        Casilla("0519", CASILLAS_100["0519"], minimo, editable=True,
                nota="Depende de circunstancias personales y familiares; revísalo."),
        Casilla("0595", CASILLAS_100["0595"], cuota_integra, editable=True,
                nota="El modelo desglosa cuota estatal (0545) + autonómica (0546); preview agregado sin deducciones."),
        Casilla("0596", CASILLAS_100["0596"], retenciones, editable=True,
                nota="El modelo separa trabajo (0596) y actividades económicas (0599); aquí agregadas."),
        Casilla("0604", CASILLAS_100["0604"], pagos),
        Casilla("0670", CASILLAS_100["0670"], resultado),
    ]
