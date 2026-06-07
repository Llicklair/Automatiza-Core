"""Mapeo del cálculo agregado del 303 a las casillas oficiales AEAT.

El modelo 303 vigente tiene ~80 casillas; aquí cubrimos las que se rellenan
en régimen general sin recargo de equivalencia ni operaciones intra-UE.
El resto se dejan a 0 con la opción de que el frontend permita ajuste manual
antes de presentar (caso de prorrata, regímenes especiales, etc.).

Referencia oficial: BOE Orden HFP/1124/2022 y posteriores.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

# Casillas del Modelo 303 — régimen general
# Listado simplificado de las casillas más comunes que se rellenan
# automáticamente desde facturas emitidas/recibidas.
CASILLAS_303 = {
    # IVA devengado (ventas)
    "01": "Régimen General — Base imponible al 4%",
    "02": "Régimen General — Tipo aplicable 4%",
    "03": "Régimen General — Cuota devengada 4%",
    "04": "Régimen General — Base imponible al 10%",
    "05": "Régimen General — Tipo aplicable 10%",
    "06": "Régimen General — Cuota devengada 10%",
    "07": "Régimen General — Base imponible al 21%",
    "08": "Régimen General — Tipo aplicable 21%",
    "09": "Régimen General — Cuota devengada 21%",
    # Totales devengado
    "27": "Total cuota devengada",
    # IVA deducible (compras corrientes)
    "28": "Cuotas soportadas en operaciones interiores corrientes — Base",
    "29": "Cuotas soportadas en operaciones interiores corrientes — Cuota",
    "30": "Cuotas soportadas en operaciones interiores con bienes de inversión — Base",
    "31": "Cuotas soportadas en operaciones interiores con bienes de inversión — Cuota",
    # Totales deducible
    "45": "Total a deducir",
    # Resultado
    "46": "Resultado del régimen general (27 - 45)",
    "64": "Resultado de la liquidación",
    "65": "% atribuible al Estado",
    "66": "Atribuible al Estado",
    "67": "Cuotas a compensar de periodos anteriores",
    "69": "Resultado (64 - 67)",
    "71": "Resultado de la autoliquidación",
}


@dataclass
class Casilla303:
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


def _round2(x: float | Decimal) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"))


def build_casillas_303(data: dict) -> list[Casilla303]:
    """Convierte el dict de `build_modelo_303_data` en casillas oficiales 303.

    `data` debe tener la forma:
      {
        "tenant": {...},
        "quarter": int, "year": int,
        "vat_collected": [{"rate": float, "base": float, "quota": float}, ...],
        "vat_deducted":  [{"rate": float, "base": float, "quota": float}, ...],
      }
    """
    collected_by_rate: dict[float, dict] = {
        float(r["rate"]): r for r in data.get("vat_collected", [])
    }
    deducted_by_rate: dict[float, dict] = {
        float(r["rate"]): r for r in data.get("vat_deducted", [])
    }

    casillas: list[Casilla303] = []

    # Régimen general — tres tipos básicos
    tipo_4 = collected_by_rate.get(4.0, {"base": 0, "quota": 0})
    tipo_10 = collected_by_rate.get(10.0, {"base": 0, "quota": 0})
    tipo_21 = collected_by_rate.get(21.0, {"base": 0, "quota": 0})

    casillas += [
        Casilla303("01", CASILLAS_303["01"], _round2(tipo_4["base"])),
        Casilla303("02", CASILLAS_303["02"], Decimal("4.00")),
        Casilla303("03", CASILLAS_303["03"], _round2(tipo_4["quota"])),
        Casilla303("04", CASILLAS_303["04"], _round2(tipo_10["base"])),
        Casilla303("05", CASILLAS_303["05"], Decimal("10.00")),
        Casilla303("06", CASILLAS_303["06"], _round2(tipo_10["quota"])),
        Casilla303("07", CASILLAS_303["07"], _round2(tipo_21["base"])),
        Casilla303("08", CASILLAS_303["08"], Decimal("21.00")),
        Casilla303("09", CASILLAS_303["09"], _round2(tipo_21["quota"])),
    ]

    total_devengado = sum((c.valor for c in casillas if c.codigo in {"03", "06", "09"}), Decimal("0"))
    casillas.append(Casilla303("27", CASILLAS_303["27"], _round2(total_devengado)))

    # Deducible — agregamos todas las cuotas soportadas en operaciones corrientes (no bienes inversión)
    base_28 = sum((Decimal(str(r["base"])) for r in deducted_by_rate.values()), Decimal("0"))
    cuota_29 = sum((Decimal(str(r["quota"])) for r in deducted_by_rate.values()), Decimal("0"))
    casillas += [
        Casilla303(
            "28", CASILLAS_303["28"], _round2(base_28),
            editable=True,
            nota="Si parte corresponde a bienes de inversión, muévelo a la casilla 30.",
        ),
        Casilla303("29", CASILLAS_303["29"], _round2(cuota_29)),
        Casilla303(
            "30", CASILLAS_303["30"], Decimal("0"),
            editable=True,
            nota="Base de bienes de inversión (si los hay). Por defecto 0.",
        ),
        Casilla303(
            "31", CASILLAS_303["31"], Decimal("0"),
            editable=True,
            nota="Cuota de bienes de inversión.",
        ),
    ]

    total_deducir = cuota_29
    casillas.append(Casilla303("45", CASILLAS_303["45"], _round2(total_deducir)))

    resultado_46 = total_devengado - total_deducir
    casillas.append(Casilla303("46", CASILLAS_303["46"], _round2(resultado_46)))

    # Suponemos 100% Estado (no País Vasco/Navarra)
    casillas += [
        Casilla303("64", CASILLAS_303["64"], _round2(resultado_46)),
        Casilla303("65", CASILLAS_303["65"], Decimal("100.00")),
        Casilla303("66", CASILLAS_303["66"], _round2(resultado_46)),
        Casilla303(
            "67", CASILLAS_303["67"], Decimal("0"),
            editable=True,
            nota="Si tienes saldo a compensar del trimestre anterior, indícalo aquí.",
        ),
    ]
    resultado_69 = resultado_46  # sin compensaciones por defecto
    casillas += [
        Casilla303("69", CASILLAS_303["69"], _round2(resultado_69)),
        Casilla303("71", CASILLAS_303["71"], _round2(resultado_69)),
    ]

    return casillas
