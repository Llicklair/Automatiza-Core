"""User CRUD operations — business logic extracted from routes."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.db.models.auth import User


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
