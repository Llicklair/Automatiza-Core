import logging
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger(__name__)

_DEFAULT_FRONTEND_URL = "http://localhost:3000"
_DEFAULT_SECRET = "CAMBIA_ESTO_EN_PRODUCCION_usa_openssl_rand_hex_32"
_DEFAULT_ENCRYPTION = "CAMBIA_ESTO_EN_PRODUCCION_usa_fernet_generate_key"

# Ruta absoluta al .env: backend/app/core/config.py → 3 niveles arriba = backend/ → 1 más = project/
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    # Aplicación
    APP_NAME: str = "AutomatizaciónPyme"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str = _DEFAULT_SECRET
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    PORT: int = 8080
    FRONTEND_URL: str = _DEFAULT_FRONTEND_URL  # Acepta múltiples orígenes separados por coma
    # URL pública del portal de clientes (la que verán los clientes finales al abrir el enlace).
    # Si está vacía, el frontend cae a window.location.origin con advertencia. En producción debe
    # apuntar a la URL accesible desde internet (Cloudflare Tunnel, dominio propio, IP fija…).
    PORTAL_PUBLIC_URL: str = ""

    @model_validator(mode="after")
    def check_secrets(self):
        if self.SECRET_KEY == _DEFAULT_SECRET:
            raise ValueError(
                "SECRET_KEY no puede ser el valor por defecto. " "Genera una clave segura con: openssl rand -hex 32"
            )
        if self.TENANT_ENCRYPTION_KEY == _DEFAULT_ENCRYPTION:
            raise ValueError(
                "TENANT_ENCRYPTION_KEY no puede ser el valor por defecto. "
                'Genera una clave con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
        return self

    # Base de datos
    # RUNTIME: conecta con el rol de aplicación `pyme_app` (NOSUPERUSER
    # NOBYPASSRLS) para que la RLS de Postgres se aplique de verdad — un
    # superusuario la bypassa por completo. Ver app.db.security_bootstrap.
    DATABASE_URL: str = "postgresql+asyncpg://pyme_app:pyme_pass@localhost:5433/pyme_db"
    # ADMIN: conexión privilegiada (rol bootstrap `pyme_user`) usada SOLO por las
    # migraciones/DDL y por la creación del rol de app. NUNCA por el runtime.
    ADMIN_DATABASE_URL: str = "postgresql+asyncpg://pyme_user:pyme_pass@localhost:5433/pyme_db"

    # LLM
    DEFAULT_LLM_PROVIDER: str = "claude_code"  # claude_code | anthropic | openai | groq | openrouter
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

    # OAuth — Redes sociales (Marketing)
    OAUTH_REDIRECT_URI: str = "http://localhost:8080/api/v1/marketing/oauth/callback"
    # Proxy OAuth (Render): si está definido, el intercambio code→token y el
    # fb_exchange_token se hacen en el servidor (que guarda el client_secret),
    # no en el cliente. Vacío → comportamiento actual (secret local). Ver
    # desktop/docs/oauth_proxy.md para el contrato del endpoint.
    OAUTH_PROXY_URL: str = ""  # usado por la generación/búsqueda de imágenes (proxy Render)

    # Búsqueda de imágenes (Marketing)
    UNSPLASH_ACCESS_KEY: str = ""
    # Generación de imágenes con IA (usa OPENAI_API_KEY). dall-e-3 devuelve URL
    # pública temporal (~2h); modelos que devuelven base64 no se soportan aquí.
    OPENAI_IMAGE_MODEL: str = "dall-e-3"

    # Marketing social vía Zernio (BYO: cada usuario trae su propia API key,
    # guardada cifrada en BD; aquí solo la base de la API).
    ZERNIO_API_BASE: str = "https://zernio.com/api/v1"

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

    # Observabilidad — Langfuse (opcional, traza llamadas LLM si las dos keys
    # están presentes; sino el código sigue funcionando en modo silencioso).
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # Sincronización bancaria: si True, "sincronizar" genera movimientos [DEMO]
    # cuando PSD2 no está configurado (solo entornos de demostración).
    BANKING_DEMO_SYNC: bool = False

    # Backups automáticos de la BD del usuario.
    BACKUP_ENABLED: bool = True
    BACKUP_DIR: str = ""  # Vacío → %APPDATA%/AutomatizaPyme/backups (default por OS)
    BACKUP_RETENTION_DAYS: int = 7

    # Tope de gasto LLM mensual AGREGADO por tenant (USD). None/0 → desactivado.
    # Complementa el límite por empleado IA (AIEmployee.budget_limit_usd). Lo
    # comprueba check_tenant_budget antes del dispatch del orquestador.
    TENANT_MONTHLY_LLM_BUDGET_USD: float | None = None

    # Entorno
    ENVIRONMENT: str = "development"  # development | staging | production

    # Cache del clasificador de intenciones (orchestrator/classifier.py).
    # Las clasificaciones se memoizan por (tenant, intent normalizado) con este TTL.
    # En desarrollo conviene bajarlo (p.ej. 60s) para iterar sobre _KEYWORD_MAP /
    # _STRONG_KEYWORDS sin esperar 24h ni hacer flush manual del cache. Para
    # invalidar el cache en caliente sin reiniciar, usar DELETE /api/v1/admin/llm-cache.
    CLASSIFY_CACHE_TTL_SECONDS: int = 86400


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def frontend_origin() -> str:
    """Origen (scheme://host:port) del primer FRONTEND_URL.

    Para `postMessage`/CORS hace falta UN origen exacto, no una lista ni una ruta
    (M2: evita `targetOrigin='*'`). Cae al valor crudo si no se puede parsear.
    """
    from urllib.parse import urlparse

    first = (settings.FRONTEND_URL or "").split(",")[0].strip()
    parsed = urlparse(first)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    # Sin un origen válido, postMessage(..., "") se trata como "null" y el popup
    # de OAuth se cuelga en silencio. Caemos al default y dejamos rastro en logs
    # en vez de devolver una cadena vacía indetectable.
    _logger.warning(
        "FRONTEND_URL ('%s') no es un origen válido; usando %s para postMessage/OAuth",
        settings.FRONTEND_URL,
        _DEFAULT_FRONTEND_URL,
    )
    return first or _DEFAULT_FRONTEND_URL
