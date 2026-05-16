"""Tests para app.core.security — hashing, tokens JWT."""
from datetime import timedelta

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    mask_iban,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "MiContraseña_Segura!123"
        hashed = get_password_hash(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = get_password_hash("correcta")
        assert not verify_password("incorrecta", hashed)

    def test_different_hashes_for_same_password(self):
        """bcrypt genera salt aleatorio → hashes distintos."""
        h1 = get_password_hash("misma")
        h2 = get_password_hash("misma")
        assert h1 != h2

    def test_empty_password(self):
        hashed = get_password_hash("")
        assert verify_password("", hashed)
        assert not verify_password("algo", hashed)

    def test_unicode_password(self):
        password = "contraseña_con_ñ_y_€"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed)


class TestAccessToken:
    def test_create_and_decode(self):
        data = {"sub": "user-123", "tenant_id": "tenant-456", "role": "admin"}
        token = create_access_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-123"
        assert decoded["tenant_id"] == "tenant-456"
        assert decoded["role"] == "admin"
        assert decoded["type"] == "access"

    def test_custom_expiry(self):
        data = {"sub": "user-1"}
        token = create_access_token(data, expires_delta=timedelta(minutes=5))
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-1"

    def test_expired_token_returns_none(self):
        data = {"sub": "user-1"}
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        assert decode_token(token) is None

    def test_invalid_token_returns_none(self):
        assert decode_token("esto.no.es.un.token.valido") is None
        assert decode_token("") is None
        assert decode_token("abc123") is None


class TestRefreshToken:
    def test_create_and_decode(self):
        data = {"sub": "user-1", "tenant_id": "t-1", "role": "user"}
        token = create_refresh_token(data)
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["type"] == "refresh"
        assert decoded["sub"] == "user-1"

    def test_refresh_token_differs_from_access(self):
        data = {"sub": "user-1", "tenant_id": "t-1", "role": "admin"}
        access = create_access_token(data)
        refresh = create_refresh_token(data)
        assert access != refresh


class TestMaskIban:
    def test_iban_sin_espacios(self):
        result = mask_iban("ES9121000418450200051332")
        assert result == "ES** **** **** **** **** 1332"

    def test_iban_con_espacios(self):
        result = mask_iban("ES91 2100 0418 4502 0005 1332")
        assert result == "ES** **** **** **** **** 1332"

    def test_iban_dentro_de_texto(self):
        result = mask_iban("Transferencia a ES91 2100 0418 4502 0005 1332 recibida.")
        assert result == "Transferencia a ES** **** **** **** **** 1332 recibida."

    def test_iban_minusculas_normaliza_pais(self):
        result = mask_iban("es9121000418450200051332")
        assert result == "ES** **** **** **** **** 1332"

    def test_no_es_iban_no_toca(self):
        # Texto sin IBANs queda intacto
        assert mask_iban("Hola mundo, sin números aquí.") == "Hola mundo, sin números aquí."

    def test_string_corto_no_se_toca(self):
        # ES12 sin más no es IBAN, no debe enmascararse
        assert mask_iban("ES12") == "ES12"

    def test_idempotente_no_re_enmascara(self):
        masked_once = mask_iban("ES9121000418450200051332")
        masked_twice = mask_iban(masked_once)
        assert masked_once == masked_twice

    def test_iban_pais_diferente(self):
        # DE89 3704 0044 0532 0130 00 (22 chars de body para DE = 22+2+2 = no, DE es 22 total)
        # DE IBAN tiene 22 chars total: DE + 2 check + 18 body
        result = mask_iban("DE89370400440532013000")
        # 22 chars: middle_groups = (22-6)//4 = 4
        assert result == "DE** **** **** **** **** 3000"

    def test_input_none_devuelve_none(self):
        assert mask_iban(None) is None

    def test_input_vacio(self):
        assert mask_iban("") == ""

    def test_multiples_ibans_en_texto(self):
        text = "De ES9121000418450200051332 a ES7600810001234567890123 transfer."
        result = mask_iban(text)
        assert "ES** **** **** **** **** 1332" in result
        assert "ES** **** **** **** **** 0123" in result
