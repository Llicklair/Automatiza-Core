"""Tests para el kill-switch de precondiciones (CONT.KILL)."""
import pytest
from app.services.system.preconditions import (
    REQUIRED_TABLES,
    check_invoice_preconditions,
)


@pytest.mark.asyncio
class TestPreconditions:
    async def test_check_invoice_preconditions_ok(self, db):
        """En el setup de tests todas las tablas se crean — debe pasar."""
        result = await check_invoice_preconditions(db)
        assert result["ok"] is True
        assert result["missing"] == []
        assert all(result["details"][t] is True for t in REQUIRED_TABLES)

    async def test_endpoint_get_preconditions_admin(self, auth_client):
        """B1: el endpoint requiere admin. Con auth de admin devuelve el estado."""
        resp = await auth_client.get("/api/v1/system/preconditions")
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data
        assert "details" in data
        assert "missing" in data

    async def test_endpoint_get_preconditions_requires_admin(self, client):
        """Regresión B1: sin auth el endpoint NO debe exponer el estado."""
        resp = await client.get("/api/v1/system/preconditions")
        assert resp.status_code in (401, 403), (
            f"Fuga de esquema fiscal: /system/preconditions devolvió "
            f"{resp.status_code} sin auth (debía ser 401/403)."
        )

    async def test_endpoint_get_preconditions_rejects_non_admin(self, client, db):
        """Regresión B1 (la importante): un usuario AUTENTICADO pero NO admin
        (role='user') debe recibir 403. Sin esta aserción, el fix podría
        debilitarse a `get_current_user` (cualquier logueado) y el test de
        'sin token' seguiría pasando. Aquí se exige el rol admin de verdad."""
        from uuid import uuid4

        from app.core.security import create_access_token, get_password_hash
        from app.db.models.models import Tenant, User

        tenant = Tenant(id=uuid4(), name="T NoAdmin Prec", nif="B33333333", plan="starter")
        db.add(tenant)
        await db.flush()
        user = User(
            id=uuid4(), tenant_id=tenant.id, email="user-prec@empresa.com",
            hashed_password=get_password_hash("UserPass123!"),
            full_name="Usuario Normal", role="user",
        )
        db.add(user)
        await db.commit()
        token = create_access_token(
            {"sub": str(user.id), "tenant_id": str(tenant.id), "role": "user"}
        )
        client.headers["Authorization"] = f"Bearer {token}"
        resp = await client.get("/api/v1/system/preconditions")
        assert resp.status_code == 403, (
            f"Escalada: un role='user' obtuvo {resp.status_code} en "
            f"/system/preconditions (debía ser 403)."
        )

    async def test_required_tables_esperadas(self):
        """La constante REQUIRED_TABLES debe cubrir FAC.NUM + SEC.APR (el core
        VeriFactu/SIF fue externalizado: ya no existe la tabla verifactu_chain)."""
        assert set(REQUIRED_TABLES) == {
            "invoice_series",         # FAC.NUM
            "fiscal_approval_log",    # SEC.APR
        }
