"""Tests para importadores MIG.1 (CSV) + MIG.2 (Holded) + MIG.3 (wizard)."""
from datetime import UTC
from decimal import Decimal

import pytest
from app.services.migration.csv_importer import (
    _detect_separator,
    _parse_decimal,
    parse_csv,
)
from app.services.migration.holded_importer import (
    normalize_holded_contact,
    normalize_holded_invoice,
)
from app.services.migration.wizard import import_clients

# ── MIG.1 — CSV importer ────────────────────────────────────────────────────


class TestCsvImporter:
    def test_detect_separator_coma(self):
        assert _detect_separator("a,b,c\n1,2,3") == ","

    def test_detect_separator_punto_coma(self):
        assert _detect_separator("a;b;c\n1;2;3") == ";"

    def test_parse_decimal_formato_es(self):
        # "1.234,56" → 1234.56 (formato europeo)
        assert _parse_decimal("1.234,56") == Decimal("1234.56")

    def test_parse_decimal_formato_us(self):
        assert _parse_decimal("1234.56") == Decimal("1234.56")

    def test_parse_decimal_solo_coma(self):
        assert _parse_decimal("100,50") == Decimal("100.50")

    def test_parse_decimal_invalido(self):
        assert _parse_decimal("not a number") is None

    def test_parse_decimal_vacio(self):
        assert _parse_decimal("") is None

    def test_parse_csv_clientes_basico(self):
        blob = b"nif,name,email\nB12345678,Acme SL,info@acme.es\nB87654321,Beta SL,info@beta.es\n"
        preview = parse_csv(blob, kind="clients")
        assert preview.detected_separator == ","
        assert preview.total_rows == 2
        assert preview.errors_count == 0
        assert preview.header_mapping["nif"] == "nif"
        assert preview.header_mapping["name"] == "name"
        assert preview.rows_sample[0].canonical["nif"] == "B12345678"

    def test_parse_csv_facturas_separador_punto_coma_formato_es(self):
        blob = (
            b"Numero;Fecha;NIF Cliente;Total\n"
            b"A2026-0001;2026-05-14;B12345678;1.210,00\n"
            b"A2026-0002;2026-05-15;B87654321;605,00\n"
        )
        preview = parse_csv(blob, kind="invoices")
        assert preview.detected_separator == ";"
        assert preview.total_rows == 2
        assert preview.errors_count == 0
        assert preview.rows_sample[0].canonical["amount_total"] == Decimal("1210.00")

    def test_parse_csv_bom_utf8(self):
        blob = b"\xef\xbb\xbfnif,name\nB12345678,Acme SL\n"
        preview = parse_csv(blob, kind="clients")
        assert preview.detected_encoding == "utf-8-sig"
        assert preview.rows_sample[0].canonical["nif"] == "B12345678"

    def test_parse_csv_fila_vacia_marca_error(self):
        blob = b"nif,name\n,\nB12345678,Acme SL\n"
        preview = parse_csv(blob, kind="clients")
        assert preview.total_rows == 2
        assert preview.errors_count == 1

    def test_parse_csv_max_rows_limita_sample_no_total(self):
        rows = "nif,name\n" + "\n".join(f"B1234567{i:01d},Cliente {i}" for i in range(50))
        preview = parse_csv(rows.encode("utf-8"), kind="clients", max_rows=10)
        assert preview.total_rows == 50
        assert len(preview.rows_sample) == 10


# ── MIG.2 — Holded normalizers ──────────────────────────────────────────────


class TestHoldedNormalizers:
    def test_normalize_contact_basico(self):
        contact = {
            "name": "Acme SL",
            "code": "B12345678",
            "email": "info@acme.es",
            "phone": "+34 91 1234567",
            "address": "Gran Via 1",
            "city": "Madrid",
            "postalCode": "28013",
            "country": "Spain",
        }
        row = normalize_holded_contact(contact)
        assert row.canonical["nif"] == "B12345678"
        assert row.canonical["name"] == "Acme SL"
        assert "Madrid" in row.canonical["address"]
        assert row.errors == []

    def test_normalize_contact_sin_nif_marca_error_si_tampoco_nombre(self):
        contact = {"email": "x@y.com"}
        row = normalize_holded_contact(contact)
        assert row.errors
        assert "sin NIF ni nombre" in row.errors[0]

    def test_normalize_invoice_centimos_a_euros(self):
        from datetime import datetime
        ts = int(datetime(2026, 5, 14, tzinfo=UTC).timestamp())
        doc = {
            "docNumber": "A2026-0001",
            "date": ts,
            "contactCode": "B12345678",
            "contactName": "Acme SL",
            "subtotal": 100000,  # 1000€ en céntimos
            "tax": 21000,
            "total": 121000,
        }
        row = normalize_holded_invoice(doc)
        assert row.canonical["amount_base"] == Decimal("1000")
        assert row.canonical["tax_amount"] == Decimal("210")
        assert row.canonical["amount_total"] == Decimal("1210")
        assert row.canonical["date"] == "2026-05-14"
        assert row.errors == []

    def test_normalize_invoice_sin_docnumber_marca_error(self):
        row = normalize_holded_invoice({})
        assert row.errors


# ── MIG.3 — Wizard / import persistence ─────────────────────────────────────


@pytest.mark.asyncio
class TestImportClients:
    async def test_insert_clientes_nuevos(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        blob = b"nif,name,email\nB99990001,Cliente Nuevo 1,x@y.es\nB99990002,Cliente Nuevo 2,a@b.es\n"
        preview = parse_csv(blob, kind="clients")
        result = await import_clients(db, tenant.id, preview.rows_sample)
        await db.commit()
        assert result.inserted == 2
        assert result.updated == 0
        assert result.failed == 0

    async def test_upsert_actualiza_existente(self, db, seed_tenant_and_user):
        from app.db.models.crm import Client
        tenant, _, _ = seed_tenant_and_user
        existing = Client(tenant_id=tenant.id, nif="B99990001", name="Antiguo Nombre")
        db.add(existing)
        await db.flush()

        blob = b"nif,name\nB99990001,Nuevo Nombre\n"
        preview = parse_csv(blob, kind="clients")
        result = await import_clients(db, tenant.id, preview.rows_sample)
        await db.commit()
        assert result.inserted == 0
        assert result.updated == 1
        # Verificar que el nombre cambió
        await db.refresh(existing)
        assert existing.name == "Nuevo Nombre"

    async def test_filas_con_errores_se_skipean(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        blob = b"nif,name\n,\nB99990003,Cliente OK\n"
        preview = parse_csv(blob, kind="clients")
        result = await import_clients(db, tenant.id, preview.rows_sample)
        await db.commit()
        assert result.inserted == 1
        assert result.skipped == 1
