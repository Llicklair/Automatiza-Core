"""Rutas de autenticación: registro, login y refresh token."""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.base import get_db
from app.db.models.models import Tenant, User, PasswordResetToken
from app.core.dependencies import get_current_user
from app.middleware.rate_limit import limiter
from app.api.v1.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserOut
from app.services.audit import log_action
from app.services.email_reset import send_password_reset_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Devuelve los datos básicos del usuario autenticado."""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name or "",
        "role": current_user.role,
        "tenant_id": str(current_user.tenant_id),
    }


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def register(request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # Comprobar email duplicado
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El email ya está registrado")

    # Comprobar NIF de tenant duplicado
    existing_tenant = await db.execute(
        select(Tenant).where(Tenant.nif == payload.tenant.nif)
    )
    if existing_tenant.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El NIF ya está registrado")

    # Crear tenant
    tenant = Tenant(name=payload.tenant.name, nif=payload.tenant.nif)
    db.add(tenant)
    await db.flush()

    # Crear usuario admin del tenant
    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role="admin",
    )
    db.add(user)
    await db.flush()

    await log_action(
        db,
        tenant_id=tenant.id,
        agent_name="system",
        action_type="user_registered",
        status="success",
        input_data={"email": payload.email, "nif": payload.tenant.nif},
    )

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/5minutes")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")

    # Actualizar último login
    user.last_login_at = datetime.now(UTC)
    await db.commit()

    token_data = {"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role, "full_name": user.full_name or "", "email": user.email}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

    token_data = {"sub": data["sub"], "tenant_id": data["tenant_id"], "role": data["role"], "full_name": data.get("full_name", ""), "email": data.get("email", "")}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


# ── Password Reset ─────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password", status_code=200)
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Solicita un enlace de recuperación. Siempre devuelve 200 para no revelar si el email existe."""
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user and user.is_active:
        # Generar token seguro
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=1)

        # Invalidar tokens anteriores del mismo usuario
        old = await db.execute(
            select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        )
        for old_token in old.scalars().all():
            old_token.used_at = datetime.now(UTC)

        db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
        await db.commit()

        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
        send_password_reset_email(payload.email, reset_url, user.full_name or "")

    return {"message": "Si el email existe, recibirás un enlace en breve."}


@router.post("/reset-password", status_code=200)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="La contraseña debe tener al menos 8 caracteres.")

    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalar_one_or_none()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Enlace inválido o expirado.")
    if reset_token.used_at is not None:
        raise HTTPException(status_code=400, detail="Este enlace ya fue utilizado.")
    if reset_token.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=400, detail="El enlace ha expirado. Solicita uno nuevo.")

    # Actualizar contraseña
    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario no encontrado.")

    user.hashed_password = get_password_hash(payload.new_password)
    reset_token.used_at = datetime.now(UTC)
    await db.commit()

    return {"message": "Contraseña actualizada correctamente."}
