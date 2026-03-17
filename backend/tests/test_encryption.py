"""Tests para app.services.encryption."""
import pytest

from app.services.encryption import decrypt_credentials, encrypt_credentials


class TestEncryption:
    def test_encrypt_and_decrypt_roundtrip(self):
        original = {"access_token": "abc123", "refresh_token": "xyz789"}
        encrypted = encrypt_credentials(original)
        assert encrypted != str(original)
        decrypted = decrypt_credentials(encrypted)
        assert decrypted == original

    def test_encrypted_string_is_not_plaintext(self):
        creds = {"api_key": "sk-secret-key-123"}
        encrypted = encrypt_credentials(creds)
        assert "sk-secret-key-123" not in encrypted

    def test_different_encryptions_differ(self):
        """Fernet incluye timestamp → mismos datos generan tokens distintos."""
        creds = {"key": "value"}
        e1 = encrypt_credentials(creds)
        e2 = encrypt_credentials(creds)
        assert e1 != e2

    def test_empty_dict(self):
        encrypted = encrypt_credentials({})
        assert decrypt_credentials(encrypted) == {}

    def test_complex_nested_data(self):
        creds = {
            "tokens": {"access": "a", "refresh": "r"},
            "scopes": ["read", "write"],
            "expires_in": 3600,
        }
        encrypted = encrypt_credentials(creds)
        assert decrypt_credentials(encrypted) == creds

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            decrypt_credentials("esto_no_es_un_token_fernet_valido")

    def test_unicode_values(self):
        creds = {"nombre": "José García", "ciudad": "Logroño"}
        encrypted = encrypt_credentials(creds)
        assert decrypt_credentials(encrypted) == creds
