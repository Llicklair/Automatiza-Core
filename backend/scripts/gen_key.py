from cryptography.fernet import Fernet
import secrets

print("=== Claves generadas para .env ===")
print(f"SECRET_KEY={secrets.token_hex(32)}")
print(f"TENANT_ENCRYPTION_KEY={Fernet.generate_key().decode()}")
