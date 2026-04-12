from typing import Any
from uuid import UUID

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


class LlmProviderConfig(BaseModel):
    api_key: str | None = None
    model: str | None = None
    enabled: bool = False


class LlmConfigUpdate(BaseModel):
    active_llm_provider: str | None = None
    active_embeddings_provider: str | None = None
    providers: dict[str, LlmProviderConfig] | None = None


class LlmConfigResponse(BaseModel):
    active_llm_provider: str
    active_embeddings_provider: str
    providers: dict[str, Any]


class ClaudeCodeSetupResponse(BaseModel):
    status: str
    version: str | None = None
    message: str = ""
