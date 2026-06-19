"""Rutas de autenticación: registro, login y refresh token."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserOut,
)
from app.core.dependencies import get_current_user
from app.core.net import is_local_request
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.auth import service as svc

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Devuelve los datos básicos del usuario autenticado."""
    return svc.get_me(current_user)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/hour")
async def register(request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    # SEC.REMOTE — /register crea un tenant+admin nuevo: es una operación de setup
    # que solo tiene sentido en el equipo local. Con el backend expuesto a internet
    # (acceso remoto), bloqueamos el registro desde la LAN o el túnel para que nadie
    # pueda crear tenants en la BD del cliente. 404 para no anunciar el endpoint.
    if not is_local_request(request):
        raise HTTPException(status_code=404, detail="Not found")
    try:
        return await svc.register(payload, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/5minutes")
async def login(request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        return await svc.login(payload.email, payload.password, db)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest):
    try:
        return svc.refresh(payload.refresh_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


# ── Password Reset ─────────────────────────────────────────────────────────────


@router.post("/forgot-password", status_code=200)
@limiter.limit("3/hour")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Solicita un enlace de recuperación. Siempre devuelve 200 para no revelar si el email existe."""
    return await svc.forgot_password(payload.email, db)


@router.post("/reset-password", status_code=200)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await svc.reset_password(payload.token, payload.new_password, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
