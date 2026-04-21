"""CRM domain services."""

from app.services.crm.contract_generator import (
    build_context_for_client,
    build_context_for_employee,
    generate_contract,
)
from app.services.crm.service import (
    create_activity,
    create_event,
    create_opportunity,
    create_reservation,
    delete_activity,
    delete_event,
    delete_opportunity,
    delete_reservation,
    list_activities,
    list_events,
    list_opportunities,
    list_reservations,
    update_event,
    update_opportunity,
    update_reservation,
)

__all__ = [
    # service
    "list_opportunities",
    "create_opportunity",
    "update_opportunity",
    "delete_opportunity",
    "list_activities",
    "create_activity",
    "delete_activity",
    "list_events",
    "create_event",
    "update_event",
    "delete_event",
    "list_reservations",
    "create_reservation",
    "update_reservation",
    "delete_reservation",
    # contract_generator
    "build_context_for_client",
    "build_context_for_employee",
    "generate_contract",
]
