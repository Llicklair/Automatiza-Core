"""Tests de negocio del agente CRM.

Ejercitan la validación real de las tools (valor esperado, etapas del embudo)
antes de tocar BD, y blindan que create_opportunity y update_opportunity_stage
comparten el MISMO vocabulario de etapas (una sola fuente de verdad: VALID_STAGES).
"""
import pytest

from app.agents.crm.tools import (
    VALID_STAGES,
    create_opportunity,
    update_opportunity_stage,
)

VALID_TENANT = "00000000-0000-0000-0000-000000000001"
VALID_OPP = "00000000-0000-0000-0000-0000000000bb"


@pytest.mark.asyncio
async def test_create_opportunity_rejects_negative_value():
    out = await create_opportunity.ainvoke(
        {"tenant_id": VALID_TENANT, "client_nif": "B12345678", "title": "Lead", "expected_value": -10}
    )
    assert out.startswith("Error")
    assert "negativo" in out


@pytest.mark.asyncio
async def test_create_opportunity_rejects_non_numeric_value():
    out = await create_opportunity.ainvoke(
        {
            "tenant_id": VALID_TENANT,
            "client_nif": "B12345678",
            "title": "Lead",
            "expected_value": "mucho",
        }
    )
    assert "inválido" in out


@pytest.mark.asyncio
async def test_create_opportunity_rejects_unknown_stage():
    out = await create_opportunity.ainvoke(
        {
            "tenant_id": VALID_TENANT,
            "client_nif": "B12345678",
            "title": "Lead",
            "stage": "ganada",
        }
    )
    assert "etapa inválida" in out


@pytest.mark.asyncio
async def test_update_opportunity_stage_rejects_unknown_stage():
    out = await update_opportunity_stage.ainvoke(
        {"tenant_id": VALID_TENANT, "opportunity_id": VALID_OPP, "new_stage": "zzz"}
    )
    assert out.startswith("Error")
    assert "invalida" in out.lower()


@pytest.mark.asyncio
async def test_create_and_update_share_same_stage_vocabulary():
    """REGRESIÓN: crear y mover deben aceptar/rechazar exactamente las mismas etapas.

    Antes 'negotiation' se aceptaba al crear pero no al mover. Ahora ambas usan
    VALID_STAGES. Este test falla si alguien vuelve a divergir los vocabularios.
    """
    # 'negotiation' ya NO es válida en ninguna de las dos.
    created = await create_opportunity.ainvoke(
        {"tenant_id": VALID_TENANT, "client_nif": "B1", "title": "T", "stage": "negotiation"}
    )
    assert "etapa inválida" in created

    moved = await update_opportunity_stage.ainvoke(
        {"tenant_id": VALID_TENANT, "opportunity_id": VALID_OPP, "new_stage": "negotiation"}
    )
    assert "invalida" in moved.lower()


def test_valid_stages_matches_frontend_funnel():
    """El embudo del frontend tiene exactamente estas 5 columnas."""
    assert set(VALID_STAGES) == {"new", "qualified", "proposal", "won", "lost"}
