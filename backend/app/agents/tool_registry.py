"""
Registro central de herramientas (@tool) de todos los agentes.

Permite ejecutar tools por nombre sin pasar por LangGraph/LLM,
habilitando pasos deterministas en workflows híbridos.

Uso:
    from app.agents.tool_registry import call_tool
    result = call_tool("list_invoices", {"tenant_id": "...", "limit": 10})
"""
import asyncio
import inspect
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Registro lazy: se puebla una sola vez al primer acceso
_REGISTRY: dict[str, Callable] | None = None


def _build_registry() -> dict[str, Callable]:
    """Importa todos los agentes y recopila sus @tool functions."""
    registry: dict[str, Callable] = {}

    # — billing —
    from app.agents.billing_agent import (
        create_invoice, list_invoices, search_client,
        update_invoice_status, update_invoice, send_invoice_by_email,
    )
    registry["create_invoice"] = create_invoice
    registry["list_invoices"] = list_invoices
    registry["search_client"] = search_client
    registry["update_invoice_status"] = update_invoice_status
    registry["update_invoice"] = update_invoice
    registry["send_invoice_by_email"] = send_invoice_by_email

    # — hr —
    from app.agents.hr_agent import (
        create_employee, calculate_and_create_payroll, generate_all_payrolls,
        list_employees, list_payrolls, update_payroll, approve_payroll,
    )
    registry["create_employee"] = create_employee
    registry["calculate_and_create_payroll"] = calculate_and_create_payroll
    registry["generate_all_payrolls"] = generate_all_payrolls
    registry["list_employees"] = list_employees
    registry["list_payrolls"] = list_payrolls
    registry["update_payroll"] = update_payroll
    registry["approve_payroll"] = approve_payroll

    # — crm —
    from app.agents.crm_agent import list_opportunities, create_opportunity, update_opportunity_stage, qualify_leads
    registry["list_opportunities"] = list_opportunities
    registry["create_opportunity"] = create_opportunity
    registry["update_opportunity_stage"] = update_opportunity_stage
    registry["qualify_leads"] = qualify_leads

    # — banking —
    from app.agents.banking_agent import check_balances, list_transactions, financial_summary, reconcile_transactions
    registry["check_balances"] = check_balances
    registry["list_transactions"] = list_transactions
    registry["financial_summary"] = financial_summary
    registry["reconcile_transactions"] = reconcile_transactions

    # — compliance —
    from app.agents.compliance_agent import check_fiscal_deadlines, check_boe_news, fiscal_query
    registry["check_fiscal_deadlines"] = check_fiscal_deadlines
    registry["check_boe_news"] = check_boe_news
    registry["fiscal_query"] = fiscal_query

    # — documents —
    from app.agents.documents_agent import classify_document, search_documents_semantic
    registry["classify_document"] = classify_document
    registry["search_documents_semantic"] = search_documents_semantic

    # — excel —
    from app.agents.excel_agent import export_erp_data, list_available_datasets, import_excel, modify_excel, read_excel
    registry["export_erp_data"] = export_erp_data
    registry["list_available_datasets"] = list_available_datasets
    registry["import_excel"] = import_excel
    registry["modify_excel"] = modify_excel
    registry["read_excel"] = read_excel

    # — email —
    from app.agents.email_agent import check_inbox, check_unread, send_email
    registry["check_inbox"] = check_inbox
    registry["check_unread"] = check_unread
    registry["send_email"] = send_email

    # — rag —
    from app.agents.rag_agent import search_documents, answer_from_documents
    registry["search_documents"] = search_documents
    registry["answer_from_documents"] = answer_from_documents

    # — shared agent_tools —
    from app.agents.agent_tools.documents import (
        create_document, list_tenant_documents, update_existing_document, get_document_content,
    )
    registry["create_document"] = create_document
    registry["list_tenant_documents"] = list_tenant_documents
    registry["update_existing_document"] = update_existing_document
    registry["get_document_content"] = get_document_content

    from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
    registry["get_tenant_knowledge"] = get_tenant_knowledge
    registry["upsert_tenant_knowledge"] = upsert_tenant_knowledge

    logger.info("Tool registry loaded: %d tools", len(registry))
    return registry


def get_registry() -> dict[str, Callable]:
    """Devuelve el registro, construyéndolo lazy en el primer acceso."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY


def list_tools() -> list[str]:
    """Devuelve los nombres de todas las tools disponibles."""
    return sorted(get_registry().keys())


def call_tool(tool_name: str, params: dict[str, Any]) -> str:
    """
    Llama a una @tool function directamente por nombre.
    Los @tool de LangChain son funciones sync que internamente
    llaman asyncio.run_until_complete, así que se invocan directamente.

    Returns:
        El string que devuelve la tool.
    Raises:
        KeyError si la tool no existe.
        Exception si la tool falla.
    """
    registry = get_registry()
    if tool_name not in registry:
        raise KeyError(f"Tool '{tool_name}' no encontrada. Disponibles: {list_tools()}")

    fn = registry[tool_name]

    # Las @tool de LangChain wrappean la función real en .func
    # Pero se pueden llamar directamente como fn.invoke(params) o fn(params)
    # Usar .invoke() es el método oficial de LangChain tools
    try:
        result = fn.invoke(params)
    except Exception:
        # Fallback: llamada directa
        result = fn(**params)

    return str(result) if result is not None else ""
