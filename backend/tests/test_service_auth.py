"""Tests para app.services.auth.service — login, refresh, reset de contraseña.

Cubre happy path y caminos de error: credenciales inválidas, cuenta desactivada,
tokens inválidos/expirados, reset con token usado o caducado.

Mockea `send_password_reset_email` para no abrir conexiones SMTP.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from app.db.models.models import PasswordResetToken, Tenant, User
from app.services.auth import service as auth_service
from app.services.auth._schemas import TenantCreate, UserCreate
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _seed_user(
    db: AsyncSession,
    *,
    email: str = "user@empresa.com",
    password: str = "OldPass123!",
    is_active: bool = True,
) -> User:
    tenant = Tenant(id=uuid4(), name="ACME SL", nif="B11111111", plan="starter")
    db.add(tenant)
    await db.flush()
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email=email,
        hashed_password=get_password_hash(password),
        full_name="User One",
        role="admin",
        is_active=is_active,
    )
    db.add(user)
    await db.commit()
    return user


# ── register ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRegister:
    async def test_crea_tenant_y_usuario_admin(self, db):
        payload = UserCreate(
            email="nuevo@empresa.com",
            password="MyPass1234!",
            full_name="Nuevo Usuario",
            tenant=TenantCreate(name="Nueva SL", nif="B12345678"),
        )
        user = await auth_service.register(payload, db)
        assert user.email == "nuevo@empresa.com"
        assert user.role == "admin"
        assert user.tenant_id is not None
        # Password debe estar hasheada
        assert user.hashed_password != "MyPass1234!"
        assert verify_password("MyPass1234!", user.hashed_password)

    async def test_falla_si_email_duplicado(self, db):
        await _seed_user(db, email="dup@empresa.com")
        payload = UserCreate(
            email="dup@empresa.com",
            password="Pass12345!",
            tenant=TenantCreate(name="XX SL", nif="B99999999"),
        )
        with pytest.raises(ValueError, match="email"):
            await auth_service.register(payload, db)

    async def test_falla_si_nif_duplicado(self, db):
        await _seed_user(db)  # crea tenant con nif B11111111
        payload = UserCreate(
            email="otro@empresa.com",
            password="Pass12345!",
            tenant=TenantCreate(name="Otro SL", nif="B11111111"),
        )
        with pytest.raises(ValueError, match="NIF"):
            await auth_service.register(payload, db)


# ── login ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestLogin:
    async def test_devuelve_par_de_tokens(self, db):
        await _seed_user(db, email="login@empresa.com", password="MyPass1234!")
        tokens = await auth_service.login("login@empresa.com", "MyPass1234!", db)
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["access_token"] != tokens["refresh_token"]

    async def test_falla_con_password_incorrecto(self, db):
        await _seed_user(db, email="login@empresa.com", password="MyPass1234!")
        with pytest.raises(LookupError):
            await auth_service.login("login@empresa.com", "WrongPass!", db)

    async def test_falla_si_email_no_existe(self, db):
        with pytest.raises(LookupError):
            await auth_service.login("noexiste@empresa.com", "x", db)

    async def test_falla_si_cuenta_desactivada(self, db):
        await _seed_user(
            db, email="off@empresa.com", password="MyPass1234!", is_active=False
        )
        with pytest.raises(PermissionError):
            await auth_service.login("off@empresa.com", "MyPass1234!", db)


# ── refresh ──────────────────────────────────────────────────────────────────


class TestRefresh:
    def test_genera_nuevos_tokens(self):
        token_data = {
            "sub": str(uuid4()),
            "tenant_id": str(uuid4()),
            "role": "admin",
            "full_name": "X",
            "email": "x@y.com",
        }
        rt = create_refresh_token(token_data)
        result = auth_service.refresh(rt)
        assert "access_token" in result and "refresh_token" in result

    def test_falla_si_token_invalido(self):
        with pytest.raises(ValueError):
            auth_service.refresh("no-es-un-token-jwt")

    def test_falla_si_es_access_token_en_lugar_de_refresh(self):
        token_data = {"sub": str(uuid4()), "tenant_id": str(uuid4()), "role": "admin"}
        at = create_access_token(token_data)
        with pytest.raises(ValueError):
            auth_service.refresh(at)


# ── forgot/reset password ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestResetPassword:
    async def test_forgot_no_revela_existencia_de_email(self, db):
        """Tanto si existe como si no, devuelve el mismo mensaje."""
        with patch(
            "app.services.auth.service.send_password_reset_email", return_value=True
        ):
            r1 = await auth_service.forgot_password("noexiste@x.com", db)
            r2 = await auth_service.forgot_password("tampoco@y.com", db)
        assert r1 == r2

    async def test_forgot_crea_token_si_user_existe(self, db):
        user = await _seed_user(db, email="forgot@empresa.com")
        with patch(
            "app.services.auth.service.send_password_reset_email", return_value=True
        ):
            await auth_service.forgot_password("forgot@empresa.com", db)

        tokens = await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user.id)
        )
        assert tokens.scalar_one_or_none() is not None

    async def test_reset_actualiza_password_y_marca_token_usado(self, db):
        user = await _seed_user(db, email="reset@empresa.com", password="OldPass123!")

        # Generar token manualmente como lo haría forgot_password
        import hashlib
        import secrets

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        prt = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(prt)
        await db.commit()

        result = await auth_service.reset_password(raw_token, "NewPass456!", db)
        assert "actualizada" in result["message"].lower()

        # La password ahora valida la nueva
        await db.refresh(user)
        assert verify_password("NewPass456!", user.hashed_password)
        await db.refresh(prt)
        assert prt.used_at is not None

    async def test_reset_falla_si_password_corta(self, db):
        with pytest.raises(ValueError, match="8 caracteres"):
            await auth_service.reset_password("xxx", "short", db)

    async def test_reset_falla_si_token_invalido(self, db):
        with pytest.raises(ValueError, match="inválido|expirado"):
            await auth_service.reset_password(
                "token-que-no-existe", "ValidPass1!", db
            )

    async def test_reset_falla_si_token_ya_usado(self, db):
        user = await _seed_user(db, email="used@empresa.com")
        import hashlib
        import secrets

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        prt = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
            used_at=datetime.now(UTC),  # ya usado
        )
        db.add(prt)
        await db.commit()

        with pytest.raises(ValueError, match="utilizado|ya"):
            await auth_service.reset_password(raw_token, "ValidPass1!", db)

    async def test_reset_falla_si_token_expirado(self, db):
        user = await _seed_user(db, email="expired@empresa.com")
        import hashlib
        import secrets

        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        prt = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # expirado
        )
        db.add(prt)
        await db.commit()

        with pytest.raises(ValueError, match="expirado"):
            await auth_service.reset_password(raw_token, "ValidPass1!", db)
