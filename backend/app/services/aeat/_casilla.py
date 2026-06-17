"""Dataclass y helpers compartidos para las casillas de los modelos AEAT.

Hogar común para los builders `casillas_NNN.py` (111, 115, 130, 200, 390…).
Los modelos 130 y 303 mantienen sus propios dataclass por motivos históricos;
los nuevos usan este `Casilla` compartido.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def round2(x) -> Decimal:
    """Redondea a 2 decimales de forma tolerante (None/'' → 0)."""
    return Decimal(str(x or 0)).quantize(Decimal("0.01"))


@dataclass
class Casilla:
    codigo: str
    descripcion: str
    valor: Decimal
    editable: bool = False
    nota: str | None = None
    formato: str = "euro"  # "euro" | "numero" | "porcentaje"

    def to_dict(self) -> dict:
        return {
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "valor": float(self.valor),
            "editable": self.editable,
            "nota": self.nota,
            "formato": self.formato,
        }
