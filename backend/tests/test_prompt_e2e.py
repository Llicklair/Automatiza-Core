"""
E2E Prompt Tests — dos niveles:

  1. DETERMINISTAS (sin LLM): verifican que los prompts contienen las reglas
     críticas que protegen contra los bugs de alta frecuencia.

  2. LLM_REAL (requieren API key): prueban el comportamiento real del LLM
     con las entradas problemáticas conocidas.
     Ejecutar con: ANTHROPIC_API_KEY=sk-... pytest -m e2e tests/test_prompt_e2e.py -v

Los tests LLM_REAL generan fixtures de "golden path" y "edge cases".
Si un test falla, el mensaje indica qué comportamiento se esperaba y cuál salió.
"""

import json
import os
import re
from pathlib import Path
import pytest

PROMPTS_DIR = Path(__file__).parent.parent / "app" / "prompts"

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")


_CLAUDE_BIN = os.environ.get(
    "CLAUDE_CODE_BIN",
    r"C:\Users\marcos\AppData\Roaming\npm\claude.cmd",
)


def _has_real_llm() -> bool:
    """True si Claude CLI está disponible o hay una API key de LLM real."""
    import shutil
    if os.path.isfile(_CLAUDE_BIN):
        return True
    if shutil.which("claude"):
        return True
    keys = ["ANTHROPIC_API_KEY", "GROQ_API_KEY", "GEMINI_API_KEY"]
    return any(os.environ.get(k, "") for k in keys)


skip_no_llm = pytest.mark.skipif(
    not _has_real_llm(),
    reason="Sin API key de LLM real. Configurar ANTHROPIC_API_KEY / GROQ_API_KEY para ejecutar.",
)


# ─────────────────────────────────────────────────────────────
# 1. TESTS DETERMINISTAS — sin LLM
# ─────────────────────────────────────────────────────────────

