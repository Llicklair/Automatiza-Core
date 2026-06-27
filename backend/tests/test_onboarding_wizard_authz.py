"""
Regresión authz: las rutas MUTANTES del wizard onboarding exigen role='admin'.

Antes del fix las 5 rutas que mutan el estado de onboarding TENANT-WIDE
(patch_step, post_skip, post_reset, post_seed, delete_seed) usaban solo
Depends(get_current_user) → cualquier miembro no-admin podía marcar pasos,
saltar/reiniciar el wizard de TODA la organización y sembrar/borrar datos demo.

Ahora usan Depends(require_role("admin")) — coherente con las rutas hermanas
REGAP (onboarding_regap.py) que ya estaban gateadas con _admin_only.

Cobertura:
  - no-admin sobre PATCH/POST reset/DELETE seed → 403 (gate activo).
  - admin sobre POST reset → NO 403 (gate selectivo, no rompe el onboarding).
  - no-admin sobre GET wizard → NO 403 (lectura sigue abierta, no se sobre-gatea).
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
        name="Tenant Wizard NoAdmin S.L.",
        nif="B22222222",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="wizard_nonadmin@empresa.com",
        hashed_password=get_password_hash("NoAdminPass123!"),
        full_name="Wizard NoAdmin",
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

class TestOnboardingWizardAuthz:

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_reset_wizard(self, nonadmin_client: AsyncClient):
        """no-admin POST /onboarding/wizard/reset → 403 (reset es tenant-wide)."""
        resp = await nonadmin_client.post("/api/v1/onboarding/wizard/reset")
        assert resp.status_code == 403, (
            f"no-admin reseteó el wizard tenant-wide: {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_patch_step(self, nonadmin_client: AsyncClient):
        """no-admin PATCH /onboarding/wizard → 403 (marca pasos tenant-wide)."""
        resp = await nonadmin_client.patch(
            "/api/v1/onboarding/wizard",
            json={"step": "company", "value": True},
        )
        assert resp.status_code == 403, (
            f"no-admin marcó un paso del wizard: {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_delete_seed(self, nonadmin_client: AsyncClient):
        """no-admin DELETE /onboarding/wizard/seed → 403 (borra datos demo)."""
        resp = await nonadmin_client.delete("/api/v1/onboarding/wizard/seed")
        assert resp.status_code == 403, (
            f"no-admin borró datos demo del tenant: {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_can_reset_wizard(self, admin_client: AsyncClient):
        """CONTROL: admin POST /onboarding/wizard/reset → NO 403 (gate selectivo)."""
        resp = await admin_client.post("/api/v1/onboarding/wizard/reset")
        assert resp.status_code != 403, (
            f"Gate sobre-restricto: admin obtuvo 403 al resetear el wizard. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_can_read_wizard(self, nonadmin_client: AsyncClient):
        """CONTROL-INVERSO: no-admin GET /onboarding/wizard → NO 403 (lectura abierta)."""
        resp = await nonadmin_client.get("/api/v1/onboarding/wizard")
        assert resp.status_code != 403, (
            f"Se sobre-gateó la lectura: no-admin obtuvo 403 al leer el wizard. "
            f"Respuesta: {resp.text}"
        )
