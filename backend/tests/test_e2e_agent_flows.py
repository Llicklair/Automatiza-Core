"""E2E con grafo de agente real + LLM mockeado.

Ejercita la cadena completa por dominio:
  agent_node -> bind_tools -> tool_call -> ToolNode (DB) -> agent_node -> finalize

El LLM se mockea con MagicMock + AsyncMock con side_effect para devolver:
  1) AIMessage con tool_calls (selección de herramienta)
  2) AIMessage final sin tool_calls (después de la ejecución de la tool)

Verifica que el grafo sale por finalize con status='done' y agent_results
poblado.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _mock_llm_with_responses(responses: list[AIMessage]) -> MagicMock:
    """Mock LLM that yields the given AIMessages in order across ainvoke calls."""
    mock = MagicMock()
    mock.bind_tools.return_value = mock
    mock.ainvoke = AsyncMock(side_effect=responses)
    return mock


# ─────────────────────────────────────────────────────────────────────────────
#  HR
# ─────────────────────────────────────────────────────────────────────────────

class TestHRAgentE2E:
    """Agente HR -> tool list_employees -> DB -> finalize."""

    @pytest.mark.asyncio
    async def test_list_employees_flow(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        from app.agents.hr.agent import graph
        from app.db.models.hr import Employee

        tenant, _user, _token = seed_tenant_and_user

        # Seed: dos empleados del mismo tenant
        e1 = Employee(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Ana García",
            base_salary=2500.0,
            irpf_rate=18.0,
            status="active",
        )
        e2 = Employee(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Luis Pérez",
            base_salary=2200.0,
            irpf_rate=15.0,
            status="active",
        )
        db.add_all([e1, e2])
        await db.commit()

        # LLM scripted: 1) tool_call to list_employees, 2) finalize message
        tool_call_id = "call_list_emp_1"
        mock_llm = _mock_llm_with_responses([
            AIMessage(
                content="",
                tool_calls=[{
                    "id": tool_call_id,
                    "name": "list_employees",
                    "type": "tool_call",
                    "args": {"tenant_id": str(tenant.id)},
                }],
            ),
            AIMessage(content="He listado los empleados.", tool_calls=[]),
        ])

        state = {
            "messages": [],
            "agent_results": [],
            "tenant_id": str(tenant.id),
            "user_intent": "Lista los empleados activos",
            "status": "running",
        }

        with patch("app.agents.hr.agent.get_llm", return_value=mock_llm):
            result = await graph.ainvoke(state)

        # 1) ainvoke se llamó dos veces (selección de tool + respuesta final)
        assert mock_llm.ainvoke.call_count == 2

        # 2) ToolNode ejecutó list_employees contra DB y devolvió los seeds
        from langchain_core.messages import ToolMessage
        tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        assert tool_msgs, "expected a ToolMessage with the tool execution result"
        tool_payload = tool_msgs[0].content
        assert "Ana" in tool_payload and "Luis" in tool_payload, (
            f"tool output should mention the seeded employees, got: {tool_payload}"
        )

        # 3) El grafo salió por finalize: status='done' y step result final
        assert result["status"] == "done"
        assert result["agent_results"], "finalize should append a step result"


# ─────────────────────────────────────────────────────────────────────────────
#  BILLING
# ─────────────────────────────────────────────────────────────────────────────

class TestBillingAgentE2E:
    """Agente billing -> tool list_invoices -> DB -> finalize."""

    @pytest.mark.asyncio
    async def test_list_invoices_flow(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        from app.agents.billing.agent import graph
        from app.db.models.models import Client
        from app.db.models.billing import Invoice
        from datetime import datetime

        tenant, _user, _token = seed_tenant_and_user

        # Seed: cliente + factura
        client = Client(
            id=uuid4(),
            tenant_id=tenant.id,
            name="Cliente Demo S.L.",
            nif="B11111111",
            email="cliente@demo.com",
        )
        db.add(client)
        await db.flush()

        invoice = Invoice(
            id=uuid4(),
            tenant_id=tenant.id,
            client_id=client.id,
            invoice_number="2026/00042",
            date=datetime(2026, 5, 1),
            amount_base=1000.0,
            tax_amount=210.0,
            amount_total=1210.0,
            status="pending",
            invoice_type="issued",
        )
        db.add(invoice)
        await db.commit()

        tool_call_id = "call_list_inv_1"
        mock_llm = _mock_llm_with_responses([
            AIMessage(
                content="",
                tool_calls=[{
                    "id": tool_call_id,
                    "name": "list_invoices",
                    "type": "tool_call",
                    "args": {"tenant_id": str(tenant.id), "limit": 15},
                }],
            ),
            AIMessage(content="Te muestro las facturas.", tool_calls=[]),
        ])

        state = {
            "messages": [],
            "agent_results": [],
            "tenant_id": str(tenant.id),
            "user_intent": "Lista las facturas pendientes",
            "status": "running",
        }

        with patch("app.agents.billing.agent.get_llm", return_value=mock_llm):
            result = await graph.ainvoke(state)

        assert mock_llm.ainvoke.call_count == 2

        from langchain_core.messages import ToolMessage
        tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        assert tool_msgs, "expected a ToolMessage from list_invoices"
        assert "2026/00042" in tool_msgs[0].content, (
            f"tool output should include the seeded invoice number, got: {tool_msgs[0].content}"
        )

        assert result["status"] == "done"
        assert result["agent_results"]


# ─────────────────────────────────────────────────────────────────────────────
#  BANKING
# ─────────────────────────────────────────────────────────────────────────────

class TestBankingAgentE2E:
    """Agente banking -> tool check_balances -> DB -> finalize."""

    @pytest.mark.asyncio
    async def test_check_balances_flow(
        self, db: AsyncSession, seed_tenant_and_user
    ):
        from app.agents.banking.agent import graph

        tenant, _user, _token = seed_tenant_and_user

        # Sin seed bancario: la tool debe ejecutarse y devolver "sin cuentas"
        # — no asertamos sobre el contenido exacto, solo que la cadena ejecuta.

        tool_call_id = "call_balance_1"
        mock_llm = _mock_llm_with_responses([
            AIMessage(
                content="",
                tool_calls=[{
                    "id": tool_call_id,
                    "name": "check_balances",
                    "type": "tool_call",
                    "args": {"tenant_id": str(tenant.id)},
                }],
            ),
            AIMessage(content="Estos son tus saldos.", tool_calls=[]),
        ])

        state = {
            "messages": [],
            "agent_results": [],
            "tenant_id": str(tenant.id),
            "user_intent": "Cuál es el saldo de mis cuentas",
            "status": "running",
        }

        with patch("app.agents.banking.agent.get_llm", return_value=mock_llm):
            result = await graph.ainvoke(state)

        assert mock_llm.ainvoke.call_count == 2

        from langchain_core.messages import ToolMessage
        tool_msgs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        assert tool_msgs, "expected a ToolMessage from check_balances"

        assert result["status"] == "done"
        assert result["agent_results"]