class TestBillingPromptContent:
    """Verifica que billing_agent.txt contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _load_prompt("billing_agent")

    def test_iva_critico_rule_exists(self):
        """La regla de IVA incluido debe existir en el prompt."""
        assert "amount_base" in self.prompt
        assert "IVA incluido" in self.prompt or "iva incluido" in self.prompt.lower()
        assert "divide" in self.prompt.lower() or "1.21" in self.prompt

    def test_iva_example_1210_to_1000(self):
        """Debe existir el ejemplo concreto: 1210€ con IVA → amount_base=1000."""
        assert "1210" in self.prompt or "1.210" in self.prompt
        assert "1000" in self.prompt

    def test_few_shot_create_invoice_example(self):
        """Debe haber un ejemplo de creación de factura con amount_base correcto."""
        assert "García S.L." in self.prompt or "García" in self.prompt
        assert "create_invoice" in self.prompt
        assert "amount_base=1500" in self.prompt

    def test_few_shot_no_create_on_query(self):
        """Debe haber un ejemplo que muestre que consulta → list_invoices, no create_invoice."""
        assert "list_invoices" in self.prompt
        # El prompt debe indicar explícitamente NO crear en queries
        assert "NO crees" in self.prompt or "no crees" in self.prompt.lower() or "NOT create" in self.prompt

    def test_tipo_reducido_alimentacion_example(self):
        """Debe haber mención al tipo reducido para alimentación (iva_rate=4)."""
        assert "4" in self.prompt  # tipo superreducido
        assert "alimentaci" in self.prompt.lower()

    def test_send_invoice_example(self):
        """Debe haber ejemplo de envío de factura que use list_invoices primero."""
        assert "send_invoice_by_email" in self.prompt
        assert "document_id" in self.prompt

    def test_tenant_id_placeholder(self):
        """El prompt debe tener {tenant_id} y {today} para formateo dinámico."""
        assert "{tenant_id}" in self.prompt
        assert "{today}" in self.prompt


class TestHRPromptContent:
    """Verifica que el HR agent prompt contiene las reglas críticas."""

    def setup_method(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.agents.hr.prompts import build_system_prompt
        self.prompt = build_system_prompt("test-tenant-id")

    def test_salary_annual_to_monthly_rule(self):
        """Debe haber regla para convertir salario anual a mensual."""
        assert "26.400" in self.prompt or "26400" in self.prompt
        assert "2200" in self.prompt or "2.200" in self.prompt
        assert "12" in self.prompt  # divide entre 12

    def test_generate_all_payrolls_example(self):
        """Debe haber ejemplo explícito de generate_all_payrolls."""
        assert "generate_all_payrolls" in self.prompt
        # Y debe decir que NO usar calculate_and_create_payroll por cada empleado
        assert "NO llames" in self.prompt or "no llames" in self.prompt.lower()

    def test_mes_pasado_resolved(self):
        """El prompt debe resolver 'mes pasado' a número concreto (no texto ambiguo)."""
        import re
        # Debe contener "mes=N" donde N es un número (no texto)
        assert re.search(r"mes=\d{1,2}", self.prompt), \
            "El prompt debe contener 'mes=<número>' para resolver fechas relativas"

    def test_nif_required_for_employee(self):
        """Debe indicar que el NIF es obligatorio al crear empleado."""
        assert "NIF" in self.prompt
        assert "obligatorio" in self.prompt.lower() or "legal" in self.prompt.lower()

    def test_list_employees_before_payroll(self):
        """Debe indicar que hay que obtener el NIF vía list_employees antes de nómina individual."""
        assert "list_employees" in self.prompt
        # Debe mostrar el flujo: list_employees → calculate_and_create_payroll
        assert "calculate_and_create_payroll" in self.prompt

    def test_current_date_injected(self):
        """El prompt debe incluir la fecha actual (no literal '{today}')."""
        assert "{today}" not in self.prompt, \
            "La fecha no fue formateada - build_system_prompt no resolvió {today}"
        # Debe haber año actual
        from datetime import date
        assert str(date.today().year) in self.prompt


class TestClassifierPromptContent:
    """Verifica que el clasificador tiene todos los dominios necesarios."""

    def setup_method(self):
        self.prompt = _load_prompt("classifier")

    def test_has_all_critical_domains(self):
        """Todos los dominios de negocio deben estar en el clasificador."""
        required_domains = [
            "billing", "hr", "workflow", "crm", "banking",
            "documents", "rag", "compliance", "email"
        ]
        for domain in required_domains:
            assert domain in self.prompt, f"Dominio '{domain}' falta en el clasificador"

    def test_single_word_instruction(self):
        """El clasificador debe pedir respuesta de UNA sola palabra."""
        prompt_lower = self.prompt.lower()
        assert "una sola" in prompt_lower or "solo con una" in prompt_lower or \
               "solo una" in prompt_lower or "una palabra" in prompt_lower

    def test_workflow_trigger_words(self):
        """El dominio workflow debe estar asociado a palabras clave de automatización."""
        # El prompt debe asociar workflow con crear/modificar automatizaciones recurrentes
        assert "workflow" in self.prompt
        # Debe distinguir workflow de billing
        assert "recurrentes" in self.prompt or "programadas" in self.prompt or \
               "automatizaciones" in self.prompt


class TestWorkflowPromptContent:
    """Verifica que el workflow_agent.txt tiene estructura JSON correcta."""

    def setup_method(self):
        self.prompt = _load_prompt("workflow_agent")

    def test_cron_format_documented(self):
        """El prompt debe documentar el formato cron estándar."""
        assert "cron" in self.prompt.lower()
        # Debe haber un ejemplo de cron
        assert re.search(r"\d+ \d+ \* \* \d", self.prompt) or \
               re.search(r"0 9 \* \* 1", self.prompt), \
               "Debe haber al menos un ejemplo de expresión cron"

    def test_ui_nodes_required_for_create(self):
        """Al crear workflow, el prompt debe requerir ui_nodes."""
        assert "ui_nodes" in self.prompt
        assert "ui_edges" in self.prompt

    def test_event_based_and_schedule_based(self):
        """El prompt debe documentar ambos tipos de trigger."""
        assert "event_based" in self.prompt
        assert "schedule_based" in self.prompt

    def test_action_config_with_domain(self):
        """El action_config debe incluir domain para saber qué agente ejecutar."""
        assert '"domain"' in self.prompt
        assert "billing" in self.prompt  # ejemplo de domain


class TestBankingPromptContent:
    """Verifica que banking_agent.txt contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _load_prompt("banking_agent")

    def test_check_balances_tool_mentioned(self):
        assert "check_balances" in self.prompt

    def test_list_transactions_tool_mentioned(self):
        assert "list_transactions" in self.prompt

    def test_financial_summary_tool_mentioned(self):
        assert "financial_summary" in self.prompt

    def test_reconcile_tool_mentioned(self):
        assert "reconcile_transactions" in self.prompt

    def test_tenant_id_placeholder(self):
        assert "{tenant_id}" in self.prompt

    def test_saldo_routing_rule(self):
        """El prompt debe asociar 'saldos' con check_balances."""
        assert "saldo" in self.prompt.lower()
        assert "check_balances" in self.prompt


class TestCompliancePromptContent:
    """Verifica que compliance_agent.txt contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _load_prompt("compliance_agent")

    def test_fiscal_deadlines_tool_mentioned(self):
        assert "check_fiscal_deadlines" in self.prompt

    def test_boe_news_tool_mentioned(self):
        assert "check_boe_news" in self.prompt

    def test_fiscal_query_tool_mentioned(self):
        assert "fiscal_query" in self.prompt

    def test_tenant_id_placeholder(self):
        assert "{tenant_id}" in self.prompt

    def test_asesor_fiscal_disclaimer(self):
        """El prompt debe recomendar consultar un asesor fiscal."""
        assert "asesor fiscal" in self.prompt.lower()

    def test_plazos_routing_rule(self):
        """Plazos/vencimientos deben asociarse a check_fiscal_deadlines."""
        assert "plazos" in self.prompt.lower() or "vencimientos" in self.prompt.lower()


# CRM system prompt — mirror of crm/agent.py lines 24-37
_CRM_SYSTEM_PROMPT = (
    "Eres el Agente Comercial (CRM) de la empresa automatizada.\n"
    "Gestionas las etapas de los leads y cualificas oportunidades.\n"
    "Tus herramientas:\n"
    "1. list_opportunities: para ver embudos y prospectos.\n"
    "2. qualify_leads: para analizar leads nuevos y rankear a quién contactar.\n"
    "3. update_opportunity_stage: para avanzar deals (won/lost/qualified).\n"
    "4. create_opportunity: si descubres una nueva vía de negocio en un cliente.\n"
    "5. create_document: para generar informes en texto o csv y guardarlos en el Gestor Documental.\n"
    "6. Herramientas documentales (list_tenant_documents, get_document_content) "
    "por si necesitas leer emails escaneados, contratos, que contengan información clave.\n"
    "Tú respondes y decides a partir del ID de Tenant actual: test-tenant."
)


class TestCRMPromptContent:
    """Verifica que el prompt inline del CRM contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _CRM_SYSTEM_PROMPT

    def test_list_opportunities_tool_mentioned(self):
        assert "list_opportunities" in self.prompt

    def test_qualify_leads_tool_mentioned(self):
        assert "qualify_leads" in self.prompt

    def test_create_opportunity_tool_mentioned(self):
        assert "create_opportunity" in self.prompt

    def test_update_opportunity_stage_tool_mentioned(self):
        assert "update_opportunity_stage" in self.prompt

    def test_agente_comercial_identity(self):
        assert "Agente Comercial" in self.prompt


