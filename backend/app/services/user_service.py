"""User CRUD operations â€” business logic extracted from routes."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.models.auth import User, UserInvitation

ALLOWED_ROLES = {"admin", "user", "viewer", "employee"}
DEFAULT_INVITATION_TTL_DAYS = 7


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def list_users(tenant_id: uuid.UUID, db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).where(User.tenant_id == tenant_id))
    return list(result.scalars().all())


async def get_user(user_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    return result.scalar_one_or_none()


async def create_user(
    tenant_id: uuid.UUID,
    email: str,
    password: str,
    first_name: str | None,
    last_name: str | None,
    role: str,
    db: AsyncSession,
) -> User:
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Rol inválido: {role}")
    full_name = " ".join(filter(None, [first_name, last_name])) or None
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    user: User,
    first_name: str | None,
    last_name: str | None,
    role: str | None,
    is_active: bool | None,
    db: AsyncSession,
) -> User:
    if role is not None and role not in ALLOWED_ROLES:
        raise ValueError(f"Rol inválido: {role}")
    parts = [first_name, last_name]
    if any(p is not None for p in parts):
        user.full_name = " ".join(filter(None, parts)) or user.full_name
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(user: User, db: AsyncSession) -> None:
    await db.delete(user)
    await db.commit()


# ── Invitations ──────────────────────────────────────────────────────────────


async def create_invitation(
    tenant_id: uuid.UUID,
    email: str,
    role: str,
    created_by_id: uuid.UUID,
    db: AsyncSession,
    ttl_days: int = DEFAULT_INVITATION_TTL_DAYS,
) -> tuple[UserInvitation, str]:
    """Crea una invitación. Devuelve (registro, raw_token). Solo el raw_token se comparte; el hash queda en BD."""
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Rol inválido: {role}")
    raw_token = secrets.token_urlsafe(32)
    inv = UserInvitation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=email.strip().lower(),
        role=role,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=ttl_days),
        created_by_id=created_by_id,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv, raw_token


async def list_invitations(tenant_id: uuid.UUID, db: AsyncSession) -> list[UserInvitation]:
    result = await db.execute(
        select(UserInvitation)
        .where(UserInvitation.tenant_id == tenant_id)
        .order_by(UserInvitation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_invitation(
    invitation_id: uuid.UUID, tenant_id: uuid.UUID, db: AsyncSession
) -> UserInvitation | None:
    result = await db.execute(
        select(UserInvitation).where(
            UserInvitation.id == invitation_id,
            UserInvitation.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def revoke_invitation(invitation: UserInvitation, db: AsyncSession) -> None:
    """Marca la invitación como usada (used_at=now) sin used_by para que ya no sea aceptable."""
    if invitation.used_at is None:
        invitation.used_at = datetime.now(UTC)
        await db.commit()


async def get_invitation_by_token(token: str, db: AsyncSession) -> UserInvitation | None:
    result = await db.execute(
        select(UserInvitation).where(UserInvitation.token_hash == _hash_token(token))
    )
    return result.scalar_one_or_none()


async def accept_invitation(
    invitation: UserInvitation,
    password: str,
    first_name: str | None,
    last_name: str | None,
    db: AsyncSession,
) -> User:
    """Crea el User a partir de la invitación, marca used_at/used_by_id."""
    full_name = " ".join(filter(None, [first_name, last_name])) or None
    user = User(
        id=uuid.uuid4(),
        tenant_id=invitation.tenant_id,
        email=invitation.email,
        hashed_password=get_password_hash(password),
        full_name=full_name,
        role=invitation.role,
    )
    db.add(user)
    await db.flush()  # populate user.id

    invitation.used_at = datetime.now(UTC)
    invitation.used_by_id = user.id
    await db.commit()
    await db.refresh(user)
    return user
