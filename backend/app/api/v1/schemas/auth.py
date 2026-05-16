"""Schemas Pydantic para autenticación y usuarios."""

from datetime import datetime
from uuid import UUID

# Schemas compartidos con la capa services — re-exportados aquí para mantener
# compat con route handlers existentes; ubicación canónica: services/auth/_schemas.py
from app.services.auth._schemas import TenantCreate, UserCreate  # noqa: F401
from pydantic import BaseModel, EmailStr

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


class TenantOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    name: str
    nif: str
    plan: str
    is_active: bool
    created_at: datetime


# ─── User ────────────────────────────────────────────────────────────────────


# UserCreate y TenantCreate viven en services/auth/_schemas — re-exportados arriba


class UserOut(BaseModel):
    model_config = {"from_attributes": True}
    id: UUID
    tenant_id: UUID
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime


# ─── Password Reset ──────────────────────────────────────────────────────────


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
