"""Tests para app.core.llm.mock — MockChatModel para testing."""
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.core.llm.mock import MockChatModel


class TestMockChatModelBasics:
    def test_llm_type(self):
        mock = MockChatModel()
        assert mock._llm_type == "mock"

    def test_generate_returns_chat_result(self):
        mock = MockChatModel()
        messages = [HumanMessage(content="Hola")]
        result = mock._generate(messages)
        assert len(result.generations) == 1
        assert isinstance(result.generations[0].message, AIMessage)

    @pytest.mark.asyncio
    async def test_agenerate_returns_chat_result(self):
        mock = MockChatModel()
        messages = [HumanMessage(content="Hola")]
        result = await mock._agenerate(messages)
        assert len(result.generations) == 1
        assert isinstance(result.generations[0].message, AIMessage)

    def test_invoke_returns_ai_message(self):
        mock = MockChatModel()
        result = mock.invoke([HumanMessage(content="Hola")])
        assert isinstance(result, AIMessage)

    @pytest.mark.asyncio
    async def test_ainvoke_returns_ai_message(self):
        mock = MockChatModel()
        result = await mock.ainvoke([HumanMessage(content="Hola")])
        assert isinstance(result, AIMessage)


class TestMockChatModelFallback:
    def test_fallback_generic_response(self):
        mock = MockChatModel()
        result = mock._generate([HumanMessage(content="cualquier cosa random")])
        content = result.generations[0].message.content
        data = json.loads(content)
        assert data["status"] == "ok"

    def test_tool_message_triggers_completion(self):
        mock = MockChatModel()
        messages = [
            HumanMessage(content="Haz algo"),
            ToolMessage(content="resultado de herramienta", tool_call_id="call_123"),
        ]
        result = mock._generate(messages)
        content = result.generations[0].message.content
        assert "Tarea completada" in content


class TestMockChatModelDomainDetection:
    def test_coordinator_plan(self):
        mock = MockChatModel()
        messages = [HumanMessage(content="Eres el coordinador general. steps agent instruction")]
        result = mock._generate(messages)
        content = result.generations[0].message.content
        data = json.loads(content)
        assert "steps" in data

    def test_billing_extraction(self):
        mock = MockChatModel()
        messages = [HumanMessage(content="client_name amount_base factura nueva")]
        result = mock._generate(messages)
        content = result.generations[0].message.content
        data = json.loads(content)
        assert "client_name" in data
        assert "amount_total" in data

    def test_billing_query_detection(self):
        mock = MockChatModel()
        messages = [HumanMessage(content="client_name amount_base listar pendientes")]
        result = mock._generate(messages)
        content = result.generations[0].message.content
        data = json.loads(content)
        assert data.get("is_query") is True

    def test_compliance_alerts(self):
        mock = MockChatModel()
        messages = [HumanMessage(content='"alertas" vencimientos fiscales')]
        result = mock._generate(messages)
        content = result.generations[0].message.content
        data = json.loads(content)
        assert "alertas" in data
        assert len(data["alertas"]) > 0

    def test_compliance_boe(self):
        mock = MockChatModel()
        messages = [HumanMessage(content="resumen_boe novedades del boe")]
        result = mock._generate(messages)
        content = result.generations[0].message.content
        data = json.loads(content)
        assert "resumen_boe" in data

    def test_compliance_fiscal_query(self):
        mock = MockChatModel()
        messages = [HumanMessage(content="respuesta_consulta asesor fiscal experto")]
        result = mock._generate(messages)
        content = result.generations[0].message.content
        data = json.loads(content)
        assert "respuesta_consulta" in data


class TestMockChatModelClassifyDomain:
    def test_classify_hr(self):
        mock = MockChatModel()
        result = mock._classify_domain("necesito ver las nominas de este mes")
        assert result == "hr"

    def test_classify_billing(self):
        mock = MockChatModel()
        result = mock._classify_domain("crear una factura de venta")
        assert result == "billing"

    def test_classify_crm(self):
        mock = MockChatModel()
        result = mock._classify_domain("oportunidad de negocio crm")
        assert result == "crm"

    def test_classify_compliance(self):
        mock = MockChatModel()
        result = mock._classify_domain("vencimiento fiscal iva")
        assert result == "compliance"

    def test_classify_documents(self):
        mock = MockChatModel()
        result = mock._classify_domain("escanear documento")
        assert result == "documents"

    def test_classify_email(self):
        mock = MockChatModel()
        result = mock._classify_domain("enviar correo electronico")
        assert result == "email"

    def test_classify_banking(self):
        mock = MockChatModel()
        result = mock._classify_domain("saldo del banco")
        assert result == "banking"

    def test_classify_fallback(self):
        mock = MockChatModel()
        result = mock._classify_domain("algo que no coincide con nada")
        assert result == "billing"


class TestMockChatModelMultiAgentPlan:
    def test_hr_plan(self):
        mock = MockChatModel()
        plan = json.loads(mock._multi_agent_plan("generar nominas de empleados"))
        assert any(s["agent"] == "hr" for s in plan["steps"])

    def test_billing_plan(self):
        mock = MockChatModel()
        plan = json.loads(mock._multi_agent_plan("facturas de cobro"))
        assert any(s["agent"] == "billing" for s in plan["steps"])

    def test_compliance_plan(self):
        mock = MockChatModel()
        plan = json.loads(mock._multi_agent_plan("vencimiento fiscal trimestre"))
        assert any(s["agent"] == "compliance" for s in plan["steps"])

    def test_fallback_plan(self):
        mock = MockChatModel()
        plan = json.loads(mock._multi_agent_plan("algo genérico"))
        assert len(plan["steps"]) >= 1


class TestMockChatModelBindTools:
    def test_bind_tools_returns_runnable(self):
        mock = MockChatModel()
        result = mock.bind_tools([])
        assert result is not None

    def test_with_structured_output_returns_runnable(self):
        from pydantic import BaseModel

        class FakeSchema(BaseModel):
            status: str = "ok"
            message: str = "test"

        mock = MockChatModel()
        runnable = mock.with_structured_output(FakeSchema)
        assert runnable is not None


class TestMockChatModelExtractTenantId:
    def test_extracts_uuid_from_message(self):
        mock = MockChatModel()
        test_uuid = "12345678-1234-1234-1234-123456789abc"
        messages = [HumanMessage(content=f"tenant_id: {test_uuid}")]
        result = mock._extract_tenant_id(messages)
        assert result == test_uuid

    def test_returns_default_when_no_uuid(self):
        mock = MockChatModel()
        messages = [HumanMessage(content="no uuid here")]
        result = mock._extract_tenant_id(messages)
        assert result == "00000000-0000-0000-0000-000000000000"