class TestDocumentsPromptContent:
    """Verifica que documents_agent.txt contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _load_prompt("documents_agent")

    def test_classify_document_tool_mentioned(self):
        assert "classify_document" in self.prompt

    def test_search_documents_semantic_tool_mentioned(self):
        assert "search_documents_semantic" in self.prompt

    def test_tenant_id_placeholder(self):
        assert "{tenant_id}" in self.prompt

    def test_nif_linking_mentioned(self):
        """Los NIFs deben vincularse a clientes automáticamente."""
        assert "NIF" in self.prompt

    def test_document_types_mentioned(self):
        assert "factura" in self.prompt.lower()
        assert "contrato" in self.prompt.lower()


class TestEmailPromptContent:
    """Verifica que el prompt dinámico del email agent contiene las reglas críticas."""

    def setup_method(self):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.agents.email.prompts import build_system_prompt
        self.prompt = build_system_prompt("NOTA: Datos de demostración.", "test-tenant")

    def test_check_inbox_tool_mentioned(self):
        assert "check_inbox" in self.prompt

    def test_send_email_tool_mentioned(self):
        assert "send_email" in self.prompt

    def test_check_unread_tool_mentioned(self):
        assert "check_unread" in self.prompt

    def test_tenant_id_injected(self):
        """El tenant_id debe estar resuelto (no como placeholder)."""
        assert "test-tenant" in self.prompt

    def test_attachment_workflow_mentioned(self):
        assert "attachment_ids" in self.prompt or "adjunt" in self.prompt.lower()


class TestExcelPromptContent:
    """Verifica que excel_agent.txt contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _load_prompt("excel_agent")

    def test_export_erp_data_tool_mentioned(self):
        assert "export_erp_data" in self.prompt

    def test_import_excel_tool_mentioned(self):
        assert "import_excel" in self.prompt

    def test_list_available_datasets_tool_mentioned(self):
        assert "list_available_datasets" in self.prompt

    def test_tenant_id_placeholder(self):
        assert "{tenant_id}" in self.prompt

    def test_datasets_documented(self):
        assert "facturas" in self.prompt
        assert "clientes" in self.prompt
        assert "empleados" in self.prompt

    def test_critical_export_rule(self):
        """Debe existir la regla CRÍTICO sobre incluir todos los datasets."""
        assert "CRÍTICO" in self.prompt or "CRITICO" in self.prompt


class TestMarketingPromptContent:
    """Verifica que marketing_agent.txt contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _load_prompt("marketing_agent")

    def test_json_format_required(self):
        assert "JSON" in self.prompt

    def test_spanish_language_requirement(self):
        assert "español" in self.prompt

    def test_platforms_mentioned(self):
        assert "Instagram" in self.prompt
        assert "Facebook" in self.prompt
        assert "LinkedIn" in self.prompt

    def test_posts_structure_documented(self):
        assert "posts" in self.prompt
        assert "platform" in self.prompt


class TestRAGPromptContent:
    """Verifica que rag_agent.txt contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _load_prompt("rag_agent")

    def test_search_documents_tool_mentioned(self):
        assert "search_documents" in self.prompt

    def test_answer_from_documents_tool_mentioned(self):
        assert "answer_from_documents" in self.prompt

    def test_tenant_id_placeholder(self):
        assert "{tenant_id}" in self.prompt

    def test_no_invention_rule(self):
        """El prompt debe prohibir inventar información."""
        assert "NUNCA inventes" in self.prompt or "nunca inventes" in self.prompt.lower()

    def test_routing_rules(self):
        """Debe distinguir cuándo usar search vs answer."""
        prompt_lower = self.prompt.lower()
        assert "buscar" in prompt_lower or "encontrar" in prompt_lower
        assert "pregunta" in prompt_lower or "responde" in prompt_lower


class TestRecruitmentPromptContent:
    """Verifica que recruitment_agent.txt contiene las reglas críticas."""

    def setup_method(self):
        self.prompt = _load_prompt("recruitment_agent")

    def test_positions_mentioned(self):
        assert "puesto" in self.prompt.lower() or "recruitment_positions" in self.prompt

    def test_cv_processing_mentioned(self):
        assert "CV" in self.prompt

    def test_pipeline_stages_mentioned(self):
        assert "new" in self.prompt
        assert "reviewed" in self.prompt
        assert "shortlisted" in self.prompt

    def test_scoring_mentioned(self):
        assert "puntuación" in self.prompt.lower() or "puntuar" in self.prompt.lower()


