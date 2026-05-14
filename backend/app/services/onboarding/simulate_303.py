"""Simulador del Modelo 303 con datos ejemplo (UI.SIM).

Función pura — NO consulta la BD del tenant. Devuelve un resultado de
Modelo 303 calculado sobre un dataset hard-coded de facturas ejemplo que
representan un autónomo prototípico (peluquería, despacho de abogados o
fontanero) en su Q1 fiscal.

Objetivo: al final del onboarding (UI.ONB), mostrar al usuario un 303
"real" para que vea el sistema funcionando antes de meter sus datos.

Reglas de diseño:
- Sin acoplamiento a `build_modelo_303_data` (que sí consulta BD) —
  duplicamos el cálculo de IVA agregado por tipo, pero sobre datos
  estáticos. La duplicación es deliberada para mantener este simulador
  totalmente independiente.
- Cifras realistas pero ficticias. Los NIF de clientes son tipo "X..."
  para que un usuario despistado no los confunda con NIF reales.
- Resultado siempre positivo a ingresar (~270€) para hacer evidente al
  usuario qué significa el modelo.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal


@dataclass(frozen=True)
class SampleLine:
    base: Decimal
    rate: Decimal  # %
    direction: Literal["devengado", "deducible"]
    concept: str


# Q1 ficticio — autónomo de servicios profesionales.
# Ingresos: ~5 facturas pequeñas a clientes B2B + 1 cliente final.
# Gastos: alquiler oficina + autónomo SS + suministros + un curso.
SAMPLE_LINES: tuple[SampleLine, ...] = (
    SampleLine(Decimal("1200.00"), Decimal("21"), "devengado", "Asesoría enero — Cliente XAcme"),
    SampleLine(Decimal("950.00"), Decimal("21"), "devengado", "Asesoría febrero — Cliente XBeta"),
    SampleLine(Decimal("1450.00"), Decimal("21"), "devengado", "Asesoría marzo — Cliente XGamma"),
    SampleLine(Decimal("300.00"), Decimal("21"), "devengado", "Consultoría puntual — Cliente XDelta"),
    SampleLine(Decimal("180.00"), Decimal("10"), "devengado", "Servicios reducidos — Cliente XEpsilon"),
    SampleLine(Decimal("700.00"), Decimal("21"), "deducible", "Alquiler oficina coworking"),
    SampleLine(Decimal("120.00"), Decimal("21"), "deducible", "Suministros y material"),
    SampleLine(Decimal("250.00"), Decimal("21"), "deducible", "Curso fiscalidad autónomos"),
    SampleLine(Decimal("65.00"), Decimal("10"), "deducible", "Manutención profesional"),
)


def _round2(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def simulate_modelo_303(quarter: int = 1, year: int = 2026) -> dict:
    """Devuelve el resultado del Modelo 303 sobre el dataset ejemplo.

    Estructura paralela a `build_modelo_303_data` pero con `is_simulation=True`
    para que la UI muestre badge "Datos ejemplo".
    """
    if quarter not in (1, 2, 3, 4):
        raise ValueError(f"Trimestre inválido: {quarter}")

    devengado: dict[Decimal, dict] = {}
    deducible: dict[Decimal, dict] = {}

    for line in SAMPLE_LINES:
        bucket = devengado if line.direction == "devengado" else deducible
        slot = bucket.setdefault(line.rate, {"rate": float(line.rate), "base": Decimal("0"), "quota": Decimal("0")})
        slot["base"] += line.base
        slot["quota"] += line.base * line.rate / Decimal("100")

    total_devengado_base = sum((s["base"] for s in devengado.values()), Decimal("0"))
    total_devengado_quota = sum((s["quota"] for s in devengado.values()), Decimal("0"))
    total_deducible_base = sum((s["base"] for s in deducible.values()), Decimal("0"))
    total_deducible_quota = sum((s["quota"] for s in deducible.values()), Decimal("0"))

    resultado = total_devengado_quota - total_deducible_quota

    def _serialize_map(m: dict[Decimal, dict]) -> list[dict]:
        out = []
        for rate in sorted(m.keys()):
            row = m[rate]
            out.append(
                {
                    "rate": row["rate"],
                    "base": _round2(row["base"]),
                    "quota": _round2(row["quota"]),
                }
            )
        return out

    return {
        "is_simulation": True,
        "year": year,
        "quarter": quarter,
        "tenant_name": "Empresa Ejemplo S.L.",
        "tenant_nif": "X00000000",
        "iva_devengado": _serialize_map(devengado),
        "iva_deducible": _serialize_map(deducible),
        "totals": {
            "devengado_base": _round2(total_devengado_base),
            "devengado_quota": _round2(total_devengado_quota),
            "deducible_base": _round2(total_deducible_base),
            "deducible_quota": _round2(total_deducible_quota),
            "resultado": _round2(resultado),
        },
        "explanation": {
            "headline": (
                "Esto es lo que pagarías a Hacienda este trimestre con estos datos ejemplo."
            ),
            "bullets": [
                f"IVA cobrado a clientes: {_round2(total_devengado_quota):.2f}€",
                f"IVA pagado a proveedores: {_round2(total_deducible_quota):.2f}€",
                f"Diferencia a ingresar: {_round2(resultado):.2f}€",
            ],
            "footer": (
                "Con tus datos reales, AutomatizaPyme genera y presenta este modelo "
                "trimestralmente. La diferencia entre ver esto y rellenarlo a mano: minutos."
            ),
        },
    }
