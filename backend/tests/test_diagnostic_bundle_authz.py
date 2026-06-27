"""
Regresión (authz / exposición de info): GET /system/diagnostic-bundle.

Antes del fix el endpoint usaba solo Depends(get_current_user) — sin gate de
rol. Devolvía un ZIP con los LOGS COMPLETOS del servidor (logs/*.jsonl*),
versión, plataforma y estado de migraciones. Cualquier usuario autenticado
(role='user'/'viewer'/'employee') podía descargarlo. INCONSISTENTE con el
resto de /system/backups/* del MISMO router, que usan require_role("admin").

Ahora el endpoint usa Depends(require_role("admin")).
Este test demuestra que el gate está activo (no-admin → 403), es selectivo
(admin NO recibe 403) y que NO se sobre-gateó otro endpoint del router que
intencionalmente es público (POST /system/frontend-errors).

Fixtures reutilizadas del patrón de test_privesc_regression.py:
nonadmin_client (role='user') y admin_client (seed_tenant_and_user).
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
        name="Tenant NoAdmin Diag S.L.",
        nif="B22222222",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="nonadmin-diag@empresa.com",
        hashed_password=get_password_hash("NoAdminPass123!"),
        full_name="Usuario NoAdmin Diag",
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


class TestDiagnosticBundleAuthz:

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_download_diagnostic_bundle(
        self, nonadmin_client: AsyncClient
    ):
        """
        CASO 1 (oro): un usuario con role='user' descarga el bundle de
        diagnóstico (logs completos del servidor) via GET
        /api/v1/system/diagnostic-bundle.
        Debe obtener 403. Antes del fix devolvía 200 con el ZIP → fuga de logs.
        Si se revierte require_role("admin"), este test falla (no será 403).
        """
        resp = await nonadmin_client.get("/api/v1/system/diagnostic-bundle")
        assert resp.status_code == 403, (
            f"Fuga de logs: no-admin obtuvo {resp.status_code} al descargar "
            f"/system/diagnostic-bundle (debía ser 403). Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_is_not_forbidden(self, admin_client: AsyncClient):
        """
        CASO 2 (control, no sobre-gateo): un ADMIN solicita el bundle.
        El gate debe DEJARLE pasar → NO 403. Construir el bundle real puede
        ser pesado o fallar por entorno (logs dir / esquema), por eso toleramos
        cualquier código que NO sea 403/401 (200 con el ZIP, o 500 si el build
        falla por entorno). Lo crítico: el gate de rol no lo bloquea.
        """
        resp = await admin_client.get("/api/v1/system/diagnostic-bundle")
        assert resp.status_code not in (401, 403), (
            f"Gate sobrerestricto: admin obtuvo {resp.status_code} en "
            f"/system/diagnostic-bundle (no debía ser 401/403). "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_frontend_errors_remains_public(
        self, nonadmin_client: AsyncClient
    ):
        """
        CASO 3 (control-inverso, no sobre-gateo): POST
        /api/v1/system/frontend-errors es intencionalmente público (recibe
        errores del frontend antes incluso del login). El fix NO debe haberlo
        gateado. Un no-admin debe seguir pudiendo postear → NO 403.
        """
        resp = await nonadmin_client.post(
            "/api/v1/system/frontend-errors",
            json={"message": "boom en el frontend"},
        )
        assert resp.status_code != 403, (
            f"Sobre-gateo: /system/frontend-errors devolvió 403 — debe seguir "
            f"siendo público. Respuesta: {resp.text}"
        )
