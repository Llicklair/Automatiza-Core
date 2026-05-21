"""Tests de la firma electrónica AutoFirma (F3.11)."""
import base64
import json

import pytest

from app.services.signing.autofirma import (
    AutoFirmaError,
    SignatureFormat,
    build_autofirma_uri,
    extract_signature_metadata,
    file_sha256,
    parse_autofirma_response,
)
from app.services.signing.sessions import (
    process_signed_callback,
    start_signing_session,
)


# ─── build_autofirma_uri (puro) ────────────────────────────────────────


def test_build_uri_devuelve_uri_y_hash():
    doc = b"%PDF-1.7 ... fake pdf"
    uri, doc_hash = build_autofirma_uri(
        doc,
        signature_format=SignatureFormat.PADES,
        storage_servlet_url="http://x/storage",
        retriever_servlet_url="http://x/retrieve",
        session_token="x" * 16,
    )
    assert uri.startswith("afirma://sign?ver=1_5")
    assert "id=" + "x" * 16 in uri
    assert "j=true" in uri
    assert "dat=" in uri
    assert doc_hash == file_sha256(doc)


def test_build_uri_rechaza_documento_vacio():
    with pytest.raises(AutoFirmaError):
        build_autofirma_uri(
            b"",
            signature_format=SignatureFormat.PADES,
            storage_servlet_url="x",
            retriever_servlet_url="y",
            session_token="x" * 16,
        )


def test_build_uri_rechaza_token_corto():
    with pytest.raises(AutoFirmaError):
        build_autofirma_uri(
            b"data",
            signature_format=SignatureFormat.PADES,
            storage_servlet_url="x",
            retriever_servlet_url="y",
            session_token="abc",
        )


def test_build_uri_rechaza_algoritmo_no_soportado():
    with pytest.raises(AutoFirmaError):
        build_autofirma_uri(
            b"data",
            signature_format=SignatureFormat.PADES,
            storage_servlet_url="x",
            retriever_servlet_url="y",
            session_token="x" * 16,
            algorithm="MD5withRSA",
        )


def test_build_uri_pades_marca_visibilidad_firma():
    uri_vis, _ = build_autofirma_uri(
        b"data",
        signature_format=SignatureFormat.PADES,
        storage_servlet_url="x",
        retriever_servlet_url="y",
        session_token="x" * 16,
        visible_signature=True,
    )
    # dat es base64 de un JSON con extraParams
    dat = uri_vis.split("dat=")[1]
    config = json.loads(
        base64.urlsafe_b64decode(dat + "=" * (-len(dat) % 4)).decode("utf-8")
    )
    assert config["format"] == "pades"
    assert config["extraParams"] == "signatureVisible=true"


# ─── parse_autofirma_response (puro) ──────────────────────────────────


def test_parse_response_json_valido():
    signed = b"binario firmado"
    payload = {
        "id": "tok123",
        "data": base64.urlsafe_b64encode(signed).decode("ascii"),
    }
    result = parse_autofirma_response(payload)
    assert result["session_token"] == "tok123"
    assert result["signed_bytes"] == signed


def test_parse_response_json_con_error_levanta():
    with pytest.raises(AutoFirmaError):
        parse_autofirma_response({"errorType": "java.security.cert.CertificateException"})


def test_parse_response_string_base64():
    signed = b"firmado raw"
    payload = base64.urlsafe_b64encode(signed).decode("ascii")
    result = parse_autofirma_response(payload)
    assert result["signed_bytes"] == signed
    assert result["session_token"] is None


def test_parse_response_bytes_directos():
    signed = b"%PDF-1.7\n... firmado"
    result = parse_autofirma_response(signed)
    assert result["signed_bytes"] == signed


def test_parse_response_tipo_no_soportado():
    with pytest.raises(AutoFirmaError):
        parse_autofirma_response(12345)  # type: ignore


# ─── extract_signature_metadata (puro) ────────────────────────────────


def test_extract_pades_detecta_firma():
    pdf_with_sig = b"%PDF-1.7\n... /Type /Sig ..."
    meta = extract_signature_metadata(pdf_with_sig, SignatureFormat.PADES)
    assert meta["has_signature"] is True


def test_extract_pades_sin_firma():
    pdf_plain = b"%PDF-1.7\n... contenido plain ..."
    meta = extract_signature_metadata(pdf_plain, SignatureFormat.PADES)
    assert meta["has_signature"] is False


def test_extract_xades_detecta_firma():
    xml = b'<?xml version="1.0"?><root><ds:Signature xmlns:ds="..."></ds:Signature></root>'
    meta = extract_signature_metadata(xml, SignatureFormat.XADES)
    assert meta["has_signature"] is True


# ─── Sesiones con DB ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_signing_session_persiste(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    result = await start_signing_session(
        db,
        tenant.id,
        document_bytes=b"%PDF-1.7 test",
        document_id=None,
        signature_format=SignatureFormat.PADES,
        storage_servlet_url="http://x/storage",
        retriever_servlet_url="http://x/retrieve",
    )
    assert result["autofirma_uri"].startswith("afirma://")
    assert len(result["session_token"]) >= 16
    assert result["signature_format"] == "PAdES"


@pytest.mark.asyncio
async def test_callback_marca_signed_si_hay_firma(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    start = await start_signing_session(
        db,
        tenant.id,
        document_bytes=b"%PDF-1.7 original",
        document_id=None,
        signature_format=SignatureFormat.PADES,
        storage_servlet_url="http://x/storage",
        retriever_servlet_url="http://x/retrieve",
    )
    token = start["session_token"]

    signed_pdf = b"%PDF-1.7 ... /Type /Sig ... signed"
    payload = {
        "id": token,
        "data": base64.urlsafe_b64encode(signed_pdf).decode("ascii"),
    }
    result = await process_signed_callback(db, token, payload)
    assert result["status"] == "signed"
    assert result["signed_hash"] == file_sha256(signed_pdf)


@pytest.mark.asyncio
async def test_callback_marca_failed_si_no_hay_firma(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    start = await start_signing_session(
        db,
        tenant.id,
        document_bytes=b"original",
        document_id=None,
        signature_format=SignatureFormat.PADES,
        storage_servlet_url="http://x/storage",
        retriever_servlet_url="http://x/retrieve",
    )
    token = start["session_token"]

    not_signed = b"%PDF-1.7 ... contenido sin firma"
    payload = {
        "id": token,
        "data": base64.urlsafe_b64encode(not_signed).decode("ascii"),
    }
    result = await process_signed_callback(db, token, payload)
    assert result["status"] == "failed"


@pytest.mark.asyncio
async def test_callback_token_inexistente(db, seed_tenant_and_user):
    with pytest.raises(AutoFirmaError):
        await process_signed_callback(
            db,
            "no_existe_token",
            {"id": "no_existe_token", "data": base64.urlsafe_b64encode(b"x").decode("ascii")},
        )
