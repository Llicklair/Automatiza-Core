"""Lógica de negocio de autenticación: registro, login, refresh y reset de contraseña."""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.datetime_utils import as_aware
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.core.tenant_context import rls_bypass
from app.db.models.models import PasswordResetToken, Tenant, User
from app.services.audit import log_action
from app.services.auth._schemas import UserCreate
from app.services.auth.email_reset import send_password_reset_email

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _build_token_data(user: User) -> dict:
    return {
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
        "full_name": user.full_name or "",
        "email": user.email,
    }


def _make_token_pair(token_data: dict) -> dict:
    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
    }


# ── Public API ────────────────────────────────────────────────────────────────


def get_me(user: User) -> dict:
    """Devuelve los datos básicos del usuario autenticado."""
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name or "",
        "role": user.role,
        "tenant_id": str(user.tenant_id),
    }


async def register(payload: UserCreate, db: AsyncSession) -> User:
    """Registra un nuevo tenant + usuario admin. Raises ValueError on duplicates."""
    # Flujo PRE-tenant: aún no existe el tenant, así que la RLS fail-closed
    # bloquearía las comprobaciones de unicidad y la propia INSERT del User
    # (WITH CHECK). El alta de un tenant es por definición global → bypass.
    with rls_bypass():
        # Comprobar email duplicado
        existing = await db.execute(select(User).where(User.email == payload.email))
        if existing.scalar_one_or_none():
            raise ValueError("El email ya está registrado")

        # Comprobar NIF de tenant duplicado
        existing_tenant = await db.execute(select(Tenant).where(Tenant.nif == payload.tenant.nif))
        if existing_tenant.scalar_one_or_none():
            raise ValueError("El NIF ya está registrado")

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

    # Ya existe el tenant: fijamos el contexto para que las escrituras restantes
    # (audit, rutinas de oficio) queden ancladas a él bajo RLS, en vez de seguir
    # con el bypass global.
    from app.core.tenant_context import set_current_tenant

    set_current_tenant(str(tenant.id))

    await log_action(
        db,
        tenant_id=tenant.id,
        agent_name="system",
        action_type="user_registered",
        status="success",
        input_data={"email": payload.email, "nif": payload.tenant.nif},
    )

    # Rutinas de oficio por defecto (motor proactivo). No fatal si falla.
    try:
        from app.services.workflow.default_routines import seed_default_routines

        await seed_default_routines(db, tenant.id, user.id)
    except Exception:
        logger.warning("Seed de rutinas de oficio falló para tenant %s", tenant.id, exc_info=True)

    await db.commit()
    await db.refresh(user)
    return user


async def login(email: str, password: str, db: AsyncSession) -> dict:
    """Autentica un usuario y devuelve tokens. Raises LookupError / PermissionError."""
    # Lookup PRE-tenant (identificamos al usuario por email antes de conocer su
    # tenant) → bypass RLS, si no fail-closed devolvería 0 filas y nadie podría
    # iniciar sesión.
    with rls_bypass():
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise LookupError("Email o contraseña incorrectos")
        if not user.is_active:
            raise PermissionError("Cuenta desactivada")

        # Actualizar último login
        user.last_login_at = datetime.now(UTC)
        await db.commit()

    return _make_token_pair(_build_token_data(user))


def refresh(refresh_token: str) -> dict:
    """Genera nuevos tokens a partir de un refresh token. Raises ValueError."""
    data = decode_token(refresh_token)
    if not data or data.get("type") != "refresh":
        raise ValueError("Refresh token inválido o expirado")

    token_data = {
        "sub": data["sub"],
        "tenant_id": data["tenant_id"],
        "role": data["role"],
        "full_name": data.get("full_name", ""),
        "email": data.get("email", ""),
    }
    return _make_token_pair(token_data)


async def forgot_password(email: str, db: AsyncSession) -> dict:
    """Solicita un enlace de recuperación. Siempre devuelve el mismo mensaje."""
    # Lookup por email PRE-tenant + escritura del token de reset (PasswordResetToken
    # lleva tenant_id) → bypass RLS.
    with rls_bypass():
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user and user.is_active:
            # Generar token seguro
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
            expires_at = datetime.now(UTC) + timedelta(hours=1)

            # Invalidar tokens anteriores del mismo usuario
            old = await db.execute(
                select(PasswordResetToken).where(
                    PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
                )
            )
            for old_token in old.scalars().all():
                old_token.used_at = datetime.now(UTC)

            db.add(
                PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at)
            )
            await db.commit()

            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
            send_password_reset_email(email, reset_url, user.full_name or "")

    return {"message": "Si el email existe, recibirás un enlace en breve."}


async def reset_password(token: str, new_password: str, db: AsyncSession) -> dict:
    """Restablece la contraseña con un token. Raises ValueError."""
    if len(new_password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    # El reset se identifica solo por el hash del token (PRE-tenant) → bypass RLS
    # para localizar el token y el usuario y reescribir la contraseña.
    with rls_bypass():
        result = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            raise ValueError("Enlace inválido o expirado.")
        if reset_token.used_at is not None:
            raise ValueError("Este enlace ya fue utilizado.")
        if as_aware(reset_token.expires_at) < datetime.now(UTC):
            raise ValueError("El enlace ha expirado. Solicita uno nuevo.")

        # Actualizar contraseña
        user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError("Usuario no encontrado.")

        user.hashed_password = get_password_hash(new_password)
        reset_token.used_at = datetime.now(UTC)
        await db.commit()

    return {"message": "Contraseña actualizada correctamente."}
