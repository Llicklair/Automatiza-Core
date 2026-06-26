"""
Regresión: escalada de privilegios en /users (POST y PATCH).

Antes del fix (commit 560b7328), cualquier usuario autenticado podía:
  - Crear un usuario con role="admin"  → 201 (debía ser 403)
  - Parchear su propio usuario con role="admin" → 200 (debía ser 403)

Ahora esas rutas usan Depends(require_role("admin")).
Este test demuestra que el gate está activo y es selectivo (deja pasar a admins).
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Fixture: cliente autenticado con role="user" (no-admin)
# ---------------------------------------------------------------------------

@pytest.fixture
async def nonadmin_client(client: AsyncClient, db):
    """
    Cliente HTTP con token JWT de role='user'.
    Reutiliza el engine SQLite en memoria del conftest; crea tenant+usuario
    con role='user' y configura el header Authorization.
    """
    from app.core.security import create_access_token, get_password_hash
    from app.db.models.models import Tenant, User

    tenant = Tenant(
        id=uuid4(),
        name="Tenant NoAdmin S.L.",
        nif="B11111111",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="nonadmin@empresa.com",
        hashed_password=get_password_hash("NoAdminPass123!"),
        full_name="Usuario NoAdmin",
        role="user",
    )
    db.add(user)
    await db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(tenant.id),
        "role": "user",
    })

    client.headers["Authorization"] = f"Bearer {token}"
    # Devolvemos también el user_id para el caso PATCH self-promotion
    client._nonadmin_user_id = str(user.id)
    return client


# ---------------------------------------------------------------------------
# Fixture: cliente admin (reutiliza seed_tenant_and_user del conftest)
# ---------------------------------------------------------------------------

@pytest.fixture
async def admin_client(client: AsyncClient, seed_tenant_and_user):
    """Cliente HTTP con token JWT de role='admin'."""
    _, _, token = seed_tenant_and_user
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPrivescRegression:

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_create_user_with_admin_role(
        self, nonadmin_client: AsyncClient
    ):
        """
        CASO 1 (oro): un usuario con role='user' intenta crear otro usuario con
        role='admin' via POST /api/v1/users.
        Debe obtener 403. Antes del fix devolvía 201 → escalada confirmada.
        Si se revierte el Depends(require_role("admin")), este test falla con
        AssertionError: 201 != 403.
        """
        resp = await nonadmin_client.post(
            "/api/v1/users",
            json={
                "email": "nuevo_admin@empresa.com",
                "password": "Admin123!",
                "first_name": "Nuevo",
                "last_name": "Admin",
                "role": "admin",
            },
        )
        assert resp.status_code == 403, (
            f"Escalada de privilegios activa: no-admin obtuvo {resp.status_code} "
            f"al crear usuario con role='admin'. Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_self_promote_via_patch(
        self, nonadmin_client: AsyncClient
    ):
        """
        CASO 2: un usuario con role='user' intenta autopromocionar su propio
        registro a role='admin' via PATCH /api/v1/users/{su_id}.
        Debe obtener 403. Antes del fix devolvía 200 → auto-escalada.
        Si se revierte el Depends(require_role("admin")) en PATCH, falla con
        AssertionError: 200 != 403.
        """
        user_id = nonadmin_client._nonadmin_user_id
        resp = await nonadmin_client.patch(
            f"/api/v1/users/{user_id}",
            json={"role": "admin"},
        )
        assert resp.status_code == 403, (
            f"Auto-promoción activa: no-admin obtuvo {resp.status_code} "
            f"al parchear su propio role a 'admin'. Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_can_create_user_with_valid_role(
        self, admin_client: AsyncClient
    ):
        """
        CASO 3 (control): un usuario ADMIN crea un usuario con role='user'.
        Debe obtener 201. Verifica que el gate es selectivo, no que rechaza todo.
        Si este test falla, el gate está sobrerestricto y rompe funcionalidad legítima.
        """
        resp = await admin_client.post(
            "/api/v1/users",
            json={
                "email": "empleado@empresa.com",
                "password": "Empleado123!",
                "first_name": "Juan",
                "last_name": "Empleado",
                "role": "user",
            },
        )
        assert resp.status_code == 201, (
            f"Admin no pudo crear usuario legítimo: {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_invalid_role_rejected_by_schema(
        self, admin_client: AsyncClient
    ):
        """
        CASO 4: incluso un ADMIN no puede crear usuario con role='superadmin'
        porque el schema Literal['admin','user','viewer','employee'] lo rechaza
        antes de llegar al servicio → 422.
        Verifica que la capa de validación de Pydantic está activa.
        """
        resp = await admin_client.post(
            "/api/v1/users",
            json={
                "email": "superadmin@empresa.com",
                "password": "Super123!",
                "first_name": "Super",
                "last_name": "Admin",
                "role": "superadmin",
            },
        )
        assert resp.status_code == 422, (
            f"Schema no rechazó role='superadmin': obtuvo {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )
