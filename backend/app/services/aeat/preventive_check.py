"""Asistente fiscal preventivo — chequeos antes de cerrar trimestre.

Antes de presentar el 303/130/111, recorre las facturas del periodo y
detecta riesgos típicos que se le pasan a una pyme sin asesor:

  - Facturas recibidas sin NIF de proveedor → IVA NO deducible.
  - Facturas recibidas sin líneas → cuota IVA no se computa.
  - Facturas emitidas/recibidas con totales descuadrados (>1 céntimo).
  - Facturas emitidas en `status='draft'` con fecha dentro del periodo →
    se olvidaron de cerrarlas y NO entrarán en el 303.
  - IVA repercutido > 0 pero IVA deducible == 0 (0 gastos del trimestre).
  - Facturas emitidas en periodo sin registro Verifactu cuando el tenant
    está en modo `voluntary` → incumplimiento del RD 1007/2023.
  - Documentos clasificados como `factura_recibida` (OCR) sin Invoice
    asociada → datos extraídos pero no registrados.

Devuelve `list[Finding]` ordenados por severidad descendente. La capa de
ruta los devuelve al frontend `/impuestos`, y la tool del compliance
agent los expone al coordinador (`check_quarter_preventive`).
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.billing import Invoice, VerifactuConfig, VerifactuRecord

_QUARTER_MONTHS = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
_BALANCE_TOLERANCE_CENTS = Decimal("0.02")


@dataclass
class Finding:
    code: str
    severity: str  # "high" | "medium" | "low"
    message: str
    suggested_action: str
    source_invoice_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "suggested_action": self.suggested_action,
            "source_invoice_ids": list(self.source_invoice_ids),
        }


_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


async def check_quarter(
    db: AsyncSession,
    tenant_id: UUID,
    quarter: int,
    year: int,
) -> list[Finding]:
    """Ejecuta los chequeos preventivos del trimestre."""
    if quarter not in _QUARTER_MONTHS:
        raise ValueError(f"Trimestre inválido: {quarter}")

    m_start, m_end = _QUARTER_MONTHS[quarter]
    start = date(year, m_start, 1)
    end = date(year, m_end, monthrange(year, m_end)[1])

    invoices_q = await db.execute(
        sa.select(Invoice)
        .options(joinedload(Invoice.lines), joinedload(Invoice.client))
        .where(
            Invoice.tenant_id == tenant_id,
            sa.func.date(Invoice.date) >= start,
            sa.func.date(Invoice.date) <= end,
        )
    )
    invoices: list[Invoice] = invoices_q.unique().scalars().all()

    findings: list[Finding] = []
    findings.extend(_check_received_without_supplier_nif(invoices))
    findings.extend(_check_invoices_without_lines(invoices))
    findings.extend(_check_amount_mismatch(invoices))
    findings.extend(_check_draft_in_period(invoices))
    findings.extend(_check_imbalance_no_purchases(invoices))
    findings.extend(await _check_verifactu_missing(db, tenant_id, invoices))
    findings.extend(await _check_unlinked_received_documents(db, tenant_id, start, end))

    findings.sort(key=lambda f: (_SEVERITY_RANK.get(f.severity, 9), f.code))
    return findings


# ─── Chequeos individuales ──────────────────────────────────────────────


def _check_received_without_supplier_nif(invoices: list[Invoice]) -> list[Finding]:
    bad = [
        inv
        for inv in invoices
        if inv.invoice_type == "received"
        and (inv.client is None or not (inv.client.nif or "").strip())
    ]
    if not bad:
        return []
    return [
        Finding(
            code="received_without_supplier_nif",
            severity="high",
            message=(
                f"{len(bad)} factura(s) recibida(s) sin NIF de proveedor. "
                f"La AEAT no admite IVA deducible sin NIF identificado."
            ),
            suggested_action=(
                "Edita cada factura recibida y completa el NIF del proveedor "
                "antes de presentar el 303. Si no lo tienes, no incluyas la "
                "cuota como deducible."
            ),
            source_invoice_ids=[str(i.id) for i in bad],
        )
    ]


def _check_invoices_without_lines(invoices: list[Invoice]) -> list[Finding]:
    bad = [inv for inv in invoices if not (inv.lines or [])]
    if not bad:
        return []
    return [
        Finding(
            code="invoices_without_lines",
            severity="medium",
            message=(
                f"{len(bad)} factura(s) sin líneas. La base imponible y la "
                f"cuota IVA no se computan en el cálculo del 303."
            ),
            suggested_action=(
                "Abre cada factura y añade al menos una línea con base e IVA "
                "para que entre en la liquidación."
            ),
            source_invoice_ids=[str(i.id) for i in bad],
        )
    ]


def _check_amount_mismatch(invoices: list[Invoice]) -> list[Finding]:
    bad: list[Invoice] = []
    for inv in invoices:
        base = Decimal(inv.amount_base or 0)
        tax = Decimal(inv.tax_amount or 0)
        total = Decimal(inv.amount_total or 0)
        if abs((base + tax) - total) > _BALANCE_TOLERANCE_CENTS:
            bad.append(inv)
    if not bad:
        return []
    return [
        Finding(
            code="amount_mismatch",
            severity="medium",
            message=(
                f"{len(bad)} factura(s) con totales descuadrados "
                f"(base + IVA ≠ total)."
            ),
            suggested_action=(
                "Recalcula la factura desde sus líneas o ajusta los totales "
                "para que sean consistentes."
            ),
            source_invoice_ids=[str(i.id) for i in bad],
        )
    ]


def _check_draft_in_period(invoices: list[Invoice]) -> list[Finding]:
    bad = [
        inv
        for inv in invoices
        if (inv.status or "").lower() == "draft" and inv.invoice_type == "issued"
    ]
    if not bad:
        return []
    return [
        Finding(
            code="draft_issued_in_period",
            severity="high",
            message=(
                f"{len(bad)} factura(s) emitida(s) están en estado 'borrador' "
                f"dentro del trimestre. No entrarán en el Modelo 303."
            ),
            suggested_action=(
                "Confirma las facturas (paso 'borrador' → 'emitida') antes "
                "de presentar el 303. Si son cancelaciones, márcalas como "
                "anuladas explícitamente."
            ),
            source_invoice_ids=[str(i.id) for i in bad],
        )
    ]


def _check_imbalance_no_purchases(invoices: list[Invoice]) -> list[Finding]:
    issued = [i for i in invoices if i.invoice_type == "issued"]
    received = [i for i in invoices if i.invoice_type == "received"]
    vat_issued = sum(Decimal(i.tax_amount or 0) for i in issued)
    if vat_issued > 0 and not received:
        return [
            Finding(
                code="no_received_invoices",
                severity="medium",
                message=(
                    f"El trimestre tiene IVA repercutido por {float(vat_issued):.2f} € "
                    f"pero 0 facturas recibidas. Quizá te falta registrar gastos."
                ),
                suggested_action=(
                    "Revisa el escáner de facturas y la bandeja IA por si hay "
                    "facturas de proveedor sin registrar. Cada euro deducible "
                    "ahorra IVA a pagar."
                ),
            )
        ]
    return []


async def _check_verifactu_missing(
    db: AsyncSession, tenant_id: UUID, invoices: list[Invoice]
) -> list[Finding]:
    """Si el tenant está en modo `voluntary`, cada factura emitida del
    periodo debería tener un registro Verifactu. Si falta → riesgo de
    sanción del RD 1007/2023.
    """
    cfg_q = await db.execute(
        sa.select(VerifactuConfig).where(VerifactuConfig.tenant_id == tenant_id)
    )
    cfg = cfg_q.scalar_one_or_none()
    if cfg is None or (cfg.mode or "").lower() != "voluntary":
        return []

    issued_ids = [i.id for i in invoices if i.invoice_type == "issued"]
    if not issued_ids:
        return []

    have_q = await db.execute(
        sa.select(VerifactuRecord.invoice_id).where(
            VerifactuRecord.invoice_id.in_(issued_ids)
        )
    )
    have = {row[0] for row in have_q.all()}
    missing = [iid for iid in issued_ids if iid not in have]
    if not missing:
        return []
    return [
        Finding(
            code="verifactu_records_missing",
            severity="high",
            message=(
                f"{len(missing)} factura(s) emitida(s) en modo Verifactu "
                f"voluntary sin registro en la cadena. Incumplimiento del "
                f"RD 1007/2023."
            ),
            suggested_action=(
                "Ejecuta el backfill Verifactu desde Ajustes → Verifactu "
                "antes de cerrar el trimestre."
            ),
            source_invoice_ids=[str(i) for i in missing],
        )
    ]


async def _check_unlinked_received_documents(
    db: AsyncSession, tenant_id: UUID, start: date, end: date
) -> list[Finding]:
    """Documentos clasificados como `factura_recibida` (vía OCR) que no
    tienen Invoice asociada → datos extraídos pero no registrados, IVA
    deducible que se pierde.
    """
    from app.db.models.tenant import TenantDocument

    docs_q = await db.execute(
        sa.select(TenantDocument).where(
            TenantDocument.tenant_id == tenant_id,
            TenantDocument.category == "factura_recibida",
            sa.func.date(TenantDocument.created_at) >= start,
            sa.func.date(TenantDocument.created_at) <= end,
        )
    )
    docs = docs_q.scalars().all()
    if not docs:
        return []

    linked_q = await db.execute(
        sa.select(Invoice.document_id).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "received",
            Invoice.is_demo.is_(False),  # datos demo del onboarding NUNCA en fiscal
            Invoice.document_id.in_([d.id for d in docs]),
        )
    )
    linked = {row[0] for row in linked_q.all() if row[0] is not None}
    unlinked = [d for d in docs if d.id not in linked]
    if not unlinked:
        return []
    return [
        Finding(
            code="unlinked_received_documents",
            severity="medium",
            message=(
                f"{len(unlinked)} documento(s) clasificado(s) como factura "
                f"recibida no están convertidos en factura registrada. "
                f"El IVA deducible no entra en el 303 mientras no se registren."
            ),
            suggested_action=(
                "Ve a /escaner o /documentos, abre los PDFs marcados y "
                "confirma la conversión a factura recibida."
            ),
        )
    ]
