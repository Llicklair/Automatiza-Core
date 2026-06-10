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
from app.services.treasury.remittances import (
    RemittanceError,
    create_direct_debit_remittance,
    create_transfer_remittance,
    get_remittance,
    list_remittances,
    update_remittance_status,
)
from app.services.treasury.sepa import (
    Pain001Error,
    Pain008Error,
    build_pain001,
    build_pain008,
)

__all__ = [
    "CashflowAlert",
    "CashflowDay",
    "Pain001Error",
    "Pain008Error",
    "RemittanceError",
    "build_pain001",
    "build_pain008",
    "create_direct_debit_remittance",
    "create_transfer_remittance",
    "get_remittance",
    "list_remittances",
    "project_cashflow",
    "update_remittance_status",
]