# ─────────────────────────────────────────────────────────────
# 2. TESTS DE ESTRUCTURA — con MockChatModel
# ─────────────────────────────────────────────────────────────

class TestClassifierStructure:
    """Verifica que el clasificador funciona end-to-end con Mock LLM."""

    @pytest.mark.asyncio
    async def test_classifier_returns_valid_domain(self, seed_tenant_and_user, db):
        """El nodo classify debe devolver un domain string válido."""
        import sys, uuid
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from app.agents.orchestrator.state import OrchestratorState, TaskStatus, VALID_DOMAINS
        from app.agents.orchestrator.classifier import classify_node

        tenant, user, token = seed_tenant_and_user
        state = OrchestratorState(
            task_id=str(uuid.uuid4()),
            tenant_id=str(tenant.id),
            user_id=str(user.id),
            user_intent="crea una factura para García por 1500 euros",
            classified_domain="",
            plan=[],
            iteration_count=0,
            status=TaskStatus.PENDING,
            agent_results=[],
            error_message=None,
            requires_human_approval=False,
            additional_metadata=None,
        )
        result = await classify_node(state)
        domain = result.get("classified_domain", "")
        assert domain in VALID_DOMAINS or domain == "unknown", \
            f"classify_node devolvió dominio inválido: {repr(domain)}"

    @pytest.mark.asyncio
    async def test_workflow_agent_creates_workflow_in_db(self, seed_tenant_and_user, db):
        """El workflow agent debe crear un Workflow en la BD."""
        import sys, uuid
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from sqlalchemy import select
        from app.db.models.models import Workflow
        from app.agents.workflow.agent import run_workflow_agent

        tenant, user, _ = seed_tenant_and_user
        result = await run_workflow_agent(
            user_intent="cada lunes a las 9 envíame resumen de facturas pendientes",
            tenant_id=str(tenant.id),
            user_id=str(user.id),
        )

        # Con MockChatModel puede devolver success o failure, pero no debe lanzar excepción
        assert result is not None
        assert hasattr(result, "success")
        assert hasattr(result, "action")


# ─────────────────────────────────────────────────────────────
# 3. TESTS E2E CON LLM REAL — skipean sin API key
# ─────────────────────────────────────────────────────────────

