"""
Regresión authz (IDOR intra-tenant): generación de documentos PDF HR.

Antes del fix, las 3 rutas de generación de PDF HR usaban solo
Depends(get_current_user) (sin gate de rol). Cualquier rol no-employee del
tenant (manager/accountant/user) podía pedir el finiquito/liquidación/registro
de jornada de OTRO empleado (datos laborales/económicos: salario,
indemnización, causa de baja) e incluso disparar create_settlement (escritura).

Las 4 rutas hermanas de hr_documents (upload/download/list/delete) en el mismo
fichero ya usan require_role("admin"). El fix alinea las 3 rutas PDF:

    POST /api/v1/hr/documents/finiquito/pdf
    POST /api/v1/hr/documents/liquidacion-finiquito/pdf
    POST /api/v1/hr/documents/registro-jornada/pdf

Ahora un no-admin recibe 403 (el gate corre ANTES de generar el PDF, así que no
hace falta un empleado/PDF real). El admin no queda bloqueado por el gate.
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

PDF_PATHS = [
    "/api/v1/hr/documents/finiquito/pdf",
    "/api/v1/hr/documents/liquidacion-finiquito/pdf",
    "/api/v1/hr/documents/registro-jornada/pdf",
]


# ---------------------------------------------------------------------------
# Fixtures (mismo patrón que test_privesc_regression.py)
# ---------------------------------------------------------------------------

@pytest.fixture
async def nonadmin_client(client: AsyncClient, db):
    """Cliente HTTP con token JWT de role='user' (no-admin) del mismo tenant."""
    from app.core.security import create_access_token, get_password_hash
    from app.db.models.models import Tenant, User

    tenant = Tenant(
        id=uuid4(),
        name="Tenant HR NoAdmin S.L.",
        nif="B22222222",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="hr_nonadmin@empresa.com",
        hashed_password=get_password_hash("NoAdminPass123!"),
        full_name="HR Usuario NoAdmin",
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
    """Cliente HTTP con token JWT de role='admin' (reutiliza el seed del conftest)."""
    _, _, token = seed_tenant_and_user
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ---------------------------------------------------------------------------
# Tests: el gate require_role("admin") rechaza a no-admin (403)
# ---------------------------------------------------------------------------

class TestHrPdfDocsAuthz:

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PDF_PATHS)
    async def test_nonadmin_cannot_generate_hr_pdf(
        self, nonadmin_client: AsyncClient, path: str
    ):
        """
        Un usuario role='user' que pide un PDF HR de un empleado debe obtener 403.
        El gate corre antes de cargar el empleado, así que un employee_id
        inexistente sigue dando 403 (no 404). Si se revierte el
        require_role("admin"), este test falla con AssertionError (≠ 403).
        """
        resp = await nonadmin_client.post(
            path,
            json={"employee_id": str(uuid4())},
        )
        assert resp.status_code == 403, (
            f"IDOR/authz activo: no-admin obtuvo {resp.status_code} en {path} "
            f"(esperado 403). Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", PDF_PATHS)
    async def test_admin_not_blocked_by_role_gate(
        self, admin_client: AsyncClient, path: str
    ):
        """
        CONTROL (gate selectivo): un ADMIN no debe ser rechazado por el gate de
        rol. Con un employee_id inexistente puede dar 404/422/400, pero NUNCA
        403. Si diera 403, el gate estaría sobre-restricto y rompería el uso
        legítimo.
        """
        resp = await admin_client.post(
            path,
            json={"employee_id": str(uuid4())},
        )
        assert resp.status_code != 403, (
            f"Gate sobre-restricto: admin obtuvo 403 en {path} "
            f"(no debería bloquearse). Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_can_still_list_employees(
        self, nonadmin_client: AsyncClient
    ):
        """
        CONTROL-INVERSO (no sobre-gateo): el listado de empleados
        (GET /api/v1/hr/employees) usa get_current_user, NO require_role.
        Un no-admin NO debe recibir 403 ahí: confirma que el fix solo gatea las
        3 rutas PDF y no se ha derramado al resto del router HR.
        """
        resp = await nonadmin_client.get("/api/v1/hr/employees")
        assert resp.status_code != 403, (
            f"Sobre-gateo: no-admin obtuvo 403 en GET /api/v1/hr/employees "
            f"(no debería estar gateado). Respuesta: {resp.text}"
        )
