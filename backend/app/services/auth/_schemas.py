"""Schemas owned by the auth service (canonical location).

Routes' schemas/auth.py re-exports from here so route handlers see no change.
"""

from pydantic import BaseModel, EmailStr, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    nif: str = Field(..., pattern=r"^[A-Z0-9]{9}$", description="NIF/CIF español (9 chars)")


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None
    tenant: TenantCreate