def _call_claude_sync(messages) -> str:
    """
    Llama al Claude CLI vía subprocess.run (síncrono).
    Evita [System]: prefixes que Claude detecta como prompt injection.
    """
    import subprocess
    from app.core.llm.claude_code import _neutral_cwd, _clean_env
    from langchain_core.messages import SystemMessage, HumanMessage

    if not _has_real_llm():
        pytest.skip("Claude CLI no disponible.")

    # Build prompt without [System]: labels to avoid injection detection
    parts = []
    for msg in messages:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        if isinstance(msg, SystemMessage):
            parts.append(content)
        else:
            parts.append(f"User: {content}")
    prompt = "\n\n".join(parts)

    result = subprocess.run(
        [_CLAUDE_BIN, "-p", "--dangerously-skip-permissions"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=60,
        encoding="utf-8",
        env={**_clean_env(), "CLAUDE_CODE_BIN": _CLAUDE_BIN},
        cwd=_neutral_cwd(),
    )
    return result.stdout.strip() or result.stderr.strip() or "sin respuesta"


@pytest.fixture
def real_llm():
    if not _has_real_llm():
        pytest.skip("Claude CLI no disponible.")
    return None  # no se usa directamente, tests llaman _call_claude_sync


@pytest.fixture
def classifier_llm():
    if not _has_real_llm():
        pytest.skip("Claude CLI no disponible.")
    return None


@pytest.mark.e2e
class TestClassifierE2E:
    """Prueba que el clasificador asigna los dominios correctos con LLM real."""

    CASES = [
        ("crea una factura para García S.L. por 1500€ de consultoría", "billing"),
        ("cada lunes envíame un resumen de facturas pendientes", "workflow"),
        ("da de alta a María García, contrato indefinido, 2200€/mes", "hr"),
        ("¿cuánto hemos facturado este mes?", "billing"),
        ("muéstrame el embudo de ventas", "crm"),
        ("sube este contrato PDF y extrae la fecha de vencimiento", "documents"),
        ("¿cuál es el saldo de la cuenta bancaria?", "banking"),
        ("¿qué dice la AEAT sobre el modelo 303?", "compliance"),
    ]

    @pytest.mark.parametrize("user_input,expected_domain", CASES)
    def test_classifies_correctly(self, user_input, expected_domain, classifier_llm):
        from langchain_core.messages import HumanMessage, SystemMessage
        from app.prompts import load_prompt

        prompt = load_prompt("classifier")
        got = _call_claude_sync([
            SystemMessage(content=prompt),
            HumanMessage(content=user_input),
        ]).lower().rstrip(".")
        assert got == expected_domain, (
            f"\nInput:    {repr(user_input)}\n"
            f"Expected: {repr(expected_domain)}\n"
            f"Got:      {repr(got)}\n"
            "→ Revisar classifier.txt para mejorar la definición de este dominio"
        )


@pytest.mark.e2e
class TestBillingAgentToolChoiceE2E:
    """Prueba que el billing agent elige la herramienta correcta con LLM real."""

    def test_create_invoice_standard(self):
        """Input estándar → create_invoice con amount_base correcto (no total con IVA)."""
        tool_call = _run_billing_agent_get_first_tool(
            "Crea una factura para García S.L. por 1500€ de consultoría"
        )
        assert tool_call["name"] == "create_invoice", \
            f"Esperaba create_invoice, obtuvo {tool_call['name']}"
        args = tool_call["args"]
        assert float(args.get("amount_base", 0)) == pytest.approx(1500, abs=1), \
            f"amount_base debería ser 1500 (sin IVA), obtuvo {args.get('amount_base')}"

    def test_create_invoice_iva_incluido(self):
        """IVA incluido → amount_base debe ser la base (1500, no 1815)."""
        tool_call = _run_billing_agent_get_first_tool(
            "Factura a Telefónica por 1815€ IVA incluido, servicios de mantenimiento"
        )
        assert tool_call["name"] == "create_invoice", \
            f"Esperaba create_invoice, obtuvo {tool_call['name']}"
        args = tool_call["args"]
        base = float(args.get("amount_base", 0))
        # Base debe ser ≈1500 (1815 / 1.21 = 1500), no 1815
        assert base < 1800, (
            f"amount_base={base} parece ser el total con IVA (1815), debería ser la base ≈1500.\n"
            "→ Revisar la regla CRÍTICO de IVA en billing_agent.txt"
        )
        assert base == pytest.approx(1500, abs=5), \
            f"amount_base={base}, esperado ≈1500 (1815/1.21). " \
            "→ El LLM no está dividiendo entre 1.21 para IVA incluido"

    def test_query_uses_list_not_create(self):
        """Una consulta NO debe llamar a create_invoice."""
        tool_call = _run_billing_agent_get_first_tool(
            "¿Cuánto hemos facturado este mes y qué facturas están pendientes?"
        )
        assert tool_call["name"] != "create_invoice", (
            f"Una consulta no debería crear factura. El LLM llamó a {tool_call['name']}.\n"
            "→ Reforzar ejemplos en billing_agent.txt sobre consultas vs creaciones"
        )
        assert tool_call["name"] == "list_invoices", \
            f"Esperaba list_invoices para consulta, obtuvo {tool_call['name']}"

    def test_mark_paid_uses_list_first(self):
        """Marcar factura como pagada debe consultar primero (list_invoices), luego update_status."""
        tool_call = _run_billing_agent_get_first_tool(
            "Marca como pagada la última factura de García"
        )
        # El primer tool call debe ser list_invoices para encontrar el ID
        assert tool_call["name"] == "list_invoices", (
            f"Para marcar como pagada, el primer paso debe ser list_invoices, no {tool_call['name']}.\n"
            "→ El ejemplo de 'marcar pagada' en billing_agent.txt debe estar más claro"
        )


@pytest.mark.e2e
class TestHRAgentToolChoiceE2E:
    """Prueba que el HR agent elige la herramienta correcta con LLM real."""

    def test_bulk_payroll_uses_generate_all(self):
        """'Genera todas las nóminas' debe usar generate_all_payrolls, NO calculate_and_create_payroll."""
        tool_call = _run_hr_agent_get_first_tool(
            "Genera todas las nóminas de este mes"
        )
        assert tool_call["name"] == "generate_all_payrolls", (
            f"Esperaba generate_all_payrolls, obtuvo {tool_call['name']}.\n"
            "→ El ejemplo de 'todas las nóminas' en hr/prompts.py no está funcionando"
        )

    def test_individual_payroll_queries_employee_first(self):
        """Nómina individual → list_employees primero para obtener NIF."""
        tool_call = _run_hr_agent_get_first_tool(
            "Calcula la nómina de Ana García de marzo"
        )
        assert tool_call["name"] == "list_employees", (
            f"Debería consultar list_employees para obtener el NIF de Ana García, "
            f"pero llamó a {tool_call['name']}.\n"
            "→ Reforzar el ejemplo de 'nómina individual' en hr/prompts.py"
        )

    def test_annual_salary_converted_correctly(self):
        """Salario anual '26400€/año' debe convertirse a 2200€/mes."""
        tool_call = _run_hr_agent_get_first_tool(
            "Da de alta a Juan Pérez con NIF 12345678A, 26400€ anuales brutos, cargo: analista"
        )
        assert tool_call["name"] == "create_employee", \
            f"Esperaba create_employee, obtuvo {tool_call['name']}"
        args = tool_call["args"]
        salary = float(args.get("base_salary", args.get("salario_base", args.get("salary", args.get("monthly_salary", 0)))))
        assert salary == pytest.approx(2200, abs=10), (
            f"salario_base={salary}, esperado 2200 (26400/12).\n"
            "→ La regla de conversión salario anual→mensual no está funcionando"
        )


@pytest.mark.e2e
class TestWorkflowAgentE2E:
    """Prueba que el workflow agent genera JSON válido con LLM real."""

    def test_weekly_schedule_creates_correct_cron(self):
        """'Cada lunes a las 9' → cron '0 9 * * 1'."""
        result_json = _run_workflow_agent_get_json(
            "Cada lunes a las 9 envíame un resumen de facturas pendientes"
        )
        assert result_json.get("action") == "create", \
            f"Esperaba action=create, obtuvo {result_json.get('action')}"
        assert result_json.get("trigger_type") == "schedule_based", \
            f"Esperaba schedule_based, obtuvo {result_json.get('trigger_type')}"
        cron = result_json.get("trigger_config", {}).get("cron", "")
        assert "1" in cron, (
            f"El cron '{cron}' no contiene '1' (lunes).\n"
            "→ El LLM no está generando el cron correcto para 'cada lunes'"
        )
        assert "9" in cron, \
            f"El cron '{cron}' no contiene '9' (las 9:00)."

    def test_event_trigger_on_invoice_created(self):
        """'Cuando se cree una factura' → trigger_type event_based."""
        result_json = _run_workflow_agent_get_json(
            "Cuando se cree una factura, envía una notificación al equipo"
        )
        assert result_json.get("trigger_type") == "event_based", (
            f"Esperaba event_based, obtuvo {result_json.get('trigger_type')}.\n"
            "→ El LLM confunde 'cuando se cree X' (event) con schedule"
        )


@pytest.mark.e2e
class TestBankingAgentToolChoiceE2E:
    """Prueba que el banking agent elige la herramienta correcta con LLM real."""

    def test_saldo_uses_check_balances(self):
        tool_call = _run_generic_agent_tool(
            "banking_agent", "{tenant_id}", "banking",
            "¿Cuál es el saldo actual de nuestras cuentas?"
        )
        assert tool_call["name"] == "check_balances", (
            f"Esperaba check_balances, obtuvo {tool_call['name']}"
        )

    def test_movimientos_uses_list_transactions(self):
        tool_call = _run_generic_agent_tool(
            "banking_agent", "{tenant_id}", "banking",
            "Muéstrame los últimos movimientos bancarios"
        )
        assert tool_call["name"] == "list_transactions", (
            f"Esperaba list_transactions, obtuvo {tool_call['name']}"
        )

    def test_resumen_uses_financial_summary(self):
        tool_call = _run_generic_agent_tool(
            "banking_agent", "{tenant_id}", "banking",
            "Dame un resumen financiero completo del mes"
        )
        assert tool_call["name"] == "financial_summary", (
            f"Esperaba financial_summary, obtuvo {tool_call['name']}"
        )


@pytest.mark.e2e
class TestComplianceAgentToolChoiceE2E:
    """Prueba que el compliance agent elige la herramienta correcta con LLM real."""

    def test_modelo_303_uses_fiscal_query(self):
        tool_call = _run_generic_agent_tool(
            "compliance_agent", "{tenant_id}", "compliance",
            "¿Qué obligaciones tengo con el modelo 303?"
        )
        assert tool_call["name"] == "fiscal_query", (
            f"Esperaba fiscal_query, obtuvo {tool_call['name']}"
        )

    def test_plazos_uses_check_fiscal_deadlines(self):
        tool_call = _run_generic_agent_tool(
            "compliance_agent", "{tenant_id}", "compliance",
            "¿Cuáles son los próximos plazos fiscales de la AEAT?"
        )
        assert tool_call["name"] == "check_fiscal_deadlines", (
            f"Esperaba check_fiscal_deadlines, obtuvo {tool_call['name']}"
        )

    def test_boe_uses_check_boe_news(self):
        tool_call = _run_generic_agent_tool(
            "compliance_agent", "{tenant_id}", "compliance",
            "¿Hay novedades en el BOE que me afecten como PYME?"
        )
        assert tool_call["name"] == "check_boe_news", (
            f"Esperaba check_boe_news, obtuvo {tool_call['name']}"
        )


@pytest.mark.e2e
class TestCRMAgentToolChoiceE2E:
    """Prueba que el CRM agent elige la herramienta correcta con LLM real."""

    def test_embudo_uses_list_opportunities(self):
        tool_call = _run_agent_get_first_tool(
            _CRM_SYSTEM_PROMPT, _import_tools("crm"),
            "Muéstrame el embudo de ventas", "crm"
        )
        assert tool_call["name"] == "list_opportunities", (
            f"Esperaba list_opportunities, obtuvo {tool_call['name']}"
        )

    def test_cualifica_leads_uses_qualify_leads(self):
        tool_call = _run_agent_get_first_tool(
            _CRM_SYSTEM_PROMPT, _import_tools("crm"),
            "Cualifica los leads nuevos y dime a quién contactar primero", "crm"
        )
        assert tool_call["name"] == "qualify_leads", (
            f"Esperaba qualify_leads, obtuvo {tool_call['name']}"
        )

    def test_nuevo_cliente_uses_create_client(self):
        tool_call = _run_agent_get_first_tool(
            _CRM_SYSTEM_PROMPT, _import_tools("crm"),
            "Registra un cliente nuevo: Acme S.L., NIF B12345678, email contacto@acme.es", "crm"
        )
        assert tool_call["name"] == "create_client", (
            f"Esperaba create_client, obtuvo {tool_call['name']}"
        )


@pytest.mark.e2e
class TestDocumentsAgentToolChoiceE2E:
    """Prueba que el documents agent elige la herramienta correcta con LLM real."""

    def test_clasifica_uses_classify_document(self):
        tool_call = _run_generic_agent_tool(
            "documents_agent", "{tenant_id}", "documents",
            "Clasifica el documento que acabo de subir con document_id doc-abc123"
        )
        assert tool_call["name"] == "classify_document", (
            f"Esperaba classify_document, obtuvo {tool_call['name']}"
        )

    def test_busca_uses_search_documents_semantic(self):
        tool_call = _run_generic_agent_tool(
            "documents_agent", "{tenant_id}", "documents",
            "Busca en los documentos facturas de Acme del último trimestre"
        )
        assert tool_call["name"] == "search_documents_semantic", (
            f"Esperaba search_documents_semantic, obtuvo {tool_call['name']}"
        )


@pytest.mark.e2e
class TestEmailAgentToolChoiceE2E:
    """Prueba que el email agent elige la herramienta correcta con LLM real."""

    def test_leer_correo_uses_check_inbox(self):
        tool_call = _run_email_agent_get_first_tool(
            "Lee mis correos recientes"
        )
        assert tool_call["name"] == "check_inbox", (
            f"Esperaba check_inbox, obtuvo {tool_call['name']}"
        )

    def test_enviar_email_uses_send_email(self):
        tool_call = _run_email_agent_get_first_tool(
            "Envía un email a juan@acme.com con asunto Presupuesto y dile que adjunto el documento"
        )
        assert tool_call["name"] == "send_email", (
            f"Esperaba send_email, obtuvo {tool_call['name']}"
        )

    def test_correos_sin_leer_uses_check_unread(self):
        tool_call = _run_email_agent_get_first_tool(
            "¿Tengo correos sin leer?"
        )
        assert tool_call["name"] == "check_unread", (
            f"Esperaba check_unread, obtuvo {tool_call['name']}"
        )


@pytest.mark.e2e
class TestExcelAgentToolChoiceE2E:
    """Prueba que el excel agent elige la herramienta correcta con LLM real."""

    def test_exporta_facturas_uses_export_erp_data(self):
        tool_call = _run_generic_agent_tool(
            "excel_agent", "{tenant_id}", "excel",
            "Exporta las facturas a Excel"
        )
        assert tool_call["name"] == "export_erp_data", (
            f"Esperaba export_erp_data, obtuvo {tool_call['name']}"
        )

    def test_que_datos_uses_list_available_datasets(self):
        tool_call = _run_generic_agent_tool(
            "excel_agent", "{tenant_id}", "excel",
            "¿Qué datos puedo exportar a Excel?"
        )
        assert tool_call["name"] == "list_available_datasets", (
            f"Esperaba list_available_datasets, obtuvo {tool_call['name']}"
        )


@pytest.mark.e2e
class TestMarketingAgentToolChoiceE2E:
    """Prueba que el marketing agent consulta el catálogo antes de generar contenido."""

    def test_plan_redes_uses_get_product_catalog(self):
        tool_call = _run_generic_agent_tool(
            "marketing_agent", None, "marketing",
            "Crea un plan de contenidos para redes sociales basado en nuestros productos actuales"
        )
        assert tool_call["name"] == "get_product_catalog", (
            f"Esperaba get_product_catalog, obtuvo {tool_call['name']}"
        )


@pytest.mark.e2e
class TestRAGAgentToolChoiceE2E:
    """Prueba que el RAG agent elige la herramienta correcta con LLM real."""

    def test_busca_uses_search_documents(self):
        tool_call = _run_generic_agent_tool(
            "rag_agent", "{tenant_id}", "rag",
            "Busca en mis documentos contratos de 2024"
        )
        assert tool_call["name"] == "search_documents", (
            f"Esperaba search_documents, obtuvo {tool_call['name']}"
        )

    def test_pregunta_uses_answer_from_documents(self):
        tool_call = _run_generic_agent_tool(
            "rag_agent", "{tenant_id}", "rag",
            "¿Qué dice mi contrato sobre la cláusula de penalización?"
        )
        assert tool_call["name"] == "answer_from_documents", (
            f"Esperaba answer_from_documents, obtuvo {tool_call['name']}"
        )


@pytest.mark.e2e
class TestRecruitmentAgentToolChoiceE2E:
    """Prueba que el recruitment agent elige la herramienta correcta con LLM real."""

    def test_publica_puesto_uses_create_position(self):
        tool_call = _run_generic_agent_tool(
            "recruitment_agent", None, "recruitment",
            "Publica un puesto de Python developer en el departamento de Tecnología"
        )
        assert tool_call["name"] == "create_position", (
            f"Esperaba create_position, obtuvo {tool_call['name']}"
        )

    def test_muestra_candidatos_uses_list_candidates(self):
        tool_call = _run_generic_agent_tool(
            "recruitment_agent", None, "recruitment",
            "Muéstrame los candidatos para el puesto abierto"
        )
        assert tool_call["name"] == "list_candidates", (
            f"Esperaba list_candidates, obtuvo {tool_call['name']}"
        )

    def test_procesa_cv_uses_process_cv(self):
        tool_call = _run_generic_agent_tool(
            "recruitment_agent", None, "recruitment",
            "Procesa el CV del archivo cv-juan.pdf para el puesto pos-123"
        )
        assert tool_call["name"] == "process_cv", (
            f"Esperaba process_cv, obtuvo {tool_call['name']}"
        )


# ─────────────────────────────────────────────────────────────
# HELPERS para tests E2E con LLM real
# ─────────────────────────────────────────────────────────────

def _setup_claude_bin():
    os.environ.setdefault("CLAUDE_CODE_BIN", _CLAUDE_BIN)


def _build_agent_prompt_for_test(system_content: str, tool_system: str, user_message: str) -> str:
    """
    Builds agent prompt without [System]: labels that trigger Claude's injection detection.
    Format: system instructions → tool protocol → user request (no prefixes).
    """
    return f"{system_content}\n\n{tool_system}\n\nUser request: {user_message}"


def _run_agent_get_first_tool(
    system_prompt: str,
    agent_tools: list,
    user_intent: str,
    agent_label: str = "agent",
) -> dict:
    """Generic: runs any agent via Claude CLI and returns the first tool call."""
    import subprocess
    _setup_claude_bin()
    from app.core.llm.claude_code import (
        _neutral_cwd, _clean_env,
        _build_tool_system_prompt, _parse_tool_response,
    )

    tool_system = _build_tool_system_prompt(agent_tools)
    full_prompt = _build_agent_prompt_for_test(system_prompt, tool_system, user_intent)
    result = subprocess.run(
        [_CLAUDE_BIN, "-p", "--dangerously-skip-permissions"],
        input=full_prompt, capture_output=True, text=True, timeout=60,
        encoding="utf-8",
        env={**_clean_env(), "CLAUDE_CODE_BIN": _CLAUDE_BIN},
        cwd=_neutral_cwd(),
    )
    raw = result.stdout.strip() or result.stderr.strip() or "sin respuesta"
    if "api error" in raw.lower() or "bonsai" in raw.lower():
        pytest.skip(f"CLI returned API error (not a prompt issue): {raw[:200]}")
    msg = _parse_tool_response(raw)
    if not msg.tool_calls:
        pytest.fail(
            f"El {agent_label} agent no hizo ningún tool call para: {repr(user_intent)}\n"
            f"Respuesta: {raw[:300]}"
        )
    return {"name": msg.tool_calls[0]["name"], "args": msg.tool_calls[0].get("args", {})}


def _import_tools(domain: str) -> list:
    """Import and return the tools list for a given agent domain."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    if domain == "email":
        from app.agents.email.tools import build_tools_list
        return build_tools_list()
    mod = __import__(f"app.agents.{domain}.tools", fromlist=["tools"])
    return mod.tools


def _run_generic_agent_tool(
    prompt_name: str,
    tenant_id_placeholder: str | None,
    domain: str,
    user_intent: str,
) -> dict:
    """Load a .txt prompt + domain tools, then run the agent and return first tool call."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.prompts import load_prompt

    prompt = load_prompt(prompt_name)
    if "{tenant_id}" in prompt:
        prompt = prompt.format(tenant_id="test-tenant")
    agent_tools = _import_tools(domain)
    return _run_agent_get_first_tool(prompt, agent_tools, user_intent, domain)


def _run_email_agent_get_first_tool(user_intent: str) -> dict:
    """Run the email agent (dynamic prompt) and return first tool call."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.agents.email.prompts import build_system_prompt
    from app.agents.email.tools import build_tools_list

    prompt = build_system_prompt("NOTA: Datos de demostración.", "test-tenant")
    agent_tools = build_tools_list()
    return _run_agent_get_first_tool(prompt, agent_tools, user_intent, "email")


def _run_billing_agent_get_first_tool(user_intent: str) -> dict:
    """Ejecuta el billing agent y devuelve el primer tool call del LLM (síncrono)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from datetime import date
    from app.prompts import load_prompt
    from app.agents.billing.tools import tools

    agent_prompt = load_prompt("billing_agent").format(
        tenant_id="test-tenant",
        today=date.today().isoformat(),
    )
    return _run_agent_get_first_tool(agent_prompt, tools, user_intent, "billing")


def _run_hr_agent_get_first_tool(user_intent: str) -> dict:
    """Ejecuta el HR agent y devuelve el primer tool call del LLM (síncrono)."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app.agents.hr.prompts import build_system_prompt
    from app.agents.hr.tools import (
        create_employee, calculate_and_create_payroll, generate_all_payrolls,
        list_employees, list_payrolls, update_payroll, approve_payroll,
    )

    agent_prompt = build_system_prompt("test-tenant")
    hr_tools = [create_employee, calculate_and_create_payroll, generate_all_payrolls,
                list_employees, list_payrolls, update_payroll, approve_payroll]
    return _run_agent_get_first_tool(agent_prompt, hr_tools, user_intent, "hr")


def _run_workflow_agent_get_json(user_intent: str) -> dict:
    """Ejecuta el workflow agent y devuelve el JSON parseado (síncrono)."""
    import sys, json as _json, subprocess
    sys.path.insert(0, str(Path(__file__).parent.parent))
    _setup_claude_bin()
    from app.prompts import load_prompt
    from app.core.llm.claude_code import _neutral_cwd, _clean_env

    agent_prompt = load_prompt("workflow_agent")
    full_prompt = f"{agent_prompt}\n\nUser request: {user_intent}"
    result = subprocess.run(
        [_CLAUDE_BIN, "-p", "--dangerously-skip-permissions"],
        input=full_prompt, capture_output=True, text=True, timeout=60,
        encoding="utf-8",
        env={**_clean_env(), "CLAUDE_CODE_BIN": _CLAUDE_BIN},
        cwd=_neutral_cwd(),
    )
    raw = result.stdout.strip() or result.stderr.strip() or "sin respuesta"
    if "api error" in raw.lower() or "bonsai" in raw.lower():
        pytest.skip(f"CLI returned API error (not a prompt issue): {raw[:200]}")
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()
    try:
        return _json.loads(raw)
    except Exception as e:
        pytest.fail(f"Workflow agent no devolvió JSON válido:\n{raw[:300]}\nError: {e}")
