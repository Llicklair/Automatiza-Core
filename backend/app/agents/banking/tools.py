"""
Banking agent tools re-export facade.

Logic lives in:
  _psd2_helpers.py        — credentials, demo data, ALERT_THRESHOLDS
  _account_tools.py       — check_balances
  _transaction_tools.py   — list_transactions, financial_summary
  _reconciliation_tools.py — reconcile_transactions
"""

from app.agents.banking._account_tools import check_balances  # noqa: F401
from app.agents.banking._transaction_tools import (  # noqa: F401
    financial_summary,
    list_transactions,
)
from app.agents.banking._reconciliation_tools import reconcile_transactions  # noqa: F401
from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge

tools = [
    check_balances,
    list_transactions,
    financial_summary,
    reconcile_transactions,
    create_document,
    list_tenant_documents,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]

__all__ = ["tools"]
