"""SEC.RBAC — los endpoints de gestión (import masivo + conectar/desconectar
integraciones) exigen rol admin.

El gate `_employee_can_access` ya frena al rol `employee`, pero los roles
intermedios (`user`, `viewer`) se colaban: este test fija que un usuario `user`
recibe 403 en esas operaciones, y que las rutas de SOLO LECTURA siguen abiertas.
"""
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.models.models import Tenant, User
from app.main import app


@pytest_asyncio.fixture
async def user_client(db):
    """Cliente autenticado con rol 'user' (ni admin ni employee)."""
    tenant = Tenant(id=uuid4(), name="Empresa RBAC S.L.", nif="B45612300", plan="starter")
    db.add(tenant)
    await db.flush()
    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="user@empresa.com",
        hashed_password=get_password_hash("UserPass123!"),
        full_name="Usuario Normal",
        role="user",
    )
    db.add(user)
    await db.commit()
    token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(tenant.id), "role": "user"}
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac


class TestRbacAdminOnly:
    @pytest.mark.asyncio
    async def test_user_cannot_bulk_import(self, user_client):
        r = await user_client.post("/api/v1/import/employees", json={"rows": []})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_user_cannot_disconnect_gmail(self, user_client):
        r = await user_client.delete("/api/v1/integrations/gmail/disconnect")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_user_cannot_disconnect_psd2(self, user_client):
        r = await user_client.delete("/api/v1/integrations/psd2/disconnect")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_user_can_read_integrations_list(self, user_client):
        # Solo lectura → sigue accesible para un usuario normal.
        r = await user_client.get("/api/v1/integrations/")
        assert r.status_code == 200


class TestRbacAdminAllowed:
    @pytest.mark.asyncio
    async def test_admin_can_bulk_import(self, auth_client):
        # auth_client (conftest) es rol admin → el gate le deja pasar.
        r = await auth_client.post("/api/v1/import/employees", json={"rows": []})
        assert r.status_code == 200
