"""Tests para `track_event` (OPS.MET)."""
from uuid import uuid4

import pytest
from app.services.analytics import CANONICAL_EVENTS, track_event


@pytest.mark.asyncio
class TestTrackEvent:
    async def test_evento_canonico_devuelve_true(self):
        ok = await track_event(
            event="user.signup",
            tenant_id=uuid4(),
            properties={"source": "landing"},
        )
        assert ok is True

    async def test_evento_no_canonico_devuelve_false(self, caplog):
        import logging
        caplog.set_level(logging.WARNING)
        ok = await track_event(
            event="user.click_button_xyz",  # no canónico
            tenant_id=uuid4(),
        )
        assert ok is False
        # Debe haber log de warning
        assert any("no canónico" in record.message for record in caplog.records)

    async def test_properties_pii_se_scrubean(self, caplog):
        import logging
        caplog.set_level(logging.INFO, logger="analytics.events")
        await track_event(
            event="invoice.created",
            tenant_id=uuid4(),
            properties={
                "error_message": "Cliente B12345678 con IBAN ES9121000418450200051332 falló",
            },
        )
        # El mensaje logueado no debe contener NIF/IBAN en plano
        for record in caplog.records:
            if "event=invoice.created" in record.getMessage():
                assert "B12345678" not in record.getMessage()
                assert "ES9121" not in record.getMessage()

    async def test_distinct_id_es_hash_no_uuid_plano(self, caplog):
        import logging
        caplog.set_level(logging.INFO, logger="analytics.events")
        tid = uuid4()
        await track_event(event="user.signup", tenant_id=tid)
        for record in caplog.records:
            if "distinct_id" in record.getMessage():
                assert str(tid) not in record.getMessage()

    async def test_excepcion_interna_no_propaga(self, monkeypatch):
        # Forzamos un fallo en el scrubber para verificar que track_event
        # devuelve False en lugar de propagar.

        def _broken_scrub(*args, **kwargs):
            raise RuntimeError("boom")

        # No tocamos el import original; parchamos directamente la función
        # accesible desde el módulo.
        import app.core.telemetry_scrubber as ts
        monkeypatch.setattr(ts, "scrub_event", _broken_scrub)

        ok = await track_event(event="user.signup", tenant_id=uuid4())
        assert ok is False

    async def test_lista_canonica_incluye_hitos_funnel(self):
        for required in (
            "user.signup",
            "invoice.first_created",
            "model_aeat.first_presented",
            "subscription.cancelled",
            "fiscal_approval.approved",
        ):
            assert required in CANONICAL_EVENTS
