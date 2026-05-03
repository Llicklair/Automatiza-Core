# Backward-compatibility shim — implementation in queries.py / commands.py.
from app.services.crm.commands import generate_contract
from app.services.crm.queries import build_context_for_client, build_context_for_employee

__all__ = [
    "build_context_for_client",
    "build_context_for_employee",
    "generate_contract",
]
