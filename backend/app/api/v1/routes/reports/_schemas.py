"""Pydantic schemas for reports endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class SnapshotSectionInvoices(BaseModel):
    ingresos_total: float
    gastos_total: float
    margen_bruto: float
    margen_pct: float
    facturas_emitidas: int
    facturas_recibidas: int
    facturas_pendientes_cobro: int
    importe_pendiente_cobro: float


class SnapshotSectionBanking(BaseModel):
    total_ingresos: float
    total_gastos: float
    saldo_neto: float
    transacciones: int
    reconciliadas: int


class SnapshotSectionHR(BaseModel):
    empleados_activos: int
    coste_nominas: float
    nominas_pagadas: int
    nominas_pendientes: int


class SnapshotSectionClients(BaseModel):
    total_clientes: int
    nuevos_periodo: int
    top_client_name: str | None
    top_client_amount: float


class CompanySnapshot(BaseModel):
    month: str  # "2026-03"
    generated_at: datetime
    facturas: SnapshotSectionInvoices
    banca: SnapshotSectionBanking
    rrhh: SnapshotSectionHR
    clientes: SnapshotSectionClients
    resumen_ejecutivo: str


class FiscalIVA(BaseModel):
    repercutido_21: float = 0.0
    repercutido_10: float = 0.0
    repercutido_4: float = 0.0
    total_repercutido: float = 0.0
    base_repercutido: float = 0.0
    soportado_21: float = 0.0
    soportado_10: float = 0.0
    soportado_4: float = 0.0
    total_soportado: float = 0.0
    base_soportado: float = 0.0
    resultado_iva: float = 0.0


class FiscalIRPF(BaseModel):
    retenciones_nominas: float = 0.0
    retenciones_facturas: float = 0.0
    total_retenciones: float = 0.0


class FiscalIS(BaseModel):
    ingresos_brutos: float = 0.0
    gastos_deducibles: float = 0.0
    base_imponible: float = 0.0
    tipo_estimado: float = 25.0
    cuota_estimada: float = 0.0


class FiscalSnapshot(BaseModel):
    period: str
    period_label: str
    generated_at: datetime
    iva: FiscalIVA
    irpf: FiscalIRPF
    impuesto_sociedades: FiscalIS
    resumen_ejecutivo: str


class ReportOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    file_name: str
    file_size: int
    category: str | None
    created_at: datetime
