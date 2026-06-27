"""Regression: los except Exception de advisory/backup_local NO deben filtrar
internals (str(e)) al cliente. Status 500 genérico, sin el marcador secreto.
"""
from unittest.mock import patch

import pytest

LEAK = "LEAK_MARKER_SECRET_77"


@pytest.mark.asyncio
async def test_boe_does_not_leak_exception_detail(auth_client):
    with patch(
        "app.api.v1.routes.advisory.BOEScraper.get_novedades",
        side_effect=Exception(LEAK),
    ):
        resp = await auth_client.get("/api/v1/advisory/boe", params={"section": "fiscal"})

    assert resp.status_code == 500
    assert LEAK not in resp.text
    assert LEAK not in (resp.json().get("detail") or "")


@pytest.mark.asyncio
async def test_calendar_does_not_leak_exception_detail(auth_client):
    with patch(
        "app.api.v1.routes.advisory.get_proximos_vencimientos",
        side_effect=Exception(LEAK),
    ):
        resp = await auth_client.get("/api/v1/advisory/calendar", params={"days_ahead": 30})

    assert resp.status_code == 500
    assert LEAK not in resp.text
    assert LEAK not in (resp.json().get("detail") or "")


@pytest.mark.asyncio
async def test_record_backup_does_not_leak_exception_detail(auth_client):
    body = {
        "kind": "full",
        "destination_path": "/tmp/backup.bak",
        "size_bytes": 1024,
        "sha256_hex": "a" * 64,
        "encryption_key_label": "key-1",
        "note": None,
    }
    with patch(
        "app.api.v1.routes.backup_local.record_backup",
        side_effect=Exception(LEAK),
    ):
        resp = await auth_client.post("/api/v1/backup-local/record", json=body)

    assert resp.status_code == 500
    assert LEAK not in resp.text
    assert LEAK not in (resp.json().get("detail") or "")
