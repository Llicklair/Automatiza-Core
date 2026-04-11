"""Schemas Pydantic para autenticación y usuarios."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# ─── Auth ───────────────────────────────────────────────────────────────────


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─── Tenant ──────────────────────────────────────────────────────────────────


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    nif: str = Field(..., pattern=r"^[A-Z0-9]{9}$", description="NIF/CIF español (9 chars)")


class TenantOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    nif: str
    plan: str
    is_active: bool
    created_at: datetime


# ─── User ────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    # Registro inicial: se crea el tenant en el mismo call
    tenant: TenantCreate


class UserOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
