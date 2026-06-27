"""
Regresión authz: las rutas de importación ERP exigen role='admin'.

Antes del fix, POST /api/v1/documents/{id}/erp-import y
.../erp-import/preview usaban solo Depends(get_current_user), de modo que
cualquier usuario autenticado podía crear EN MASA productos, clientes y
empleados (con NIF/DNI y salario) en el tenant desde un CSV. Eso es acción de
admin, coherente con el resto de operaciones sensibles del repo (users,
hr docs, ai_employees provision, etc.).

Ahora ambas rutas usan Depends(require_role("admin")):
  - no-admin → 403 (el gate corre ANTES de procesar el documento, así que un
    document_id inexistente vale para disparar el 403).
  - admin → NO 403 (404/422 por document_id inexistente, pero el gate deja pasar).
  - CONTROL-INVERSO: una ruta NORMAL de documentos (GET listado) sigue siendo
    accesible para no-admin → NO 403 (no se sobre-gateó el router).

Reutiliza las fixtures nonadmin_client / admin_client del patrón de
test_privesc_regression.py.
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
        name="Tenant NoAdmin ERP S.L.",
        nif="B22222222",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="nonadmin_erp@empresa.com",
        hashed_password=get_password_hash("NoAdminPass123!"),
        full_name="Usuario NoAdmin ERP",
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

class TestErpImportAuthz:

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_erp_import_apply(self, nonadmin_client: AsyncClient):
        """no-admin POST /api/v1/documents/{id}/erp-import → 403 (gate antes de procesar)."""
        doc_id = uuid4()
        resp = await nonadmin_client.post(
            f"/api/v1/documents/{doc_id}/erp-import",
            json={"target": "empleados"},
        )
        assert resp.status_code == 403, (
            f"no-admin pudo aplicar import ERP: {resp.status_code}. Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_erp_import_preview(self, nonadmin_client: AsyncClient):
        """no-admin POST .../erp-import/preview → 403."""
        doc_id = uuid4()
        resp = await nonadmin_client.post(
            f"/api/v1/documents/{doc_id}/erp-import/preview",
            json={"target": "empleados"},
        )
        assert resp.status_code == 403, (
            f"no-admin pudo previsualizar import ERP: {resp.status_code}. Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_not_forbidden_erp_import_apply(self, admin_client: AsyncClient):
        """CONTROL: admin POST .../erp-import → NO 403 (404/422 por doc inexistente, pero pasa el gate)."""
        doc_id = uuid4()
        resp = await admin_client.post(
            f"/api/v1/documents/{doc_id}/erp-import",
            json={"target": "empleados"},
        )
        assert resp.status_code != 403, (
            f"Gate sobrerestricto: admin obtuvo 403 en import ERP. Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_not_forbidden_erp_import_preview(self, admin_client: AsyncClient):
        """CONTROL: admin POST .../erp-import/preview → NO 403."""
        doc_id = uuid4()
        resp = await admin_client.post(
            f"/api/v1/documents/{doc_id}/erp-import/preview",
            json={"target": "empleados"},
        )
        assert resp.status_code != 403, (
            f"Gate sobrerestricto: admin obtuvo 403 en preview ERP. Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_can_list_documents(self, nonadmin_client: AsyncClient):
        """CONTROL-INVERSO (no sobre-gateo): no-admin GET listado de documentos → NO 403.

        Las rutas normales del router documents (list/upload/scan/download) NO se
        gatearon; solo las dos erp-import.
        """
        resp = await nonadmin_client.get("/api/v1/documents")
        assert resp.status_code != 403, (
            f"Se sobre-gateó el router: no-admin obtuvo 403 al listar documentos. "
            f"Respuesta: {resp.text}"
        )
