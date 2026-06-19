"""Mapeo del cálculo agregado del Modelo 130 a las casillas oficiales AEAT.

Modelo 130 — IRPF, pago fraccionado en estimación directa. Cubrimos el Apartado I
(actividades económicas en estimación directa, casillas 01-07) y el Apartado III
(total liquidación, casillas 12-19). El Apartado II (actividades agrícolas,
ganaderas, forestales y pesqueras, casillas 08-11) se omite por defecto: N/A para
la mayoría de pymes/autónomos.

Las casillas que dependen de datos cross-period o del contribuyente (05, 06, 13,
15, 16, 18) se devuelven a 0 marcadas como `editable=True` con nota explicativa —
NO se inventan importes. El wizard fiscal o el usuario las ajusta antes de presentar.

Referencia oficial: Orden HAC/1264/2018 (modelo 130). Mapeo de casillas verificado
contra la guía oficial casilla por casilla (AEAT / Verifácturamos / Infoautónomos).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# Descripciones oficiales de las casillas del Modelo 130.
CASILLAS_130 = {
    # Apartado I — Actividades económicas en estimación directa
    "01": "Ingresos computables",
    "02": "Gastos fiscalmente deducibles",
    "03": "Rendimiento neto (casilla 01 − casilla 02)",
    "04": "20 % del rendimiento neto (casilla 03, si es positivo)",
    "05": "Pagos fraccionados de trimestres anteriores",
    "06": "Retenciones e ingresos a cuenta soportados",
    "07": "Pago fraccionado previo (casilla 04 − 05 − 06)",
    # Apartado III — Total liquidación
    "12": "Suma de pagos fraccionados (casilla 07 + casilla 11)",
    "13": "Minoración por rendimientos netos reducidos (art. 110.3.c RIRPF)",
    "14": "Diferencia (casilla 12 − casilla 13)",
    "15": "Resultados negativos de trimestres anteriores (mismo ejercicio)",
    "16": "Deducción por adquisición o rehabilitación de vivienda habitual",
    "17": "Diferencia (casilla 14 − casilla 15 − casilla 16)",
    "18": "A deducir (exclusivamente en declaración complementaria)",
    "19": "Resultado de la autoliquidación (casilla 17 − casilla 18)",
}


@dataclass
class Casilla130:
    codigo: str
    descripcion: str
    valor: Decimal
    editable: bool = False
    nota: str | None = None

    def to_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "valor": float(self.valor),
            "editable": self.editable,
            "nota": self.nota,
        }


def _round2(x) -> Decimal:
    # ROUND_HALF_UP: criterio fiscal AEAT, coherente con reports/fiscal.py.
    return Decimal(str(x or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_casillas_130(data: dict) -> list[Casilla130]:
    """Convierte el dict de `build_modelo_130_data` en casillas oficiales 130.

    Deriva las casillas calculadas (03, 04, 07, 12, 14, 17, 19) a partir de los
    importes base; las casillas que requieren datos del contribuyente (05, 06,
    13, 15, 16, 18) se toman de `data` si vienen (por defecto 0) y se marcan
    editables.
    """
    # --- Apartado I — estimación directa ---
    c01 = _round2(data.get("ingresos_acumulados"))
    c02 = _round2(data.get("gastos_acumulados"))
    c03 = _round2(c01 - c02)  # rendimiento neto acumulado
    c04 = _round2(c03 * Decimal("0.20")) if c03 > 0 else Decimal("0.00")
    c05 = _round2(data.get("pagos_fraccionados_anteriores"))
    c06 = _round2(data.get("retenciones_soportadas"))
    c07 = _round2(c04 - c05 - c06)

    # --- Apartado III (el Apartado II, agrícola, se omite: casilla 11 = 0) ---
    c11 = Decimal("0.00")
    c12 = _round2(c07 + c11)
    if c12 < 0:
        c12 = Decimal("0.00")
    c13 = _round2(data.get("deduccion_rentas_bajas"))
    c14 = _round2(c12 - c13)
    c15 = _round2(data.get("resultados_negativos_anteriores"))
    c16 = _round2(data.get("deduccion_vivienda_habitual"))
    c17 = _round2(c14 - c15 - c16)
    c18 = _round2(data.get("a_deducir_complementaria"))
    c19 = _round2(c17 - c18)

    def _c(cod, valor, editable=False, nota=None):
        return Casilla130(cod, CASILLAS_130[cod], valor, editable=editable, nota=nota)

    return [
        _c("01", c01),
        _c("02", c02),
        _c("03", c03),
        _c("04", c04),
        _c("05", c05, editable=True,
           nota="Suma de los resultados positivos (casilla 07) de los modelos 130 ya presentados este ejercicio."),
        _c("06", c06, editable=True,
           nota="Retenciones de IRPF que te han practicado tus clientes, acumuladas desde el 1 de enero."),
        _c("07", c07),
        _c("12", c12),
        _c("13", c13, editable=True,
           nota="Solo si el rendimiento neto anual previsto es ≤ 12.000 €: entre 100 € y 400 €/trimestre según escala."),
        _c("14", c14),
        _c("15", c15, editable=True,
           nota="Importe negativo de la casilla 19 de trimestres anteriores del mismo ejercicio (no superior a la casilla 14)."),
        _c("16", c16, editable=True,
           nota="Solo si la casilla 14 es positiva y pagas un préstamo por tu vivienda habitual."),
        _c("17", c17),
        _c("18", c18, editable=True,
           nota="Solo en declaración complementaria: resultado de autoliquidaciones previas del mismo período."),
        _c("19", c19),
    ]
