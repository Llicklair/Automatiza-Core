"""Regresión: borrar una entidad con registros asociados devuelve 409, no 500.

Fija el fix de `f3b0e05` (`except IntegrityError -> rollback -> raise
ConflictError`) en `delete_client`: al intentar borrar un cliente que tiene una
factura asociada, la FK `invoices.client_id -> clients.id` impide el DELETE; el
servicio captura el `IntegrityError`, hace rollback y lanza `ConflictError`, que
el handler de `main.py` mapea a HTTP 409.

Si se revierte el fix el DELETE propagaría un 500 (o un 204 silencioso si la FK
no bloqueara), por lo que el `assert == 409` rompe. No es tautológico: afirma el
código 409 concreto.

Detalle de infraestructura: el conftest usa SQLite en memoria, donde la
verificación de claves foráneas está DESACTIVADA por defecto. Sin ella, el
borrado tendría éxito (204) y el escenario nunca se reproduciría. Por eso este
test activa `PRAGMA foreign_keys=ON` en las conexiones del engine de tests
(listener idempotente, NO toca producción) para que la FK se respete igual que
en PostgreSQL.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import event, text

from tests.conftest import _test_engine


@pytest_asyncio.fixture
async def enforce_sqlite_foreign_keys():
    """Activa la verificación de FK en SQLite (apagada por defecto).

    PostgreSQL (producción) siempre la respeta; SQLite no, salvo PRAGMA. Sin
    esto el DELETE tendría éxito y el conflicto nunca se daría, invalidando la
    regresión.

    NO se hace ``dispose()``: el engine usa StaticPool sobre una BD en memoria
    (una sola conexión compartida que contiene el esquema creado por
    ``setup_db``). Recrearla borraría las tablas. En su lugar fijamos el PRAGMA
    sobre la conexión viva y registramos un listener para futuras conexiones.
    """
    sync_engine = _test_engine.sync_engine

    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    event.listen(sync_engine, "connect", _set_sqlite_pragma)
    # Aplicar el PRAGMA a la conexión ya abierta del StaticPool sin recrearla.
    async with _test_engine.begin() as conn:
        await conn.execute(text("PRAGMA foreign_keys=ON"))
    try:
        yield
    finally:
        event.remove(sync_engine, "connect", _set_sqlite_pragma)
        # Restaurar el estado por defecto (FK OFF) en la conexión compartida del
        # StaticPool. Sin esto, la verificación de FK quedaría ACTIVADA para el
        # resto de la suite (una sola conexión compartida) y rompería los tests
        # posteriores que insertan filas con FKs "de atajo" (caps, ledger, audit…).
        async with _test_engine.begin() as conn:
            await conn.execute(text("PRAGMA foreign_keys=OFF"))


class TestDeleteClientConflict409:
    @pytest.mark.asyncio
    async def test_delete_client_with_invoice_returns_409(
        self, auth_client: AsyncClient, enforce_sqlite_foreign_keys, db, seed_tenant_and_user
    ):
        tenant, _user, _token = seed_tenant_and_user

        # 1) Crear cliente vía API.
        create = await auth_client.post(
            "/api/v1/clients", json={"name": "Cliente Con Factura"}
        )
        assert create.status_code == 201, create.text
        client_id = create.json()["id"]

        # 2) Crear una factura asociada a ese cliente a nivel ORM (la creación
        #    por API arrastra numeración/VeriFactu; el ORM aísla la regresión).
        from app.db.models.billing import Invoice

        invoice = Invoice(
            id=uuid4(),
            tenant_id=tenant.id,
            client_id=UUID(client_id),
            date=datetime.now(timezone.utc),
            amount_total=Decimal("121.00"),
            status="draft",
        )
        db.add(invoice)
        await db.commit()

        # 3) Borrar el cliente -> debe devolver 409 (no 500, no 204).
        resp = await auth_client.delete(f"/api/v1/clients/{client_id}")
        assert resp.status_code == 409, (
            f"esperado 409 (ConflictError por FK), recibido {resp.status_code}: {resp.text}"
        )

        # El cliente sigue existiendo (el borrado se revirtió).
        listed = await auth_client.get("/api/v1/clients")
        assert any(c["id"] == client_id for c in listed.json())

    @pytest.mark.asyncio
    async def test_delete_client_without_invoice_still_204(
        self, auth_client: AsyncClient, enforce_sqlite_foreign_keys
    ):
        """Control: sin factura asociada el borrado sigue siendo 204.

        Garantiza que el 409 anterior viene de la FK y no de que el endpoint
        siempre falle (descarta falso positivo).
        """
        create = await auth_client.post("/api/v1/clients", json={"name": "Sin Factura"})
        client_id = create.json()["id"]
        resp = await auth_client.delete(f"/api/v1/clients/{client_id}")
        assert resp.status_code == 204, resp.text
