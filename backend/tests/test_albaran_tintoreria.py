"""Vertical tintorería T1+T2 (spec-tintoreria.md).

T1 — estados del ciclo mostrador: recibido → en_proceso → listo → delivered
(entregado, registra quién/cuándo) y anulado (revierte stock). El descuento de
stock ocurre al confirmar O entregar (idempotente: no duplica).
T2 — ticket-resguardo 80 mm con QR del número de albarán.
"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.db.models.billing import DeliveryNote, DeliveryNoteLine
from app.db.models.crm import Client
from app.db.models.inventory import Product
from app.services.sales.albaran_ticket import render_albaran_ticket_html
from app.services.sales.commands import update_albaran_status


async def _seed_albaran(db, tenant_id, *, status="recibido", with_product=False, stock=10):
    cli = Client(tenant_id=tenant_id, name="Cliente Tinte", phone="600111222")
    db.add(cli)
    await db.flush()
    product = None
    if with_product:
        product = Product(tenant_id=tenant_id, name="Quitamanchas", price=5, stock_quantity=stock)
        db.add(product)
        await db.flush()
    note = DeliveryNote(
        tenant_id=tenant_id,
        client_id=cli.id,
        albaran_number="ALB-T-001",
        date=datetime(2026, 7, 22, tzinfo=UTC).date(),
        status=status,
        notes="2 trajes, mancha en solapa",
        amount_base=Decimal("20.00"),
        tax_amount=Decimal("4.20"),
        amount_total=Decimal("24.20"),
    )
    db.add(note)
    await db.flush()
    db.add(
        DeliveryNoteLine(
            albaran_id=note.id,
            product_id=product.id if product else None,
            description="Limpieza traje",
            quantity=Decimal("2"),
            unit_price=Decimal("10.00"),
            tax_percentage=Decimal("21.00"),
            total=Decimal("24.20"),
        )
    )
    await db.commit()
    return note, product


@pytest.mark.asyncio
class TestEstadosTintoreria:
    async def test_ciclo_completo_y_registro_de_entrega(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        note, _ = await _seed_albaran(db, tenant.id, status="recibido")

        for estado in ("en_proceso", "listo"):
            note = await update_albaran_status(note.id, tenant.id, estado, db, user_id=user.id)
            assert note.status == estado
            assert note.delivered_at is None

        note = await update_albaran_status(note.id, tenant.id, "delivered", db, user_id=user.id)
        assert note.status == "delivered"
        assert note.delivered_at is not None
        assert note.delivered_by == user.id

    async def test_entregar_descuenta_stock_y_anular_lo_devuelve(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        note, product = await _seed_albaran(db, tenant.id, status="listo", with_product=True, stock=10)

        await update_albaran_status(note.id, tenant.id, "delivered", db, user_id=user.id)
        await db.refresh(product)
        assert float(product.stock_quantity) == 8.0  # 10 - 2

        await update_albaran_status(note.id, tenant.id, "anulado", db, user_id=user.id)
        await db.refresh(product)
        assert float(product.stock_quantity) == 10.0  # revertido

    async def test_confirmed_y_luego_delivered_no_descuenta_doble(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        note, product = await _seed_albaran(db, tenant.id, status="draft", with_product=True, stock=10)

        await update_albaran_status(note.id, tenant.id, "confirmed", db, user_id=user.id)
        await update_albaran_status(note.id, tenant.id, "delivered", db, user_id=user.id)
        await db.refresh(product)
        assert float(product.stock_quantity) == 8.0  # una sola vez

    async def test_servicios_no_bloquean_entrega_ni_tocan_stock(self, db, seed_tenant_and_user):
        # Una tintorería vende SERVICIOS (limpieza, planchado) sin stock físico.
        # Antes, entregar un albarán con un servicio (stock 0) reventaba con
        # "Stock insuficiente"; y anular sumaba stock a un servicio jamás
        # descontado. Ambos caminos deben ignorar item_type="service".
        tenant, user, _t = seed_tenant_and_user
        cli = Client(tenant_id=tenant.id, name="Cliente Servicios")
        db.add(cli)
        await db.flush()
        servicio = Product(tenant_id=tenant.id, name="Limpieza traje", item_type="service", price=12, stock_quantity=0)
        producto = Product(tenant_id=tenant.id, name="Quitamanchas", item_type="product", price=5, stock_quantity=10)
        db.add_all([servicio, producto])
        await db.flush()
        note = DeliveryNote(
            tenant_id=tenant.id,
            client_id=cli.id,
            albaran_number="ALB-T-SRV",
            date=datetime(2026, 7, 22, tzinfo=UTC).date(),
            status="listo",
            amount_base=Decimal("29.00"),
            tax_amount=Decimal("6.09"),
            amount_total=Decimal("35.09"),
        )
        db.add(note)
        await db.flush()
        db.add_all(
            [
                DeliveryNoteLine(
                    albaran_id=note.id,
                    product_id=servicio.id,
                    description="Limpieza traje",
                    quantity=Decimal("2"),
                    unit_price=Decimal("12.00"),
                    tax_percentage=Decimal("21.00"),
                    total=Decimal("29.04"),
                ),
                DeliveryNoteLine(
                    albaran_id=note.id,
                    product_id=producto.id,
                    description="Quitamanchas",
                    quantity=Decimal("1"),
                    unit_price=Decimal("5.00"),
                    tax_percentage=Decimal("21.00"),
                    total=Decimal("6.05"),
                ),
            ]
        )
        await db.commit()

        # La entrega NO revienta pese al servicio con stock 0.
        await update_albaran_status(note.id, tenant.id, "delivered", db, user_id=user.id)
        await db.refresh(servicio)
        await db.refresh(producto)
        assert float(servicio.stock_quantity) == 0.0  # intacto
        assert float(producto.stock_quantity) == 9.0  # 10 - 1

        # Anular restaura SOLO el producto físico.
        await update_albaran_status(note.id, tenant.id, "anulado", db, user_id=user.id)
        await db.refresh(servicio)
        await db.refresh(producto)
        assert float(servicio.stock_quantity) == 0.0
        assert float(producto.stock_quantity) == 10.0

    async def test_estado_invalido_rechazado(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        note, _ = await _seed_albaran(db, tenant.id)
        with pytest.raises(ValueError):
            await update_albaran_status(note.id, tenant.id, "planchado", db, user_id=user.id)


class TestTicketResguardo:
    def _note(self):
        return SimpleNamespace(
            id="x",
            albaran_number="ALB-2026-0042",
            date=datetime(2026, 7, 22),
            status="recibido",
            notes="Mancha de vino en solapa",
            amount_total=Decimal("24.20"),
        )

    def test_render_contenido_basico(self):
        html = render_albaran_ticket_html(
            emisor={"name": "Tintorería Pascual SL", "nif": "B12345678", "address": None, "phone": "911222333"},
            note=self._note(),
            lines=[SimpleNamespace(quantity=Decimal("2"), description="Limpieza traje", total=Decimal("24.20"))],
            cliente={"name": "Ana Pérez", "phone": "600111222"},
        )
        assert "RESGUARDO DE DEPÓSITO" in html
        assert "ALB-2026-0042" in html
        assert "Tintorería Pascual SL" in html
        assert "Ana Pérez" in html
        assert "Limpieza traje" in html
        assert "24,20 €" in html
        assert "Mancha de vino" in html
        assert "Recibido" in html
        assert "data:image/svg+xml;base64," in html  # QR del número
        assert "Conserve este resguardo" in html

    def test_render_escapa_html(self):
        html = render_albaran_ticket_html(
            emisor={"name": "A <script>", "nif": None, "address": None, "phone": None},
            note=self._note(),
            lines=[SimpleNamespace(quantity=1, description="<b>x</b>", total=1)],
            cliente=None,
        )
        assert "<script>" not in html
        assert "&lt;b&gt;x&lt;/b&gt;" in html
