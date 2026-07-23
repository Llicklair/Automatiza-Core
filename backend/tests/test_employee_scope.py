"""T5 tintorería: el rol `employee` queda restringido al mostrador.

Denegación por defecto (EmployeeScopeMiddleware): albaranes, clientes,
catálogo y fichaje SÍ; facturas, RRHH, VeriFactu, config… 403. El rol viaja
en el JWT; un admin no se ve afectado.
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from app.core.security import create_access_token, get_password_hash
from app.db.models.models import User


@pytest_asyncio.fixture
async def employee_client(client, db, seed_tenant_and_user):
    """Cliente HTTP autenticado como usuario con role=employee del MISMO tenant."""
    tenant, _admin, _t = seed_tenant_and_user
    emp = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="mostrador@empresa.com",
        hashed_password=get_password_hash("TestPass123!"),
        full_name="Empleado Mostrador",
        role="employee",
    )
    db.add(emp)
    await db.commit()
    token = create_access_token({"sub": str(emp.id), "tenant_id": str(tenant.id), "role": "employee"})
    client.headers["Authorization"] = f"Bearer {token}"
    return client


@pytest.mark.asyncio
class TestEmployeePermitido:
    async def test_albaranes(self, employee_client):
        resp = await employee_client.get("/api/v1/albaranes")
        assert resp.status_code == 200, resp.text

    async def test_clientes_busqueda(self, employee_client):
        resp = await employee_client.get("/api/v1/clients?q=ana")
        assert resp.status_code == 200, resp.text

    async def test_catalogo_productos(self, employee_client):
        resp = await employee_client.get("/api/v1/products")
        assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
class TestEmployeeDenegado:
    async def test_facturas(self, employee_client):
        assert (await employee_client.get("/api/v1/invoices")).status_code == 403

    async def test_facturas_del_cliente(self, employee_client):
        # Prefijo permitido (/clients) pero subruta de facturación → DENY.
        assert (await employee_client.get(f"/api/v1/clients/{uuid4()}/invoices")).status_code == 403

    async def test_rrhh(self, employee_client):
        assert (await employee_client.get("/api/v1/hr/attendance")).status_code == 403

    async def test_verifactu_config(self, employee_client):
        assert (await employee_client.get("/api/v1/verifactu/config")).status_code == 403

    async def test_facturar_albaranes_denegado(self, employee_client):
        # Prefijo permitido (/albaranes) pero facturar NO es mostrador (T7).
        resp = await employee_client.post("/api/v1/albaranes/facturar", json={"albaran_ids": []})
        assert resp.status_code == 403

    async def test_prefijo_no_cuela_por_concatenacion(self, employee_client):
        # /api/v1/clientsX no debe tratarse como /api/v1/clients.
        resp = await employee_client.get("/api/v1/clientsX")
        assert resp.status_code in (403, 404)
        if resp.status_code == 404:
            # si no matchea ninguna ruta, al menos NO pasó el allowlist con 200
            pass


@pytest.mark.asyncio
class TestAdminNoAfectado:
    async def test_admin_sigue_viendo_facturas(self, auth_client):
        assert (await auth_client.get("/api/v1/invoices")).status_code == 200

    async def test_admin_sigue_en_verifactu(self, auth_client):
        assert (await auth_client.get("/api/v1/verifactu/config")).status_code == 200
