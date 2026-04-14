"""CRM domain services."""

from app.services.crm.service import (
    list_opportunities,
    create_opportunity,
    update_opportunity,
    delete_opportunity,
    list_activities,
    create_activity,
    delete_activity,
    list_events,
    create_event,
    update_event,
    delete_event,
    list_reservations,
    create_reservation,
    update_reservation,
    delete_reservation,
)
from app.services.crm.contract_generator import (
    build_context_for_client,
    build_context_for_employee,
    generate_contract,
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
