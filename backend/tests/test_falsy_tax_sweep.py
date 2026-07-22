"""Barrido de la clase `or 21` (B3-bis + M5 + M6 del re-audit 2026-07-22).

`x or 21` con `Decimal('0.00')` (falsy) coerciona 0% → 21%: inventaba IVA en
líneas exentas por todo el backend. Además del arreglo sitio a sitio, el
test-puerta prohíbe el patrón para siempre.
"""

import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.models.billing import Invoice, InvoiceLine, Quote, QuoteLine
from app.db.models.crm import Client
from app.services.billing.commands import create_rectificativa
from app.services.sales.commands import convert_to_invoice
from app.services.workflow.approval_actions import _exec_create_invoice


def test_gate_sin_coercion_falsy_or21():
    """Patrón prohibido en todo backend/app: `tax_percentage ... or 21` (y
    `vat_rate ... or 21`). Si esto falla, alguien reintrodujo la clase B3."""
    root = Path(__file__).resolve().parents[1] / "app"
    pat = re.compile(r"(tax_percentage[^\n]{0,60}\bor\s+21\b)|(vat_rate[^\n]{0,40}\bor\s+21\b)")
    hits = []
    for f in root.rglob("*.py"):
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
            if pat.search(line):
                hits.append(f"{f.relative_to(root)}:{i}: {line.strip()}")
    assert not hits, "Coerción falsy 0%→21% reintroducida:\n" + "\n".join(hits)


async def _client(db, tenant_id):
    cli = Client(tenant_id=tenant_id, name="Cliente Sweep SL", nif="B44444444")
    db.add(cli)
    await db.flush()
    return cli


@pytest.mark.asyncio
class TestB3bisQuote:
    async def test_convertir_presupuesto_exento_preserva_0(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        cli = await _client(db, tenant.id)
        quote = Quote(
            tenant_id=tenant.id,
            client_id=cli.id,
            quote_number="Q-EX-1",
            date=datetime(2026, 6, 1, tzinfo=UTC),
            amount_base=Decimal("100.00"),
            tax_amount=Decimal("0.00"),
            amount_total=Decimal("100.00"),
            status="sent",
        )
        db.add(quote)
        await db.flush()
        db.add(
            QuoteLine(
                quote_id=quote.id,
                description="Formación exenta",
                quantity=Decimal("1"),
                unit_price=Decimal("100.00"),
                tax_percentage=Decimal("0.00"),
                total_line=Decimal("100.00"),
            )
        )
        await db.commit()

        await convert_to_invoice(db, quote.id, tenant.id, user.id)

        inv = (
            (
                await db.execute(
                    select(Invoice).where(Invoice.tenant_id == tenant.id).order_by(Invoice.created_at.desc())
                )
            )
            .scalars()
            .first()
        )
        lines = (await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == inv.id))).scalars().all()
        assert lines
        for ln in lines:
            # El bug persistía la línea exenta al 21% (total = base * 1.21).
            assert float(ln.tax_percentage) == 0.0
            assert float(ln.total) == 100.0


@pytest.mark.asyncio
class TestM5RectificativaSinLineas:
    async def test_original_sin_lineas_sintetiza_linea(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        cli = await _client(db, tenant.id)
        original = Invoice(
            tenant_id=tenant.id,
            client_id=cli.id,
            invoice_number="H-77",
            date=datetime(2026, 3, 1, tzinfo=UTC),
            amount_base=Decimal("100.00"),
            tax_amount=Decimal("21.00"),
            amount_total=Decimal("121.00"),
            invoice_type="issued",
            status="paid",
        )
        db.add(original)
        await db.commit()

        rect = await create_rectificativa(original.id, "anulación de histórica", tenant.id, db)

        # Antes: rectificativa a 0,00 € (y la idempotencia impedía la buena).
        assert Decimal(str(rect.amount_total)) == Decimal("-121.00")
        lines = (await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == rect.id))).scalars().all()
        assert len(lines) == 1
        assert float(lines[0].unit_price) == -100.0
        assert float(lines[0].tax_percentage) == 21.0

    async def test_original_sin_lineas_ni_importes_bloquea(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        cli = await _client(db, tenant.id)
        vacia = Invoice(
            tenant_id=tenant.id,
            client_id=cli.id,
            invoice_number="H-78",
            date=datetime(2026, 3, 2, tzinfo=UTC),
            amount_base=Decimal("0.00"),
            tax_amount=Decimal("0.00"),
            amount_total=Decimal("0.00"),
            invoice_type="issued",
            status="paid",
        )
        db.add(vacia)
        await db.commit()

        with pytest.raises(ValueError, match="líneas ni importes"):
            await create_rectificativa(vacia.id, "motivo", tenant.id, db)


@pytest.mark.asyncio
class TestM6AprobacionDelega:
    async def test_aprobacion_usa_servicio_canonico(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        params = {
            "amount_base": "100.00",
            "vat_rate": 21,
            "concept": "Proyecto aprobado",
            "client_name": "Cliente Aprobado SL",
        }

        ok, msg = await _exec_create_invoice(params, db, str(tenant.id))

        assert ok is True, msg
        inv = (
            (
                await db.execute(
                    select(Invoice).where(Invoice.tenant_id == tenant.id).order_by(Invoice.created_at.desc())
                )
            )
            .scalars()
            .first()
        )
        # Numeración canónica (next_invoice_number con lock), no la serie
        # paralela "FAC-YYYY-" por count()+1 (M6).
        assert not inv.invoice_number.startswith("FAC-")
        assert inv.status == "draft"
        lines = (await db.execute(select(InvoiceLine).where(InvoiceLine.invoice_id == inv.id))).scalars().all()
        assert len(lines) == 1
        assert float(lines[0].tax_percentage) == 21.0

    async def test_dos_aprobaciones_numeros_distintos(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        base_params = {"vat_rate": 21, "concept": "x", "client_name": "C SL"}

        ok1, _ = await _exec_create_invoice({**base_params, "amount_base": "10.00"}, db, str(tenant.id))
        ok2, _ = await _exec_create_invoice({**base_params, "amount_base": "20.00"}, db, str(tenant.id))
        assert ok1 and ok2

        nums = (await db.execute(select(Invoice.invoice_number).where(Invoice.tenant_id == tenant.id))).scalars().all()
        assert len(nums) == len(set(nums)) == 2
