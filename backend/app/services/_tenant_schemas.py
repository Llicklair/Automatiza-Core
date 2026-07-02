"""Schemas owned by the tenant service.

Routes' schemas/tenant.py re-exports from here so route handlers see no change.
"""

from pydantic import BaseModel


class LlmProviderConfig(BaseModel):
    api_key: str | None = None
    model: str | None = None
    enabled: bool = False
