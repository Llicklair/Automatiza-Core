"""Regresión N1/N2 (auditoría 2026-06-25): los modelos AEAT excluyen las facturas
anuladas, incluyen las rectificativas y mantienen los borradores, y el 303 cuadra
con el libro registro de emitidas.

- N1: una factura emitida 'cancelled' NO se cuenta en el 303 (antes sí → IVA de más).
- N1: un borrador SÍ se cuenta (las compras nacen 'draft'; no regresar esto).
- N2: una rectificativa (abono, importes negados) MINORA el devengado del 303.
- Cuadre: el libro de emitidas declara el mismo conjunto/cuota que el 303.
"""

import csv
import io
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Invoice, InvoiceLine, Tenant
from app.services.aeat.casillas_303 import build_casillas_303
from app.services.reports.fiscal import build_libro_registro_csv, build_modelo_303_data
from app.services.reports.modelos_aeat import build_modelo_347_data


async def _add_invoice(db, tenant_id, client_id, number, inv_type, status, lines):
    """lines: list of (unit_price, tax_percentage). unit_price negativo = abono."""
    base_total = sum((Decimal(str(up)) for up, _ in lines), Decimal("0"))
    tax_total = sum((Decimal(str(up)) * Decimal(str(r)) / 100 for up, r in lines), Decimal("0"))
    inv = Invoice(
        id=uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, 15, tzinfo=UTC),  # Q2 2026
        amount_base=base_total,
        tax_amount=tax_total,
        amount_total=base_total + tax_total,
        status=status,
        invoice_type=inv_type,
    )
    db.add(inv)
    await db.flush()
    for i, (unit_price, rate) in enumerate(lines):
        up = Decimal(str(unit_price))
        r = Decimal(str(rate))
        db.add(
            InvoiceLine(
                invoice_id=inv.id,
                description=f"L{i}",
                quantity=1,
                unit_price=up,
                tax_percentage=r,
                total=up * (1 + r / 100),
            )
        )


async def _seed() -> str:
    """Q2 2026, emitidas al 21%: borrador 1000 (cuenta) + anulada 500 (fuera)
    + rectificativa -200 (minora). Devengado neto esperado: base 800, cuota 168."""
    async with AsyncSessionLocal() as db:
        tenant = Tenant(
            id=uuid4(), name="IVA NM Test S.L.", nif=f"B{str(uuid4().int)[:8]}", plan="starter"
        )
        db.add(tenant)
        await db.flush()
        client = Client(id=uuid4(), tenant_id=tenant.id, name="Cliente X", nif="B12345678")
        db.add(client)
        await db.flush()
        await _add_invoice(db, tenant.id, client.id, "FAC-DRAFT", "issued", "draft", [(1000, 21)])
        await _add_invoice(db, tenant.id, client.id, "FAC-CANCEL", "issued", "cancelled", [(500, 21)])
        await _add_invoice(db, tenant.id, client.id, "REC-ABONO", "rectificativa", "pending", [(-200, 21)])
        await db.commit()
        return str(tenant.id)


async def test_303_excluye_anuladas_minora_rectificativas_y_mantiene_borradores():
    tenant_id = await _seed()
    async with AsyncSessionLocal() as db:
        data = await build_modelo_303_data(db, UUID(tenant_id), quarter=2, year=2026)
    cas = {c.codigo: float(c.valor) for c in build_casillas_303(data)}

    assert cas["07"] == 800.0  # base 21%: 1000 (borrador) - 200 (abono); 500 anulada FUERA
    assert cas["09"] == 168.0  # cuota 21%: 210 - 42
    assert cas["27"] == 168.0  # total devengado


async def test_libro_emitidas_cuadra_con_el_303():
    tenant_id = await _seed()
    async with AsyncSessionLocal() as db:
        data = await build_modelo_303_data(db, UUID(tenant_id), quarter=2, year=2026)
        csv_content, _ = await build_libro_registro_csv(db, UUID(tenant_id), 2026, "emitidas")
    cas = {c.codigo: float(c.valor) for c in build_casillas_303(data)}

    rows = list(csv.reader(io.StringIO(csv_content), delimiter=";"))[1:]  # sin cabecera
    cuota_libro = round(sum(float(r[7]) for r in rows), 2)  # columna "Cuota IVA" (por línea)

    assert "FAC-CANCEL" not in csv_content  # anulada fuera del libro
    assert "REC-ABONO" in csv_content       # rectificativa dentro
    assert "FAC-DRAFT" in csv_content        # borrador dentro
    # Invariante real: libro y 303 declaran EL MISMO CONJUNTO (mismos filtros vía
    # _period_invoices_stmt). Los importes solo coinciden aquí PORQUE toda la
    # fixture cae en Q2; el total del libro es ANUAL y el del 303 TRIMESTRAL, así
    # que esta igualdad NO se sostendría con facturas en otros trimestres.
    assert cuota_libro == cas["27"] == 168.0


async def _seed_347() -> tuple[str, str]:
    """Año 2026: una emitida 4000€+21% (total 4840) y una rectificativa -1000€+21%
    (total -1210) al MISMO cliente. Neto emitidas = 3630 → supera el umbral."""
    async with AsyncSessionLocal() as db:
        tenant = Tenant(
            id=uuid4(), name="347 Test S.L.", nif=f"B{str(uuid4().int)[:8]}", plan="starter"
        )
        db.add(tenant)
        await db.flush()
        client = Client(id=uuid4(), tenant_id=tenant.id, name="Cliente 347", nif="B87654321")
        db.add(client)
        await db.flush()
        await _add_invoice(db, tenant.id, client.id, "FAC-347", "issued", "pending", [(4000, 21)])
        await _add_invoice(db, tenant.id, client.id, "REC-347", "rectificativa", "pending", [(-1000, 21)])
        await db.commit()
        return str(tenant.id), client.nif


async def test_modelo_347_minora_rectificativas():
    """Regresión: el 347 NETEA la rectificativa (importe negado) sobre el mismo NIF
    en vez de inflar el acumulado. 4840 (emitida) - 1210 (abono) = 3630."""
    tenant_id, client_nif = await _seed_347()
    async with AsyncSessionLocal() as db:
        data = await build_modelo_347_data(db, UUID(tenant_id), year=2026)

    assert data["num_declarables"] == 1
    decl = data["declarables"][0]
    assert decl["nif"] == client_nif
    # 4840 - 1210 = 3630 (NO 4840 + 1210 = 6050, que sería inflar el acumulado).
    assert decl["importe_emitidas"] == 3630.0
