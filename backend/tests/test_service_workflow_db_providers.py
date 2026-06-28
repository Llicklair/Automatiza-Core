"""Tests para app.services.workflow.db_query_providers y db_conditions.

Estos módulos resuelven hojas de condiciones de workflow contra la BD
(p.ej. "ejecutar workflow si pending_invoice_count > 10"). Sin cobertura
previa, eran un riesgo silencioso para automatizaciones programadas.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from app.db.models.models import Employee, Invoice, Payroll, Tenant
from app.services.workflow.db_conditions import (
    _collect_provider_leaves,
    resolve_db_conditions,
)
from app.services.workflow.db_query_providers import QUERY_PROVIDERS


@pytest.fixture
async def _tenant(db):
    t = Tenant(
        id=uuid4(),
        name="Test Providers",
        nif=f"P{uuid4().int % 10**8:08d}",
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


def _utcnow():
    return datetime.now(timezone.utc)


# ── _collect_provider_leaves ─────────────────────────────────────────────────


class TestCollectProviderLeaves:
    def test_none_devuelve_vacio(self):
        assert _collect_provider_leaves(None) == []

    def test_arbol_vacio_devuelve_vacio(self):
        assert _collect_provider_leaves({}) == []

    def test_hoja_provider_se_recoge(self):
        cond = {"provider": "billing.unpaid_total", "op": "gt", "value": 100}
        leaves = _collect_provider_leaves(cond)
        assert leaves == [cond]

    def test_hoja_sin_provider_no_se_recoge(self):
        cond = {"field": "x", "op": "gt", "value": 1}
        leaves = _collect_provider_leaves(cond)
        assert leaves == []

    def test_arbol_AND_recoge_hijos(self):
        a = {"provider": "a.b", "op": "gt", "value": 1}
        b = {"provider": "c.d", "op": "lt", "value": 5}
        tree = {"operator": "AND", "conditions": [a, b]}
        leaves = _collect_provider_leaves(tree)
        assert leaves == [a, b]

    def test_arbol_OR_recoge_hijos(self):
        a = {"provider": "x.y", "op": "eq", "value": 1}
        tree = {"operator": "OR", "conditions": [a]}
        assert _collect_provider_leaves(tree) == [a]

    def test_NOT_recoge_hijo_anidado(self):
        a = {"provider": "z.w", "op": "eq", "value": 0}
        tree = {"operator": "NOT", "condition": a}
        assert _collect_provider_leaves(tree) == [a]

    def test_arbol_mixto_AND_NOT(self):
        a = {"provider": "p.a", "op": "gt", "value": 1}
        b = {"provider": "p.b", "op": "lt", "value": 5}
        c = {"field": "no_db", "op": "eq", "value": "x"}
        tree = {
            "operator": "AND",
            "conditions": [
                a,
                {"operator": "NOT", "condition": b},
                c,  # se ignora (sin provider)
            ],
        }
        assert _collect_provider_leaves(tree) == [a, b]


# ── resolve_db_conditions ────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestResolveDbConditions:
    async def test_sin_hojas_provider_devuelve_contexto_intacto(self, db, _tenant):
        ctx = {"time": "now"}
        result = await resolve_db_conditions(None, _tenant.id, db, ctx)
        assert result == {"time": "now"}

        cond_sin_provider = {"field": "x", "op": "eq", "value": 1}
        result = await resolve_db_conditions(cond_sin_provider, _tenant.id, db, ctx)
        # No se añadió "db" al contexto
        assert "db" not in result

    async def test_provider_se_resuelve_y_se_inyecta_en_db_ctx(self, db, _tenant):
        # Sin facturas pending → count=0
        ctx = {}
        cond = {"provider": "billing.pending_invoice_count", "op": "gt", "value": 0}
        result = await resolve_db_conditions(cond, _tenant.id, db, ctx)
        assert "db" in result
        assert result["db"]["billing"]["pending_invoice_count"] == 0
        # La hoja queda enriquecida con field
        assert cond["field"] == "db.billing.pending_invoice_count"

    async def test_provider_desconocido_no_rompe(self, db, _tenant):
        cond = {"provider": "no.existe", "op": "eq", "value": 1}
        ctx = {}
        result = await resolve_db_conditions(cond, _tenant.id, db, ctx)
        # No crashea; el provider desconocido queda con field pero sin valor en db_ctx
        assert cond["field"] == "db.no.existe"
        # db_ctx existe pero sin la clave
        assert result["db"] == {}

    async def test_provider_que_lanza_excepcion_devuelve_None(self, db, _tenant, monkeypatch):
        """Provider que crashea no debe romper la evaluación del workflow."""

        async def _broken(tenant_id, db, params):
            raise RuntimeError("simulated DB error")

        monkeypatch.setitem(QUERY_PROVIDERS, "test.broken", _broken)

        cond = {"provider": "test.broken", "op": "eq", "value": 0}
        ctx = {}
        result = await resolve_db_conditions(cond, _tenant.id, db, ctx)
        # El provider crasheó → valor None, pero el workflow no rompe
        assert result["db"]["test"]["broken"] is None


# ── QUERY_PROVIDERS — billing ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestBillingProviders:
    async def _make_invoices(self, db, tenant_id, items):
        """items: lista de tuplas (status, amount, due_offset_days)."""
        from app.db.models.models import Client

        client = Client(
            tenant_id=tenant_id,
            name=f"Cli-{uuid4().hex[:6]}",
            nif=f"C{uuid4().int % 10**8:08d}",
        )
        db.add(client)
        await db.commit()
        for i, (status, amount, due_offset) in enumerate(items):
            inv = Invoice(
                tenant_id=tenant_id,
                client_id=client.id,
                invoice_number=f"F-{uuid4().hex[:6]}-{i}",
                date=_utcnow(),
                due_date=_utcnow() + timedelta(days=due_offset),
                amount_base=Decimal(str(amount)),
                tax_amount=Decimal("0"),
                amount_total=Decimal(str(amount)),
                status=status,
            )
            db.add(inv)
        await db.commit()

    async def test_pending_invoice_count(self, db, _tenant):
        await self._make_invoices(
            db, _tenant.id,
            [("pending", 100, 30), ("pending", 50, 30), ("paid", 200, 0)],
        )
        fn = QUERY_PROVIDERS["billing.pending_invoice_count"]
        assert await fn(_tenant.id, db, {"status": "pending"}) == 2
        # Default status también es "pending"
        assert await fn(_tenant.id, db, {}) == 2

    async def test_unpaid_total(self, db, _tenant):
        await self._make_invoices(
            db, _tenant.id,
            [("pending", 100, 30), ("sent", 250, 30), ("paid", 999, 0)],
        )
        fn = QUERY_PROVIDERS["billing.unpaid_total"]
        # 100 + 250 = 350 (paid se excluye)
        assert await fn(_tenant.id, db, {}) == 350.0

    async def test_overdue_count(self, db, _tenant):
        await self._make_invoices(
            db, _tenant.id,
            [
                ("pending", 100, -5),   # vencida (due hace 5 días)
                ("pending", 50, -1),    # vencida
                ("pending", 200, 10),   # NO vencida
                ("paid", 999, -100),    # vencida pero pagada → no cuenta
            ],
        )
        fn = QUERY_PROVIDERS["billing.overdue_count"]
        assert await fn(_tenant.id, db, {}) == 2

    async def test_aislamiento_por_tenant(self, db, _tenant):
        other = Tenant(
            id=uuid4(), name="Other", nif=f"O{uuid4().int % 10**8:08d}"
        )
        db.add(other)
        await db.commit()
        await self._make_invoices(
            db, _tenant.id, [("pending", 100, 30)]
        )
        await self._make_invoices(
            db, other.id, [("pending", 999, 30), ("pending", 555, 30)]
        )
        fn = QUERY_PROVIDERS["billing.pending_invoice_count"]
        # Cada tenant ve solo lo suyo
        assert await fn(_tenant.id, db, {}) == 1
        assert await fn(other.id, db, {}) == 2


# ── QUERY_PROVIDERS — hr ─────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestHrProviders:
    async def _make_employees(self, db, tenant_id, n):
        for i in range(n):
            db.add(Employee(
                tenant_id=tenant_id,
                name=f"Emp {i}",
                nif=f"E{uuid4().int % 10**8:08d}",
                role="dev",
                department="eng",
                base_salary=Decimal("2500"),
                status="active",
            ))
        await db.commit()

    async def _make_payrolls(self, db, tenant_id, employees_count, statuses):
        emps = []
        # Un empleado por nómina: la UNIQUE (tenant, employee, period_start) impide
        # varias nóminas del mismo empleado en el mismo período (mismo mes aquí).
        for i in range(max(employees_count, len(statuses))):
            e = Employee(
                tenant_id=tenant_id,
                name=f"PEmp {i}",
                nif=f"PE{uuid4().int % 10**6:06d}",
                role="dev",
                department="eng",
                base_salary=Decimal("2500"),
                status="active",
            )
            db.add(e)
            emps.append(e)
        await db.commit()

        for i, status in enumerate(statuses):
            db.add(Payroll(
                tenant_id=tenant_id,
                employee_id=emps[i].id,
                period_start=_utcnow().replace(day=1),
                period_end=_utcnow(),
                issue_date=_utcnow(),
                base_salary=Decimal("2500"),
                net_salary=Decimal("1940"),
                status=status,
            ))
        await db.commit()

    async def test_employee_count(self, db, _tenant):
        await self._make_employees(db, _tenant.id, 3)
        fn = QUERY_PROVIDERS["hr.employee_count"]
        assert await fn(_tenant.id, db, {}) == 3

    async def test_draft_payroll_count(self, db, _tenant):
        await self._make_payrolls(db, _tenant.id, 2, ["draft", "draft", "approved"])
        fn = QUERY_PROVIDERS["hr.draft_payroll_count"]
        assert await fn(_tenant.id, db, {}) == 2

    async def test_payrolls_this_month(self, db, _tenant):
        await self._make_payrolls(db, _tenant.id, 1, ["draft", "approved"])
        fn = QUERY_PROVIDERS["hr.payrolls_this_month"]
        # Las dos creadas este mes
        assert await fn(_tenant.id, db, {}) == 2


# ── Registry integrity ───────────────────────────────────────────────────────


class TestRegistryIntegrity:
    def test_todos_los_providers_son_callables(self):
        for key, fn in QUERY_PROVIDERS.items():
            assert callable(fn), f"{key} no es callable"

    def test_no_hay_keys_duplicadas(self):
        # Asegura que el dict no tiene duplicados conceptuales
        assert len(QUERY_PROVIDERS) >= 6
        # Estructura dominio.nombre
        for key in QUERY_PROVIDERS:
            assert "." in key, f"{key} debe tener formato dominio.nombre"
