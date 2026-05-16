"""Tests para cifrado E2E y retención de backup B2 (BAK.B2)."""
from datetime import UTC, datetime, timedelta

import pytest
from app.services.backup import (
    BackupCandidate,
    apply_rolling_retention,
    decrypt_e2e,
    derive_key_from_password,
    encrypt_e2e,
    new_salt,
)


class TestCrypto:
    def test_round_trip_basico(self):
        data = b"contenido confidencial"
        blob = encrypt_e2e(data, "MiPasswordSeguro123!")
        result = decrypt_e2e(blob, "MiPasswordSeguro123!")
        assert result == data

    def test_password_incorrecto_falla(self):
        blob = encrypt_e2e(b"x", "correcto")
        with pytest.raises(ValueError, match="incorrecto|corrupto"):
            decrypt_e2e(blob, "wrong")

    def test_blob_corrupto_falla(self):
        blob = encrypt_e2e(b"x", "p")
        tampered = bytearray(blob)
        tampered[-5] ^= 0xFF  # corrompe último bloque
        with pytest.raises(ValueError):
            decrypt_e2e(bytes(tampered), "p")

    def test_dos_cifrados_mismo_input_distinto_blob(self):
        # Salt + nonce aleatorios → mismo input produce blobs distintos
        a = encrypt_e2e(b"data", "p")
        b = encrypt_e2e(b"data", "p")
        assert a != b
        # Pero ambos descifran a lo mismo
        assert decrypt_e2e(a, "p") == decrypt_e2e(b, "p") == b"data"

    def test_blob_demasiado_corto(self):
        with pytest.raises(ValueError, match="tama"):
            decrypt_e2e(b"short", "p")

    def test_derive_key_determinista_misma_sal(self):
        salt = new_salt()
        k1 = derive_key_from_password("p", salt)
        k2 = derive_key_from_password("p", salt)
        assert k1 == k2
        assert len(k1) == 32

    def test_derive_key_password_vacio_lanza(self):
        with pytest.raises(ValueError):
            derive_key_from_password("", new_salt())

    def test_derive_key_salt_invalido(self):
        with pytest.raises(ValueError):
            derive_key_from_password("p", b"corto")

    def test_blob_es_opaco(self):
        # El blob no debe contener el password ni el plaintext en plano
        blob = encrypt_e2e(b"NIF B12345678", "MiPassword")
        assert b"B12345678" not in blob
        assert b"MiPassword" not in blob


class TestRollingRetention:
    def test_vacio_devuelve_vacio(self):
        keep, purge = apply_rolling_retention([])
        assert keep == purge == []

    def test_backup_de_hoy_se_conserva(self):
        now = datetime(2026, 5, 14, 12, 0, tzinfo=UTC)
        c = BackupCandidate(key="a", created_at=now - timedelta(hours=1))
        keep, purge = apply_rolling_retention([c], now=now)
        assert keep == [c]
        assert purge == []

    def test_backup_de_hace_60_dias_es_purgado_si_no_es_mensual(self):
        # 60 días atrás está fuera de la ventana diaria 30d. Si no es el
        # primer backup de su mes, se purga.
        now = datetime(2026, 5, 14, tzinfo=UTC)
        c1 = BackupCandidate(key="a", created_at=now - timedelta(days=60, hours=2))
        c2 = BackupCandidate(key="b", created_at=now - timedelta(days=60))  # mismo día
        keep, purge = apply_rolling_retention([c1, c2], now=now)
        # c1 es el más antiguo del mes → se conserva como snapshot mensual
        # c2 es del mismo mes pero no el primero → se purga
        assert c1 in keep
        assert c2 in purge

    def test_snapshot_mensual_de_hace_5_meses(self):
        now = datetime(2026, 5, 14, tzinfo=UTC)
        # Backup de hace ~5 meses (diciembre 2025)
        old = BackupCandidate(key="dic", created_at=datetime(2025, 12, 5, tzinfo=UTC))
        keep, purge = apply_rolling_retention([old], now=now)
        assert old in keep  # dentro de la ventana de 12 meses

    def test_snapshot_de_hace_2_anos_se_purga(self):
        now = datetime(2026, 5, 14, tzinfo=UTC)
        very_old = BackupCandidate(
            key="2024", created_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        keep, purge = apply_rolling_retention([very_old], now=now)
        assert very_old in purge
        assert keep == []

    def test_combina_diario_y_mensual_sin_duplicar(self):
        now = datetime(2026, 5, 14, tzinfo=UTC)
        candidates = [
            BackupCandidate(key=f"d{i}", created_at=now - timedelta(days=i))
            for i in range(0, 35)  # 35 días, los 30 últimos son diarios
        ]
        # Añadimos un backup mensual viejo (hace 10 meses)
        ten_months_ago = datetime(2025, 7, 1, tzinfo=UTC)
        candidates.append(BackupCandidate(key="m10", created_at=ten_months_ago))

        keep, purge = apply_rolling_retention(candidates, now=now)
        keep_keys = {c.key for c in keep}

        # Los últimos 30 días deben estar
        for i in range(30):
            assert f"d{i}" in keep_keys
        # El backup mensual de hace 10 meses debe estar
        assert "m10" in keep_keys
        # No deben aparecer duplicados
        assert len(keep) == len(keep_keys)
