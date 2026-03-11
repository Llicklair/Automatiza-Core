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
    FRONTEND_URL: str = "http://localhost:3000"

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
                "Genera una clave con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        return self

    # Base de datos
    DATABASE_URL: str = "postgresql+asyncpg://pyme_user:pyme_pass@localhost:5432/pyme_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # LLM
    DEFAULT_LLM_PROVIDER: str = "ollama"  # ollama | gemini | openai | anthropic | groq | openrouter
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-preview-04-17"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "anthropic/claude-3.5-sonnet"
    OLLAMA_BASE_URL: str = "http://ollama:11434"

    # Cifrado de credenciales de tenants
    TENANT_ENCRYPTION_KEY: str = "CAMBIA_ESTO_EN_PRODUCCION_usa_fernet_generate_key"

    # Entorno
    ENVIRONMENT: str = "development"  # development | staging | production


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
