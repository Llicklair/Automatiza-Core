"""Tarjeta de fidelización del cliente (PDF)."""

import uuid

import pytest

from app.db.models.crm import Client
from app.services.crm.loyalty_card import generate_loyalty_card_pdf


@pytest.mark.asyncio
class TestLoyaltyCardPdf:
    async def test_genera_pdf_de_la_tarjeta(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, name="María López", nif="12345678Z")
        db.add(client)
        await db.commit()

        pdf = await generate_loyalty_card_pdf(db, tenant.id, client.id)

        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 1000  # incluye el QR → PDF no trivial

    async def test_cliente_inexistente_lanza_lookup(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(LookupError):
            await generate_loyalty_card_pdf(db, tenant.id, uuid.uuid4())

    async def test_cliente_de_otro_tenant_no_accesible(self, db, seed_tenant_and_user, seed_second_tenant_and_user):
        t1, _u1, _tok1 = seed_tenant_and_user
        t2, _u2, _tok2 = seed_second_tenant_and_user
        ajeno = Client(tenant_id=t2.id, name="Cliente Ajeno", nif=None)
        db.add(ajeno)
        await db.commit()

        with pytest.raises(LookupError):
            await generate_loyalty_card_pdf(db, t1.id, ajeno.id)
