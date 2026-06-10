"""Guard de contrato en `_resolve_custom_employee`.

Un AIEmployee custom 'Perfil' (0-1 de las 4 capacidades del contrato) mencionado
de pasada NO debe interceptar el routing de un dominio builtin — eso provocaba un
dispatch custom lento (timeout 180s, p.ej. 'Alicja Wiszczulis'). Solo los
empleados 'de verdad' (>=2 capacidades) interceptan.
"""
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


def _emp(scope=None, mem=False, know=False, wf=None):
    m = MagicMock()
    m.scope = scope
    m.memory_enabled = mem
    m.knowledge_enabled = know
    m.workflows = wf
    return m


def test_meets_contract_cuenta_capacidades():
    from app.agents.orchestrator.classifier import _meets_employee_contract

    assert _meets_employee_contract(_emp()) is False                         # 0
    assert _meets_employee_contract(_emp(mem=True)) is False                  # 1
    assert _meets_employee_contract(_emp(mem=True, know=True)) is True        # 2
    assert _meets_employee_contract(_emp(scope={"a": 1}, wf=[{"b": 2}])) is True  # 2


class TestResolveCustomContract:
    @pytest.mark.asyncio
    async def test_perfil_no_intercepta(self, db: AsyncSession, seed_tenant_and_user):
        from app.agents.orchestrator.classifier import _resolve_custom_employee
        from app.db.models.ai_employees import AIEmployee

        tenant, _u, _t = seed_tenant_and_user
        perfil = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="Alicja Perfil",
            role="Auditora Interna", domain="compliance", is_builtin=False,
            status="idle", system_prompt="Soy auditora.", icon="x", avatar_color="#fff",
            scope=None, memory_enabled=False, knowledge_enabled=False, workflows=None,
        )
        db.add(perfil)
        await db.commit()

        state = {"tenant_id": str(tenant.id), "additional_metadata": {}}
        res = await _resolve_custom_employee(state, "necesito una auditora interna para el cierre")
        assert res is None  # Perfil no secuestra el routing

    @pytest.mark.asyncio
    async def test_empleado_real_si_intercepta(self, db: AsyncSession, seed_tenant_and_user):
        from app.agents.orchestrator.classifier import _resolve_custom_employee
        from app.db.models.ai_employees import AIEmployee

        tenant, _u, _t = seed_tenant_and_user
        real = AIEmployee(
            id=uuid4(), tenant_id=tenant.id, name="Berta Real",
            role="Controller", domain="compliance", is_builtin=False,
            status="idle", system_prompt="Soy controller.", icon="x", avatar_color="#fff",
            memory_enabled=True, knowledge_enabled=True,  # 2 capacidades
        )
        db.add(real)
        await db.commit()

        state = {"tenant_id": str(tenant.id), "additional_metadata": {}}
        res = await _resolve_custom_employee(state, "que opina berta del cierre")
        assert res is not None
        assert res.get("addressed_employee_id") == str(real.id)

    @pytest.mark.asyncio
    async def test_seleccion_explicita_se_respeta_aunque_sea_perfil(self, db, seed_tenant_and_user):
        # Si el usuario lo eligió en la UI (addressed_employee_id), se respeta
        # aunque sea Perfil — la elección explícita manda sobre el contrato.
        from app.agents.orchestrator.classifier import _resolve_custom_employee

        tenant, _u, _t = seed_tenant_and_user
        state = {"tenant_id": str(tenant.id), "additional_metadata": {"addressed_employee_id": "abc-123"}}
        res = await _resolve_custom_employee(state, "haz lo que sea")
        assert res is not None and res.get("addressed_employee_id") == "abc-123"
