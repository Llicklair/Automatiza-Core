"""Rutas de autenticación: registro, login y refresh token."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.base import get_db
from app.db.models.models import Tenant, User
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserCreate, UserOut
from app.services.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
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
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
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

    token_data = {"sub": str(user.id), "tenant_id": str(user.tenant_id), "role": user.role}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")

    token_data = {"sub": data["sub"], "tenant_id": data["tenant_id"], "role": data["role"]}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )
