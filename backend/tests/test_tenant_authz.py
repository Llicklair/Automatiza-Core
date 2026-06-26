"""
Regresión authz: rutas de ESCRITURA de /api/v1/tenant exigen role='admin'.

Antes del fix, TODAS las rutas mutantes de routes/tenant.py usaban solo
Depends(get_current_user): un usuario no-admin (role='user') podía modificar
datos fiscales (NIF/nombre), el proveedor LLM + claves API, el logo y el
certificado de firma del tenant. El fix gatea cada endpoint mutante con
Depends(require_role("admin")); las rutas de LECTURA (GET) siguen abiertas a
cualquier usuario autenticado.

Casos:
  - no-admin PATCH /tenant/me  -> 403 (gate activo)
  - no-admin PUT  /tenant/llm-config -> 403 (gate activo, 2ª ruta)
  - admin PATCH /tenant/me con NIF válido -> 200 (control: gate selectivo)
  - admin PATCH /tenant/me con nif="" -> 422 (validación de schema)
  - no-admin GET /tenant/me -> NO 403 (lectura sigue abierta, no se sobre-gateó)
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.fixture
async def nonadmin_client(client: AsyncClient, db):
    """Cliente HTTP con token JWT de role='user' (no-admin) en su tenant."""
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
        email="nonadmin_tenant@empresa.com",
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
    return client


@pytest.fixture
async def admin_client(client: AsyncClient, seed_tenant_and_user):
    """Cliente HTTP con token JWT de role='admin'."""
    _, _, token = seed_tenant_and_user
    client.headers["Authorization"] = f"Bearer {token}"
    return client


class TestTenantWriteAuthz:

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_patch_tenant_me(self, nonadmin_client: AsyncClient):
        """no-admin parchea datos fiscales del tenant -> 403."""
        resp = await nonadmin_client.patch(
            "/api/v1/tenant/me",
            json={"nif": "B22222222", "name": "Hackeada S.L."},
        )
        assert resp.status_code == 403, (
            f"no-admin pudo mutar el tenant: {resp.status_code}. Resp: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_put_llm_config(self, nonadmin_client: AsyncClient):
        """no-admin cambia el proveedor LLM/claves API -> 403 (2ª ruta mutante)."""
        resp = await nonadmin_client.put(
            "/api/v1/tenant/llm-config",
            json={"active_llm_provider": "openai"},
        )
        assert resp.status_code == 403, (
            f"no-admin pudo mutar la config LLM: {resp.status_code}. Resp: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_can_patch_tenant_me(self, admin_client: AsyncClient):
        """Control no-tautológico: admin parchea NIF válido -> 200 (gate selectivo)."""
        resp = await admin_client.patch(
            "/api/v1/tenant/me",
            json={"nif": "B87654321"},
        )
        assert resp.status_code == 200, (
            f"Admin no pudo mutar el tenant: {resp.status_code}. Resp: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_patch_blank_nif_rejected(self, admin_client: AsyncClient):
        """Validación: admin envía nif="" -> 422 (schema rechaza vacío)."""
        resp = await admin_client.patch(
            "/api/v1/tenant/me",
            json={"nif": ""},
        )
        assert resp.status_code == 422, (
            f"nif vacío no rechazado por el schema: {resp.status_code}. Resp: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_can_still_read_tenant_me(self, nonadmin_client: AsyncClient):
        """No se sobre-gateó: la LECTURA (GET) sigue abierta a no-admin (no 403)."""
        resp = await nonadmin_client.get("/api/v1/tenant/me")
        assert resp.status_code != 403, (
            f"Se sobre-gateó la lectura: GET devolvió 403. Resp: {resp.text}"
        )
