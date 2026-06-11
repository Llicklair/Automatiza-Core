"""Backward-compatibility shim — implementation in queries.py / commands.py."""
from app.services.hr.commands import (
    approve_document,
    delete_document,
    generate_document,
    get_document_pdf,
)
from app.services.hr.queries import (
    DOC_TYPE_LABELS,
    _build_company_context,
    _build_employee_context,
    _get_system_prompt,
    _strip_markdown_wrapper,
    get_document,
    list_documents,
)

__all__ = [
    "list_documents",
    "get_document",
    "generate_document",
    "approve_document",
    "delete_document",
    "get_document_pdf",
    "DOC_TYPE_LABELS",
    "_get_system_prompt",
    "_build_employee_context",
    "_build_company_context",
    "_strip_markdown_wrapper",
]
