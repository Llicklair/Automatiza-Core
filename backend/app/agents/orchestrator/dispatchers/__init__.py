"""
Dispatcher registry — centraliza el mapeo agent_name → función dispatcher.
"""
from app.agents.orchestrator.dispatchers.billing import _dispatch_billing
from app.agents.orchestrator.dispatchers.documents import _dispatch_documents
from app.agents.orchestrator.dispatchers.compliance import _dispatch_compliance
from app.agents.orchestrator.dispatchers.hr import _dispatch_hr
from app.agents.orchestrator.dispatchers.crm import _dispatch_crm
from app.agents.orchestrator.dispatchers.banking import _dispatch_banking
from app.agents.orchestrator.dispatchers.reports import _dispatch_report
from app.agents.orchestrator.dispatchers.chat import _dispatch_chat
from app.agents.orchestrator.dispatchers.misc import (
    _dispatch_rag,
    _dispatch_excel,
    _dispatch_email,
    _dispatch_workflow,
    _dispatch_recruitment,
    _dispatch_marketing,
    _dispatch_skill,
)

# Registro de dispatchers: agent_name → callable(state, subtask) -> AgentResult
DISPATCHER_MAP = {
    "billing": _dispatch_billing,
    "documents": _dispatch_documents,
    "compliance": _dispatch_compliance,
    "banking": _dispatch_banking,
    "rag": _dispatch_rag,
    "crm": _dispatch_crm,
    "hr": _dispatch_hr,
    "excel": _dispatch_excel,
    "email": _dispatch_email,
    "workflow": _dispatch_workflow,
    "report": _dispatch_report,
    "recruitment": _dispatch_recruitment,
    "marketing": _dispatch_marketing,
    "skill": _dispatch_skill,
    "chat": _dispatch_chat,
}

__all__ = [
    "DISPATCHER_MAP",
    "_dispatch_billing",
    "_dispatch_documents",
    "_dispatch_compliance",
    "_dispatch_hr",
    "_dispatch_crm",
    "_dispatch_banking",
    "_dispatch_report",
    "_dispatch_rag",
    "_dispatch_excel",
    "_dispatch_email",
    "_dispatch_workflow",
    "_dispatch_recruitment",
    "_dispatch_marketing",
    "_dispatch_skill",
    "_dispatch_chat",
]
