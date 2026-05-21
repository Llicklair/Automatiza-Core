"""Tests del marketplace de workflows (F3.10)."""
from uuid import uuid4

import pytest
import yaml as _yaml

from app.db.models.workflows import Workflow
from app.services.workflow_marketplace import (
    WorkflowYamlError,
    export_workflow_to_yaml,
    get_template,
    import_yaml_as_workflow,
    install_template,
    list_templates,
    seed_official_templates,
)


# ─── Seed + catálogo ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seed_official_idempotente(db, seed_tenant_and_user):
    r1 = await seed_official_templates(db)
    assert r1["created"] == r1["total_official"]
    r2 = await seed_official_templates(db)
    assert r2["created"] == 0


@pytest.mark.asyncio
async def test_list_templates_devuelve_oficiales(db, seed_tenant_and_user):
    await seed_official_templates(db)
    items = await list_templates(db)
    assert len(items) >= 3
    slugs = {t["slug"] for t in items}
    assert "gestoria-mensual" in slugs
    assert "cierre-trimestral" in slugs
    assert "recordatorios-cobros" in slugs


@pytest.mark.asyncio
async def test_list_templates_filtra_por_categoria(db, seed_tenant_and_user):
    await seed_official_templates(db)
    fiscal = await list_templates(db, category="fiscal")
    cobros = await list_templates(db, category="cobros")
    assert all(t["category"] == "fiscal" for t in fiscal)
    assert all(t["category"] == "cobros" for t in cobros)
    assert len(fiscal) >= 2
    assert len(cobros) >= 1


@pytest.mark.asyncio
async def test_get_template_devuelve_none_si_no_existe(db, seed_tenant_and_user):
    assert await get_template(db, "no-existe") is None


# ─── Install ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_install_template_crea_workflow_inactivo(db, seed_tenant_and_user):
    tenant, user, _t = seed_tenant_and_user
    await seed_official_templates(db)

    result = await install_template(
        db, tenant.id, "gestoria-mensual", created_by=user.id
    )
    assert result["workflow_id"]
    assert result["name"] == "Gestoría mensual"
    assert result["is_active"] is False

    # Verifica DB
    import sqlalchemy as sa
    res = await db.execute(sa.select(Workflow).where(Workflow.tenant_id == tenant.id))
    wfs = res.scalars().all()
    assert len(wfs) == 1
    assert wfs[0].is_active is False
    assert wfs[0].name == "Gestoría mensual"
    assert wfs[0].trigger_type == "cron"


@pytest.mark.asyncio
async def test_install_template_sufija_si_nombre_existe(db, seed_tenant_and_user):
    tenant, user, _t = seed_tenant_and_user
    await seed_official_templates(db)

    r1 = await install_template(db, tenant.id, "gestoria-mensual", created_by=user.id)
    r2 = await install_template(db, tenant.id, "gestoria-mensual", created_by=user.id)
    assert r1["name"] == "Gestoría mensual"
    assert r2["name"] == "Gestoría mensual (2)"


@pytest.mark.asyncio
async def test_install_template_incrementa_downloads(db, seed_tenant_and_user):
    tenant, user, _t = seed_tenant_and_user
    await seed_official_templates(db)

    before = await get_template(db, "gestoria-mensual")
    await install_template(db, tenant.id, "gestoria-mensual", created_by=user.id)
    after = await get_template(db, "gestoria-mensual")
    assert after["downloads_count"] == before["downloads_count"] + 1


@pytest.mark.asyncio
async def test_install_template_no_existente_da_value_error(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    with pytest.raises(ValueError):
        await install_template(db, tenant.id, "no-existe")


# ─── Export / Import YAML ──────────────────────────────────────────────


def _make_wf(tenant_id, name="Test"):
    return Workflow(
        id=uuid4(),
        tenant_id=tenant_id,
        name=name,
        description="desc",
        trigger_type="cron",
        trigger_config={"cron": "0 9 * * 1"},
        action_type="agent_sequence",
        action_config={"agents": ["billing"]},
        execution_mode="deterministic",
        compiled_steps=[{"step": "list_invoices", "agent": "billing"}],
        is_active=True,
    )


def test_export_workflow_to_yaml_parseable():
    wf = _make_wf(uuid4(), name="Cierre semanal")
    text = export_workflow_to_yaml(wf)
    parsed = _yaml.safe_load(text)
    assert parsed["name"] == "Cierre semanal"
    assert parsed["trigger_type"] == "cron"
    assert parsed["trigger_config"] == {"cron": "0 9 * * 1"}
    assert parsed["execution_mode"] == "deterministic"
    assert "tenant_id" not in parsed
    assert "id" not in parsed


@pytest.mark.asyncio
async def test_roundtrip_export_import(db, seed_tenant_and_user):
    tenant, user, _t = seed_tenant_and_user
    src = _make_wf(tenant.id, name="Roundtrip")
    yaml_str = export_workflow_to_yaml(src)
    result = await import_yaml_as_workflow(db, tenant.id, yaml_str, created_by=user.id)
    assert result["name"] == "Roundtrip"
    assert result["is_active"] is False  # imports SIEMPRE inactivos


@pytest.mark.asyncio
async def test_import_rechaza_yaml_invalido(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    with pytest.raises(WorkflowYamlError):
        await import_yaml_as_workflow(db, tenant.id, "[no es un mapping]")


@pytest.mark.asyncio
async def test_import_rechaza_falta_campo_obligatorio(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    bad = "name: Solo nombre\ntrigger_type: cron"  # falta action_type
    with pytest.raises(WorkflowYamlError) as exc:
        await import_yaml_as_workflow(db, tenant.id, bad)
    assert "action_type" in str(exc.value)


@pytest.mark.asyncio
async def test_import_rechaza_campo_extra(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    bad = (
        "name: x\ntrigger_type: cron\naction_type: agent_sequence\n"
        "campo_inventado: 123\n"
    )
    with pytest.raises(WorkflowYamlError):
        await import_yaml_as_workflow(db, tenant.id, bad)
