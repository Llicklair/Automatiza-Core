from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SECRET = "CAMBIA_ESTO_EN_PRODUCCION_usa_openssl_rand_hex_32"
_DEFAULT_ENCRYPTION = "CAMBIA_ESTO_EN_PRODUCCION_usa_fernet_generate_key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Aplicación
    APP_NAME: str = "AutomatizaciónPyme"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = _DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PORT: int = 8080
    FRONTEND_URL: str = "http://localhost:3000"  # Acepta múltiples orígenes separados por coma

    @model_validator(mode="after")
    def check_secrets(self):
        if self.SECRET_KEY == _DEFAULT_SECRET:
            raise ValueError(
                "SECRET_KEY no puede ser el valor por defecto. "
                "Genera una clave segura con: openssl rand -hex 32"
            )
        if self.TENANT_ENCRYPTION_KEY == _DEFAULT_ENCRYPTION:
            raise ValueError(
                "TENANT_ENCRYPTION_KEY no puede ser el valor por defecto. "
                'Genera una clave con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        return self

    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://pyme_user:pyme_pass@localhost:5433/pyme_db"

    # LLM
    DEFAULT_LLM_PROVIDER: str = (
        "claude_code"  # claude_code | anthropic | openai | groq | openrouter
    )
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"  # claude-sonnet-4-6 | claude-opus-4-6
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-opus-4-6"

    # SMTP (recuperación de contraseña)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_TLS: bool = True

    # Embeddings
    EMBEDDINGS_PROVIDER: str = "local"  # local | openai
    EMBEDDINGS_LOCAL_MODEL: str = "BAAI/bge-m3"  # modelo HuggingFace local

    # OAuth — Google (Gmail + Drive)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8080/api/v1/integrations/google/callback"

    # OAuth — Microsoft (Outlook + OneDrive)
    MICROSOFT_CLIENT_ID: str = ""
    MICROSOFT_CLIENT_SECRET: str = ""
    MICROSOFT_REDIRECT_URI: str = "http://localhost:8080/api/v1/integrations/microsoft/callback"

    # Cifrado de credenciales de tenants
    TENANT_ENCRYPTION_KEY: str = "CAMBIA_ESTO_EN_PRODUCCION_usa_fernet_generate_key"

    # Scanner / Gatekeeper
    SCANNER_TOKEN_EXPIRE_MINUTES: int = 2  # QR tokens de corta vida
    SCANNER_ALLOWED_SCOPES: str = "inventory:read,inventory:write,albaranes:read,albaranes:write"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""  # e.g. https://tudominio.com/api/v1/messaging/telegram/webhook

    # Cola de tareas (opcional — activa Celery cuando está configurado)
    REDIS_URL: str | None = None  # redis://localhost:6379/0

    # Entorno
    ENVIRONMENT: str = "development"  # development | staging | production


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
