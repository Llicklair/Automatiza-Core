"""Tests de las tools `remember` / `recall` / `recall_all` del AIEmployee (F1.2).

Estas tools son @tool de LangChain — el grafo de código sólo las ve invocadas
por el LLM en runtime (a través de tool_registry), no hay llamadas directas
desde otros archivos. Por eso el diagnóstico GitNexus las reportó como "0
test callers": no era falso positivo del grafo, era un gap real.

Aquí cubrimos el contrato:
  - memory_enabled=False → la tool rechaza con FAIL legible (no excepción).
  - memory_enabled=True → roundtrip remember → recall → recall_all.
  - Validación de UUIDs malformados y `key` fuera de rango.
  - Upsert: la misma key actualiza el valor en lugar de duplicar fila.
"""

import json
import uuid

import pytest

from app.db.models.ai_employees import AIEmployee, EmployeeMemory


async def _seed_employee(db, tenant, *, memory_enabled: bool) -> AIEmployee:
    emp = AIEmployee(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        name="Test",
        role="QA",
        domain="custom",
        system_prompt="x",
        is_builtin=False,
        memory_enabled=memory_enabled,
    )
    db.add(emp)
    await db.commit()
    await db.refresh(emp)
    return emp


# ─── memory_enabled=False ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remember_falla_si_memory_disabled(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import remember

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=False)
    result = await remember.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "x",
        "value": "y",
    })
    assert result.startswith("FAIL")
    assert "memoria" in result.lower()


@pytest.mark.asyncio
async def test_recall_falla_si_memory_disabled(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import recall

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=False)
    result = await recall.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "x",
    })
    assert result.startswith("FAIL")


# ─── memory_enabled=True — roundtrip ────────────────────────────────────


@pytest.mark.asyncio
async def test_remember_recall_roundtrip_string(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import recall, remember

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=True)

    ok = await remember.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "preferred_greeting",
        "value": "Buenos días",
    })
    assert ok.startswith("OK")

    got = await recall.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "preferred_greeting",
    })
    assert got == "Buenos días"


@pytest.mark.asyncio
async def test_remember_recall_roundtrip_json_object(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import recall, remember

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=True)

    value = '{"client_aliases": {"acme": "Acme Industrial S.L."}}'
    await remember.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "client_book",
        "value": value,
    })

    got = await recall.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "client_book",
    })
    parsed = json.loads(got)
    assert parsed["client_aliases"]["acme"] == "Acme Industrial S.L."


@pytest.mark.asyncio
async def test_recall_not_found_devuelve_marker(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import recall

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=True)

    got = await recall.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "no_existe",
    })
    assert got == "NOT_FOUND"


@pytest.mark.asyncio
async def test_recall_all_devuelve_ordenado(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import recall_all, remember

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=True)

    for key, val in [("alfa", "1"), ("beta", "2"), ("gamma", "3")]:
        await remember.ainvoke({
            "tenant_id": str(tenant.id),
            "employee_id": str(emp.id),
            "key": key,
            "value": val,
        })

    got = await recall_all.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "limit": 10,
    })
    payload = json.loads(got)
    assert len(payload) == 3
    keys = {item["key"] for item in payload}
    assert keys == {"alfa", "beta", "gamma"}


# ─── Upsert por (employee_id, key) ──────────────────────────────────────


@pytest.mark.asyncio
async def test_remember_upsert_no_duplica(db, seed_tenant_and_user):
    import sqlalchemy as sa

    from app.agents.agent_tools.memory import recall, remember

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=True)

    await remember.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "color_favorito",
        "value": "azul",
    })
    await remember.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "color_favorito",
        "value": "rojo",
    })

    # Una sola fila
    count_q = await db.execute(
        sa.select(sa.func.count()).select_from(EmployeeMemory).where(
            EmployeeMemory.employee_id == emp.id,
            EmployeeMemory.key == "color_favorito",
        )
    )
    assert count_q.scalar_one() == 1

    got = await recall.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "color_favorito",
    })
    assert got == "rojo"


# ─── Validación de inputs ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remember_rechaza_uuid_invalido(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import remember

    tenant, _u, _t = seed_tenant_and_user
    result = await remember.ainvoke({
        "tenant_id": "no_es_uuid",
        "employee_id": str(uuid.uuid4()),
        "key": "x",
        "value": "y",
    })
    assert result.startswith("FAIL")
    assert "UUID" in result


@pytest.mark.asyncio
async def test_remember_rechaza_key_vacia(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import remember

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=True)
    result = await remember.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "",
        "value": "y",
    })
    assert result.startswith("FAIL")


@pytest.mark.asyncio
async def test_remember_rechaza_key_demasiado_larga(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import remember

    tenant, _u, _t = seed_tenant_and_user
    emp = await _seed_employee(db, tenant, memory_enabled=True)
    result = await remember.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(emp.id),
        "key": "x" * 200,
        "value": "y",
    })
    assert result.startswith("FAIL")


@pytest.mark.asyncio
async def test_remember_empleado_inexistente(db, seed_tenant_and_user):
    from app.agents.agent_tools.memory import remember

    tenant, _u, _t = seed_tenant_and_user
    result = await remember.ainvoke({
        "tenant_id": str(tenant.id),
        "employee_id": str(uuid.uuid4()),
        "key": "x",
        "value": "y",
    })
    assert result.startswith("FAIL")
    assert "no existe" in result.lower()
