from typing import Any
from uuid import UUID

# Re-export de la ubicación canónica en services/
from app.services._tenant_schemas import LlmProviderConfig  # noqa: F401
from pydantic import BaseModel, ConfigDict


class TenantMeResponse(BaseModel):
    id: UUID
    name: str
    nif: str
    address: str | None = None
    phone: str | None = None
    contact_email: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TenantMeUpdate(BaseModel):
    name: str | None = None
    nif: str | None = None
    address: str | None = None
    phone: str | None = None
    contact_email: str | None = None


# LlmProviderConfig vive en services/_tenant_schemas — re-exportado arriba


class LlmConfigUpdate(BaseModel):
    active_llm_provider: str | None = None
    active_embeddings_provider: str | None = None
    providers: dict[str, LlmProviderConfig] | None = None


class LlmConfigResponse(BaseModel):
    active_llm_provider: str
    active_embeddings_provider: str
    providers: dict[str, Any]
    # BYOK: si la IA está lista (proveedor + clave) y un motivo accionable, para
    # que el frontend muestre el aviso con enlace a Configuración → Claves API.
    ai_ready: bool = True
    ai_reason: str = ""


class ClaudeCodeSetupResponse(BaseModel):
    status: str
    version: str | None = None
    message: str = ""
