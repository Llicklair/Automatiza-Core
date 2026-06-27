"""
Seguridad en documentos de empleado (datos sensibles: contratos/nóminas).

Dos regresiones cubiertas:

BUG 1 — IDOR intra-tenant (authz):
    Las 4 rutas de documentos de empleado usaban solo Depends(get_current_user),
    sin require_role. Cualquier rol no-admin (user/viewer) podía listar/descargar/
    borrar documentos de cualquier empleado del tenant. Ahora exigen
    require_role("admin") → un no-admin recibe 403.

BUG 2 — path traversal en el nombre guardado:
    upload_employee_document construía safe_name con el filename CRUDO del cliente
    (f"{uuid}_{filename}"); un filename como "x/../../evil.pdf" escapaba el
    directorio de uploads vía os.path.join. Ahora se sanitiza con el basename
    (pathlib.Path(filename).name) → el nombre guardado nunca contiene componentes
    de ruta.

Reutiliza fixtures del conftest (client, db, seed_tenant_and_user).
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Fixtures (patrón de test_privesc_regression.py)
# ---------------------------------------------------------------------------


@pytest.fixture
async def nonadmin_client(client: AsyncClient, db):
    """Cliente HTTP con token JWT de role='user' (no-admin)."""
    from app.core.security import create_access_token, get_password_hash
    from app.db.models.models import Tenant, User

    tenant = Tenant(
        id=uuid4(),
        name="Tenant DocSec S.L.",
        nif="B22222222",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="nonadmin-docsec@empresa.com",
        hashed_password=get_password_hash("NoAdminPass123!"),
        full_name="Usuario NoAdmin DocSec",
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
    """Cliente HTTP con token JWT de role='admin' (reutiliza seed del conftest)."""
    _, _, token = seed_tenant_and_user
    client.headers["Authorization"] = f"Bearer {token}"
    return client


# ---------------------------------------------------------------------------
# BUG 1 — AUTHZ (IDOR intra-tenant): require_role("admin") en las 4 rutas
# ---------------------------------------------------------------------------

# Path real: /api/v1 (api_router) + /hr (hr.router) + /employees/... (hr_employees)
DOCS_PATH = "/api/v1/hr/employees/{eid}/documents"


class TestEmployeeDocsAuthz:

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_list_employee_documents(
        self, nonadmin_client: AsyncClient
    ):
        """
        CASO 1 (oro): un usuario role='user' hace GET de la lista de documentos
        de un empleado. Debe obtener 403. Antes del fix devolvía 200/404 (sin gate)
        → IDOR confirmado. Si se revierte el require_role("admin"), este test falla.
        """
        eid = uuid4()
        resp = await nonadmin_client.get(DOCS_PATH.format(eid=eid))
        assert resp.status_code == 403, (
            f"IDOR activo: no-admin obtuvo {resp.status_code} al listar documentos "
            f"de empleado. Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_download_employee_document(
        self, nonadmin_client: AsyncClient
    ):
        """Un no-admin no puede descargar un documento de empleado → 403."""
        eid = uuid4()
        did = uuid4()
        resp = await nonadmin_client.get(
            f"/api/v1/hr/employees/{eid}/documents/{did}/download"
        )
        assert resp.status_code == 403, (
            f"IDOR activo en download: no-admin obtuvo {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_nonadmin_cannot_delete_employee_document(
        self, nonadmin_client: AsyncClient
    ):
        """Un no-admin no puede borrar un documento de empleado → 403."""
        eid = uuid4()
        did = uuid4()
        resp = await nonadmin_client.delete(
            f"/api/v1/hr/employees/{eid}/documents/{did}"
        )
        assert resp.status_code == 403, (
            f"IDOR activo en delete: no-admin obtuvo {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )

    @pytest.mark.asyncio
    async def test_admin_is_not_forbidden_listing_documents(
        self, admin_client: AsyncClient
    ):
        """
        CASO control: un ADMIN hace la misma GET. NO debe recibir 403.
        (200 con lista vacía, o 404 si el empleado no existe, pero NUNCA 403.)
        Verifica que el gate es selectivo y no rompe el flujo admin legítimo.
        """
        eid = uuid4()
        resp = await admin_client.get(DOCS_PATH.format(eid=eid))
        assert resp.status_code != 403, (
            f"Gate sobrerestricto: admin recibió 403 al listar documentos. "
            f"Respuesta: {resp.text}"
        )


# ---------------------------------------------------------------------------
# BUG 2 — PATH TRAVERSAL: el nombre guardado nunca contiene componentes de ruta
# ---------------------------------------------------------------------------


class TestEmployeeDocsPathTraversal:

    @pytest.mark.asyncio
    async def test_upload_strips_path_components_from_saved_name(self, db, tmp_path):
        """
        Sube un documento con filename malicioso "x/../../evil.pdf" y verifica que
        el file_path guardado en disco usa solo el basename (sin '..', '/' ni '\\')
        y termina en 'evil.pdf'. Antes del fix, el filename crudo escapaba el
        directorio de uploads vía os.path.join.

        Aísla el directorio de uploads en tmp_path para no tocar disco real del repo.
        """
        import app.services.hr._employee_docs as docs_mod
        import app.services.hr.service as hr_service
        from app.db.models.models import Employee, Tenant

        # Tenant + empleado reales (el service valida que el empleado exista).
        tenant = Tenant(id=uuid4(), name="T Traversal", nif="B33333333", plan="starter")
        db.add(tenant)
        await db.flush()
        emp = Employee(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Empleado Traversal",
            nif="12345678Z",
        )
        db.add(emp)
        await db.commit()

        # Aísla UPLOAD_DIR a tmp_path (el service lo importa desde hr_service).
        upload_root = str(tmp_path / "uploads")
        original = hr_service.UPLOAD_DIR
        hr_service.UPLOAD_DIR = upload_root
        try:
            result = await docs_mod.upload_employee_document(
                emp.id,
                "x/../../evil.pdf",
                b"fake-pdf-bytes",
                "application/pdf",
                tenant.id,
                None,
                db,
            )
        finally:
            hr_service.UPLOAD_DIR = original

        assert result is not None

        # Recupera el file_path real persistido para inspeccionar el nombre guardado.
        import os
        from uuid import UUID as _UUID

        from sqlalchemy import select

        from app.db.models.models import TenantDocument

        row = (
            await db.execute(
                select(TenantDocument).where(TenantDocument.id == _UUID(result["id"]))
            )
        ).scalar_one()

        saved_basename = os.path.basename(row.file_path)

        # El componente de nombre guardado NO debe contener separadores ni '..'.
        assert ".." not in saved_basename, f"'..' en nombre guardado: {saved_basename}"
        assert "/" not in saved_basename, f"'/' en nombre guardado: {saved_basename}"
        assert "\\" not in saved_basename, f"'\\\\' en nombre guardado: {saved_basename}"
        assert saved_basename.endswith("evil.pdf"), (
            f"El nombre guardado no termina en 'evil.pdf': {saved_basename}"
        )

        # Y el fichero debe haberse escrito DENTRO del directorio de uploads (no escapó).
        real_root = os.path.realpath(upload_root)
        real_file = os.path.realpath(row.file_path)
        assert real_file.startswith(real_root), (
            f"El fichero escapó el directorio de uploads: {real_file} no está bajo {real_root}"
        )
