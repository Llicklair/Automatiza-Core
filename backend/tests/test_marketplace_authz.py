"""
Regresión (authz): seed-official del marketplace exige rol admin.

Antes del fix, POST /api/v1/marketplace/templates/seed-official usaba solo
Depends(get_current_user) — sin gate de rol. Ese endpoint ESCRIBE en la tabla
GLOBAL `workflow_template` (no es por-tenant): cualquier usuario autenticado podía
modificar el catálogo global. Es una operación de admin/setup.

Ahora seed_official usa Depends(require_role("admin")). Este test demuestra que el
gate está activo y es SELECTIVO:
  - no-admin → 403
  - admin → NO 403 (control: el gate deja pasar a admins)
  - no-admin GET /templates → NO 403 (control-inverso: listar sigue abierto)
  - no-admin POST .../install → NO 403 (control-inverso: install NO se gateó;
    puede dar 404 si el slug no existe, pero nunca 403 por authz)
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Fixtures (mismo patrón que test_privesc_regression.py)
# ---------------------------------------------------------------------------

@pytest.fixture
async def nonadmin_client(client: AsyncClient, db):
    """Cliente HTTP con token JWT de role='user' (no-admin)."""
    from app.core.security import create_access_token, get_password_hash
    from app.db.models.models import Tenant, User

    tenant = Tenant(
        id=uuid4(),
        name="Tenant NoAdmin Mkt S.L.",
        nif="B22222222",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="nonadmin_mkt@empresa.com",
        hashed_password=get_password_hash("NoAdminPass123!"),
        full_name="Usuario NoAdmin Mkt",
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

SEED_PATH = "/api/v1/marketplace/templates/seed-official"


class TestMarketplaceSeedAuthz:

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_seed_official(self, nonadmin_client: AsyncClient):
        """
        CASO oro: un no-admin intenta sembrar el catálogo GLOBAL.
        Debe obtener 403. Antes del fix devolvía 200 → escritura global no autorizada.
        Si se revierte el Depends(require_role("admin")), falla con 200 != 403.
        """
        resp = await nonadmin_client.post(SEED_PATH)
        assert resp.status_code == 403, (
            f"Escritura global no autorizada: no-admin obtuvo {resp.status_code} "
            f"al sembrar plantillas oficiales. Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_can_seed_official(self, admin_client: AsyncClient):
        """
        CASO control: un ADMIN siembra el catálogo. NO debe obtener 403.
        Verifica que el gate es selectivo (no rechaza a todos).
        """
        resp = await admin_client.post(SEED_PATH)
        assert resp.status_code != 403, (
            f"Gate sobrerestricto: admin obtuvo 403 al sembrar plantillas. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_can_list_templates(self, nonadmin_client: AsyncClient):
        """
        CONTROL-INVERSO: listar el catálogo sigue abierto a usuarios autenticados.
        no-admin GET /templates NO debe obtener 403 (no sobre-gateamos).
        """
        resp = await nonadmin_client.get("/api/v1/marketplace/templates")
        assert resp.status_code != 403, (
            f"Sobre-gateo: no-admin obtuvo 403 al LISTAR el catálogo. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_install_not_gated_by_role(self, nonadmin_client: AsyncClient):
        """
        CONTROL-INVERSO: install crea workflows del PROPIO tenant; NO se gateó por rol.
        no-admin POST .../{slug}/install NO debe dar 403 por authz. Puede dar 404 si
        el slug no existe, pero nunca 403.
        """
        resp = await nonadmin_client.post(
            "/api/v1/marketplace/templates/slug-inexistente-xyz/install"
        )
        assert resp.status_code != 403, (
            f"Sobre-gateo: no-admin obtuvo 403 en install (no debía gatearse). "
            f"Respuesta: {resp.text}"
        )
