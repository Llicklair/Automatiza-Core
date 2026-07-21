"""Registro de eventos del SIF (cadena encadenada por huella)."""

import pytest

from app.services.billing.sif_events import (
    EVENT_ARRANQUE,
    EVENT_RESUMEN,
    record_event,
    verify_events_integrity,
)


@pytest.mark.asyncio
class TestSifEvents:
    async def test_primer_evento_sin_huella_anterior(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        ev = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_ARRANQUE)
        await db.commit()

        assert ev.huella_anterior is None
        assert len(ev.huella) == 64
        assert "TipoEvento=ARRANQUE" in ev.payload_canonico

    async def test_segundo_evento_encadena_al_primero(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        e1 = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_ARRANQUE)
        await db.flush()
        e2 = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_RESUMEN, detalle="resumen 6h")
        await db.commit()

        assert e2.huella_anterior == e1.huella
        assert e2.huella != e1.huella

    async def test_tipo_evento_invalido_lanza(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        with pytest.raises(ValueError, match="inválido"):
            await record_event(db, tenant_id=tenant.id, tipo_evento="NOPE")

    async def test_integridad_detecta_manipulacion(self, db, seed_tenant_and_user):
        tenant, _u, _t = seed_tenant_and_user
        await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_ARRANQUE)
        await db.flush()
        ev = await record_event(db, tenant_id=tenant.id, tipo_evento=EVENT_RESUMEN)
        await db.flush()

        ok, count = await verify_events_integrity(db, tenant.id)
        assert ok is True
        assert count == 2

        ev.huella = "0" * 64  # manipulación
        await db.flush()
        ok2, _ = await verify_events_integrity(db, tenant.id)
        assert ok2 is False

    async def test_cadenas_independientes_por_tenant(self, db, seed_tenant_and_user, seed_second_tenant_and_user):
        t1, _u1, _tok1 = seed_tenant_and_user
        t2, _u2, _tok2 = seed_second_tenant_and_user
        e1 = await record_event(db, tenant_id=t1.id, tipo_evento=EVENT_ARRANQUE)
        e2 = await record_event(db, tenant_id=t2.id, tipo_evento=EVENT_ARRANQUE)
        await db.commit()

        # Cada tenant es el primer evento de su propia cadena.
        assert e1.huella_anterior is None
        assert e2.huella_anterior is None

    async def test_cambiar_modo_verifactu_registra_evento(self, db, seed_tenant_and_user):
        from sqlalchemy import select

        from app.db.models.billing import SifEvent
        from app.services.billing.sif_events import EVENT_CAMBIO_MODO
        from app.services.billing.verifactu_mode import set_mode

        tenant, _u, _t = seed_tenant_and_user
        await set_mode(db, tenant_id=tenant.id, mode="voluntary")
        await db.commit()

        res = await db.execute(
            select(SifEvent).where(
                SifEvent.tenant_id == tenant.id,
                SifEvent.tipo_evento == EVENT_CAMBIO_MODO,
            )
        )
        events = res.scalars().all()
        assert len(events) == 1
        assert "voluntary" in (events[0].detalle or "")
