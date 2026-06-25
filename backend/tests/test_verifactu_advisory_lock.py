"""Guard del advisory lock VeriFactu (FAC.HASH — RD 1007/2023 Art. 8).

Hallazgo /forja a verificar: en `append_verifactu_record`,

    dialect_name = db.bind.dialect.name if db.bind is not None else ""
    if dialect_name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:k))"), ...)

La SOSPECHA era que en `AsyncSession` de SQLAlchemy 2.x `db.bind` es `None`,
de modo que `dialect_name` quedaba "" y el `pg_advisory_xact_lock` NUNCA se
adquiría, dejando la cadena de hash sin protección concurrente.

VEREDICTO (ver abajo): FALSO POSITIVO. Una `AsyncSession` creada con
`async_sessionmaker(engine)` (como `AsyncSessionLocal` en `app/db/base.py`)
SÍ tiene `bind` poblado (el `AsyncEngine`), luego `db.bind is not None` es True
y `dialect_name` resuelve al dialecto real. Estos tests son la regresión que
fija ese contrato: si una futura refactor rompe `db.bind`, el lock dejaría de
adquirirse silenciosamente y estos tests fallarán.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.services.billing import verifactu_chain
from app.services.billing.verifactu_chain import append_verifactu_record


def _make_invoice(tenant_id, client_id, *, invoice_number: str, importe: Decimal) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=invoice_number,
        date=datetime(2026, 5, 14, 10, 0, tzinfo=UTC),
        amount_base=importe,
        tax_amount=Decimal("0.00"),
        amount_total=importe,
    )


@pytest.mark.asyncio
class TestAdvisoryLockGuard:
    async def test_bind_no_es_none_en_la_sesion_real_del_repo(self, db):
        """DECISIVO sobre la sospecha del hallazgo.

        Si esto fallase (`db.bind is None`), el guard caería al `else ""`,
        `dialect_name` jamás sería "postgresql" y el advisory lock NUNCA se
        adquiriría en producción. Pasa → la premisa del hallazgo es falsa.
        """
        assert db.bind is not None, (
            "BUG CONFIRMADO: AsyncSession.bind es None → el guard de "
            "append_verifactu_record nunca toma pg_advisory_xact_lock"
        )
        # El mismo cálculo exacto que hace el código de producción.
        dialect_name = db.bind.dialect.name if db.bind is not None else ""
        assert dialect_name != "", "dialect_name vacío → guard inalcanzable"
        # En el conftest el dialecto es sqlite (no postgres), pero lo relevante
        # es que NO sea cadena vacía: el guard SÍ es alcanzable.
        assert dialect_name == "sqlite"

    async def test_en_postgres_se_emite_pg_advisory_xact_lock(
        self, db, seed_tenant_and_user, monkeypatch
    ):
        """Con dialecto postgresql, el lock SÍ se emite.

        Forzamos `db.bind.dialect.name == "postgresql"` y espiamos `db.execute`
        para comprobar que se ejecuta exactamente UNA sentencia
        `pg_advisory_xact_lock` por llamada, scoped al tenant. Esto prueba que
        la rama del guard funciona y NO está muerta.
        """
        tenant, _user, _token = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Acme SL")
        db.add(client)
        await db.flush()
        invoice = _make_invoice(
            tenant.id, client.id, invoice_number="A2026-0001", importe=Decimal("121.00")
        )
        db.add(invoice)
        await db.flush()

        # Hacer creer al guard que el dialecto es postgres sin tocar producción.
        monkeypatch.setattr(db.bind.dialect, "name", "postgresql")

        executed_sql: list[str] = []
        real_execute = db.execute

        async def spy_execute(statement, *args, **kwargs):
            executed_sql.append(str(statement))
            # El SQL de pg_advisory_xact_lock no corre en SQLite; lo cortamos
            # tras registrarlo para no romper el resto de la lógica del append.
            if "pg_advisory_xact_lock" in str(statement):

                class _Noop:
                    def scalar_one_or_none(self):
                        return None

                    def all(self):
                        return []

                return _Noop()
            return await real_execute(statement, *args, **kwargs)

        monkeypatch.setattr(db, "execute", spy_execute)

        record = await append_verifactu_record(
            db, invoice=invoice, nif_emisor="B99999999"
        )

        lock_calls = [s for s in executed_sql if "pg_advisory_xact_lock" in s]
        assert len(lock_calls) == 1, (
            "El advisory lock NO se adquirió pese a dialecto postgresql "
            f"(SQL emitido: {executed_sql})"
        )
        assert record is not None

    async def test_engine_de_produccion_tambien_puebla_bind(self):
        """`AsyncSessionLocal` de `app/db/base.py` (engine de producción)
        también deja `bind` poblado: el contrato no depende del conftest.
        """
        from app.db.base import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            assert session.bind is not None
            assert session.bind.dialect.name != ""
