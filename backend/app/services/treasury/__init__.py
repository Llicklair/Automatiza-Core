"""Servicios de tesorería (F2.7 — Beta → Producción).

Dos motores complementarios:

  - `projection`  — Cashflow proyectado a N días (cobros previstos +
                     pagos previstos + nóminas previstas) con detección
                     de tensión de liquidez.
  - `sepa`        — Construcción de ficheros SEPA pain.001.001.03 para
                     remesas de transferencias salientes (pagos masivos
                     a proveedores).
"""

from app.services.treasury.projection import (
    CashflowAlert,
    CashflowDay,
    project_cashflow,
)
from app.services.treasury.sepa import Pain001Error, build_pain001

__all__ = [
    "CashflowAlert",
    "CashflowDay",
    "Pain001Error",
    "build_pain001",
    "project_cashflow",
]
