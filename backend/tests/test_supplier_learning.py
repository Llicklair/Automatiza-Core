"""Tests del aprendizaje OCR por proveedor (F2.5)."""

import pytest

from app.db.models.supplier_learning import SupplierInvoiceTemplate
from app.services.ocr.supplier_learning import (
    apply_template_overrides,
    build_few_shot_block,
    diff_corrections,
    file_sha256,
    get_template,
    lookup_cached,
    record_extraction,
    save_correction,
    save_to_cache,
)


# ─── file_sha256 ────────────────────────────────────────────────────────


def test_file_sha256_estable():
    a = b"hello world"
    b = b"hello world"
    assert file_sha256(a) == file_sha256(b)
    assert len(file_sha256(a)) == 64


# ─── diff_corrections ───────────────────────────────────────────────────


def test_diff_corrections_detecta_tax_uniforme():
    original = {
        "lines": [
            {"description": "A", "tax_percentage": 10},
            {"description": "B", "tax_percentage": 10},
        ]
    }
    corrected = {
        "lines": [
            {"description": "A", "tax_percentage": 21},
            {"description": "B", "tax_percentage": 21},
        ]
    }
    d = diff_corrections(original, corrected)
    assert d["default_tax_percentage"] == 21.0


def test_diff_corrections_no_propone_tax_si_no_uniforme():
    original = {"lines": [{"description": "A", "tax_percentage": 10}, {"description": "B", "tax_percentage": 10}]}
    corrected = {"lines": [{"description": "A", "tax_percentage": 21}, {"description": "B", "tax_percentage": 4}]}
    d = diff_corrections(original, corrected)
    assert "default_tax_percentage" not in d


def test_diff_corrections_detecta_renombrados_descripcion():
    original = {"lines": [{"description": "CONSUMO KWH"}, {"description": "ALQUILER EQUIPO"}]}
    corrected = {"lines": [{"description": "Electricidad consumo"}, {"description": "ALQUILER EQUIPO"}]}
    d = diff_corrections(original, corrected)
    assert d["description_overrides"] == {"CONSUMO KWH": "Electricidad consumo"}


def test_diff_corrections_vacio_si_no_hay_cambios():
    payload = {"lines": [{"description": "A", "tax_percentage": 21}]}
    assert diff_corrections(payload, payload) == {}


# ─── apply_template_overrides ──────────────────────────────────────────


def test_apply_template_overrides_sin_template_no_modifica():
    payload = {"lines": [{"description": "X", "tax_percentage": 10}]}
    result = apply_template_overrides(payload, None)
    assert result == payload


def test_apply_template_overrides_aplica_default_tax_si_falta():
    template = SupplierInvoiceTemplate(
        tenant_id=None,
        supplier_nif="B12345678",
        default_tax_percentage=21,
    )
    payload = {"lines": [{"description": "X"}, {"description": "Y", "tax_percentage": 4}]}
    result = apply_template_overrides(payload, template)
    # Línea 0 sin tax → recibe el default
    assert result["lines"][0]["tax_percentage"] == 21.0
    # Línea 1 ya tenía 4 → respetada
    assert result["lines"][1]["tax_percentage"] == 4


def test_apply_template_overrides_renombra_descripcion():
    template = SupplierInvoiceTemplate(
        tenant_id=None,
        supplier_nif="B12345678",
        description_overrides={"consumo kwh": "Electricidad"},
    )
    payload = {"lines": [{"description": "CONSUMO KWH MES JUNIO", "tax_percentage": 21}]}
    result = apply_template_overrides(payload, template)
    assert result["lines"][0]["description"] == "Electricidad"


# ─── build_few_shot_block ──────────────────────────────────────────────


def test_build_few_shot_block_vacio_si_no_hay_template():
    assert build_few_shot_block(None) == ""


def test_build_few_shot_block_con_extraccion_previa():
    template = SupplierInvoiceTemplate(
        tenant_id=None,
        supplier_nif="B12345678",
        default_tax_percentage=21,
        last_extraction={
            "emisor": {"nif": "B12345678"},
            "invoice_number": "FAC-2026-0001",
            "lines": [{"description": "Servicio A", "tax_percentage": 21}],
        },
    )
    block = build_few_shot_block(template)
    assert "B12345678" in block
    assert "FAC-2026-0001" in block


# ─── Integración con DB (cache + record_extraction + save_correction) ──


@pytest.mark.asyncio
async def test_cache_roundtrip(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    payload = {"emisor": {"nif": "B12345678"}, "amount_total": 121.0, "lines": []}
    hashv = "a" * 64

    assert await lookup_cached(db, tenant.id, hashv) is None

    await save_to_cache(
        db, tenant.id, hashv, file_size=1234, mime_type="application/pdf",
        extracted_data=payload,
    )

    cached = await lookup_cached(db, tenant.id, hashv)
    assert cached is not None
    assert cached["emisor"]["nif"] == "B12345678"
    assert cached["_from_cache"] is True


@pytest.mark.asyncio
async def test_record_extraction_crea_template_y_actualiza_contador(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    payload = {
        "emisor": {"nif": "B11111111", "name": "Proveedor SA"},
        "amount_total": 100.0,
        "lines": [{"description": "A", "tax_percentage": 21}],
    }
    await record_extraction(db, tenant.id, payload)

    template = await get_template(db, tenant.id, "B11111111")
    assert template is not None
    assert template.extractions_count == 1
    assert template.supplier_name == "Proveedor SA"

    # Segunda extracción acumula
    payload2 = {**payload, "amount_total": 200.0}
    await record_extraction(db, tenant.id, payload2)

    template = await get_template(db, tenant.id, "B11111111")
    assert template.extractions_count == 2
    assert float(template.avg_amount_total) == 150.0  # (100+200)/2


@pytest.mark.asyncio
async def test_save_correction_persiste_overrides(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user

    original = {
        "emisor": {"nif": "B22222222", "name": "Iberdrola"},
        "lines": [{"description": "CONSUMO KWH", "tax_percentage": 10}],
    }
    corrected = {
        "emisor": {"nif": "B22222222", "name": "Iberdrola"},
        "lines": [{"description": "Electricidad consumo", "tax_percentage": 21}],
    }
    diff = await save_correction(db, tenant.id, "B22222222", original, corrected)
    assert diff["default_tax_percentage"] == 21.0
    assert diff["description_overrides"] == {"CONSUMO KWH": "Electricidad consumo"}

    template = await get_template(db, tenant.id, "B22222222")
    assert template is not None
    assert float(template.default_tax_percentage) == 21.0
    assert template.description_overrides == {"CONSUMO KWH": "Electricidad consumo"}


@pytest.mark.asyncio
async def test_save_correction_merge_no_overwrite_descriptions(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user

    await save_correction(
        db,
        tenant.id,
        "B33333333",
        original={"lines": [{"description": "A_OLD"}]},
        corrected={"lines": [{"description": "A_NEW"}]},
    )
    await save_correction(
        db,
        tenant.id,
        "B33333333",
        original={"lines": [{"description": "B_OLD"}]},
        corrected={"lines": [{"description": "B_NEW"}]},
    )
    template = await get_template(db, tenant.id, "B33333333")
    assert template.description_overrides == {"A_OLD": "A_NEW", "B_OLD": "B_NEW"}
