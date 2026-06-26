"""Users management endpoints."""

import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import as_aware
from app.core.dependencies import get_current_user, require_role
from app.core.security import create_access_token, create_refresh_token
from app.db.base import get_db
from app.db.models.auth import User, UserInvitation
from app.services import user_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/users", tags=["users"])


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str | None = None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None
    role: Literal["admin", "user", "viewer", "employee"] = "user"


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    role: Literal["admin", "user", "viewer", "employee"] | None = None
    is_active: bool | None = None


def _user_out(u: User) -> UserOut:
    return UserOut(
        id=str(u.id), email=u.email, full_name=u.full_name, role=u.role, is_active=u.is_active
    )


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    users = await user_service.list_users(current_user.tenant_id, db)
    return [_user_out(u) for u in users]


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return _user_out(current_user)


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = await user_service.create_user(
        tenant_id=current_user.tenant_id,
        email=payload.email,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        db=db,
    )
    return _user_out(user)


# ── Invitations ──────────────────────────────────────────────────────────────


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "employee"
    ttl_days: int = Field(default=7, ge=1, le=30)


class InvitationOut(BaseModel):
    id: str
    email: str
    role: str
    expires_at: datetime
    used_at: datetime | None = None
    used_by_id: str | None = None
    created_at: datetime
    status: str  # pending | used | expired


class InvitationCreateResponse(InvitationOut):
    token: str  # raw token, only returned once at creation


class InvitationPublic(BaseModel):
    """Datos públicos de la invitación, devueltos en /by-token para mostrar al invitado."""
    email: str
    role: str
    expires_at: datetime


class InvitationAccept(BaseModel):
    password: str = Field(min_length=8)
    first_name: str | None = None
    last_name: str | None = None


def _invitation_status(inv: UserInvitation) -> str:
    if inv.used_at is not None:
        return "used"
    expires_at = as_aware(inv.expires_at)
    if expires_at and expires_at < datetime.now(UTC):
        return "expired"
    return "pending"


def _invitation_out(inv: UserInvitation) -> InvitationOut:
    return InvitationOut(
        id=str(inv.id),
        email=inv.email,
        role=inv.role,
        expires_at=inv.expires_at,
        used_at=inv.used_at,
        used_by_id=str(inv.used_by_id) if inv.used_by_id else None,
        created_at=inv.created_at,
        status=_invitation_status(inv),
    )


@router.get("/invitations", response_model=list[InvitationOut])
async def list_invitations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    invs = await user_service.list_invitations(current_user.tenant_id, db)
    return [_invitation_out(i) for i in invs]


@router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    payload: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    # Reject if there's already an active user with that email in the tenant
    email_norm = payload.email.strip().lower()
    existing = await db.execute(
        select(User).where(
            User.tenant_id == current_user.tenant_id, User.email == email_norm
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")

    try:
        inv, raw_token = await user_service.create_invitation(
            tenant_id=current_user.tenant_id,
            email=email_norm,
            role=payload.role,
            created_by_id=current_user.id,
            db=db,
            ttl_days=payload.ttl_days,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return InvitationCreateResponse(
        id=str(inv.id),
        email=inv.email,
        role=inv.role,
        expires_at=inv.expires_at,
        used_at=inv.used_at,
        used_by_id=None,
        created_at=inv.created_at,
        status="pending",
        token=raw_token,
    )


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    inv = await user_service.get_invitation(
        uuid.UUID(invitation_id), current_user.tenant_id, db
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    await user_service.revoke_invitation(inv, db)


@router.get("/invitations/by-token/{token}", response_model=InvitationPublic)
async def get_invitation_public(token: str, db: AsyncSession = Depends(get_db)):
    inv = await user_service.get_invitation_by_token(token, db)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    if inv.used_at is not None:
        raise HTTPException(status_code=410, detail="La invitación ya fue utilizada")
    if as_aware(inv.expires_at) < datetime.now(UTC):
        raise HTTPException(status_code=410, detail="La invitación ha caducado")
    return InvitationPublic(email=inv.email, role=inv.role, expires_at=inv.expires_at)


@router.post("/invitations/by-token/{token}/accept")
async def accept_invitation(
    token: str,
    payload: InvitationAccept,
    db: AsyncSession = Depends(get_db),
):
    inv = await user_service.get_invitation_by_token(token, db)
    if not inv:
        raise HTTPException(status_code=404, detail="Invitación no encontrada")
    if inv.used_at is not None:
        raise HTTPException(status_code=410, detail="La invitación ya fue utilizada")
    if as_aware(inv.expires_at) < datetime.now(UTC):
        raise HTTPException(status_code=410, detail="La invitación ha caducado")

    # Reject if a user already has this email (defense against race / manual creation)
    existing = await db.execute(select(User).where(User.email == inv.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe un usuario con ese email")

    user = await user_service.accept_invitation(
        invitation=inv,
        password=payload.password,
        first_name=payload.first_name,
        last_name=payload.last_name,
        db=db,
    )

    token_data = {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "full_name": user.full_name or "",
        "email": user.email,
    }
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "user": _user_out(user),
    }


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = await user_service.get_user(uuid.UUID(user_id), current_user.tenant_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return _user_out(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    user = await user_service.get_user(uuid.UUID(user_id), current_user.tenant_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user = await user_service.update_user(
        user=user,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        is_active=payload.is_active,
        db=db,
    )
    return _user_out(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Borra un usuario del tenant. Solo admin del propio tenant."""
    user = await user_service.get_user(uuid.UUID(user_id), current_user.tenant_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await user_service.delete_user(user, db)
