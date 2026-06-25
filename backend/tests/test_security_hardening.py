"""Regresión de la tanda de seguridad (auditoría 2026-06-25): SEC1 / X1 / SEC2.

- SEC1: el webhook de Telegram es fail-CLOSED — sin TELEGRAM_WEBHOOK_SECRET se
  rechaza (antes devolvía True → endpoint sin auth).
- X1: el email de reset, en producción y sin SMTP, NO finge el envío ni filtra el
  token de reset en los logs; en desarrollo sí muestra el enlace para probar.
- SEC2: el callback de AutoFirma rechaza una sesión de firma caducada.
"""

import base64
import logging
from datetime import datetime, timedelta

import pytest
import sqlalchemy as sa

from app.db.models.signed_document import SignedDocument
from app.services.auth import email_reset
from app.services.integration import messaging
from app.services.signing.autofirma import AutoFirmaError, SignatureFormat, file_sha256
from app.services.signing.sessions import process_signed_callback, start_signing_session

# ─── SEC1: webhook de Telegram fail-closed ────────────────────────────────────


def test_verify_webhook_secret_fail_closed_sin_secreto(monkeypatch):
    monkeypatch.setattr(messaging.settings, "TELEGRAM_WEBHOOK_SECRET", "", raising=False)
    assert messaging.verify_webhook_secret("lo-que-sea") is False
    assert messaging.verify_webhook_secret(None) is False


def test_verify_webhook_secret_ok_con_secreto(monkeypatch):
    monkeypatch.setattr(messaging.settings, "TELEGRAM_WEBHOOK_SECRET", "s3cr3t", raising=False)
    assert messaging.verify_webhook_secret("s3cr3t") is True
    assert messaging.verify_webhook_secret("incorrecto") is False
    assert messaging.verify_webhook_secret(None) is False


# ─── X1: email de reset sin SMTP ──────────────────────────────────────────────


def test_reset_email_produccion_sin_smtp_no_filtra_token_ni_finge(monkeypatch, caplog):
    monkeypatch.setattr(email_reset.settings, "SMTP_HOST", "", raising=False)
    monkeypatch.setattr(email_reset.settings, "SMTP_USER", "", raising=False)
    monkeypatch.setattr(email_reset.settings, "ENVIRONMENT", "production", raising=False)

    url = "https://app.example/reset-password?token=SECRETO_NO_LOGUEAR"
    with caplog.at_level(logging.INFO):
        ok = email_reset.send_password_reset_email("u@x.com", url)

    assert ok is False  # no finge el envío
    assert "SECRETO_NO_LOGUEAR" not in caplog.text  # el token NO se filtra en logs


def test_reset_email_dev_sin_smtp_muestra_enlace(monkeypatch, caplog):
    monkeypatch.setattr(email_reset.settings, "SMTP_HOST", "", raising=False)
    monkeypatch.setattr(email_reset.settings, "SMTP_USER", "", raising=False)
    monkeypatch.setattr(email_reset.settings, "ENVIRONMENT", "development", raising=False)

    url = "https://app.example/reset-password?token=DEVTOKEN"
    with caplog.at_level(logging.INFO):
        ok = email_reset.send_password_reset_email("u@x.com", url)

    assert ok is True
    assert "DEVTOKEN" in caplog.text  # en dev sí se muestra para poder probar el flujo


# ─── SEC2: caducidad de la sesión de firma ────────────────────────────────────


async def _start(db, tenant_id) -> str:
    res = await start_signing_session(
        db, tenant_id, document_bytes=b"%PDF-1.7 doc", document_id=None,
        signature_format=SignatureFormat.PADES,
        storage_servlet_url="http://x/storage", retriever_servlet_url="http://x/retrieve",
    )
    return res["session_token"]


@pytest.mark.asyncio
async def test_callback_rechaza_sesion_caducada(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    token = await _start(db, tenant.id)

    # Envejecer la sesión más allá del TTL (1 h).
    sd = (
        await db.execute(sa.select(SignedDocument).where(SignedDocument.session_token == token))
    ).scalar_one()
    sd.created_at = datetime.utcnow() - timedelta(hours=2)
    await db.commit()

    signed_pdf = b"%PDF-1.7 ... /Type /Sig ... signed"
    payload = {"id": token, "data": base64.urlsafe_b64encode(signed_pdf).decode("ascii")}
    with pytest.raises(AutoFirmaError, match="caducad"):  # "ha caducado"
        await process_signed_callback(db, token, payload)

    await db.refresh(sd)
    assert sd.status == "failed"  # la sesión caducada queda marcada como fallida


@pytest.mark.asyncio
async def test_callback_sesion_reciente_no_caduca(db, seed_tenant_and_user):
    """Una sesión recién creada NO debe rechazarse por caducidad (no regresión)."""
    tenant, _u, _t = seed_tenant_and_user
    token = await _start(db, tenant.id)

    signed_pdf = b"%PDF-1.7 ... /Type /Sig ... signed"
    payload = {"id": token, "data": base64.urlsafe_b64encode(signed_pdf).decode("ascii")}
    result = await process_signed_callback(db, token, payload)
    assert result["status"] == "signed"
    assert result["signed_hash"] == file_sha256(signed_pdf)
