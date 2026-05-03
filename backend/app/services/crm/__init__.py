"""CRM domain services — re-exports for backwards compatibility."""

from app.services.crm.commands import (
    create_activity,
    create_event,
    create_opportunity,
    create_reservation,
    delete_activity,
    delete_event,
    delete_opportunity,
    delete_reservation,
    generate_contract,
    update_event,
    update_opportunity,
    update_reservation,
)
from app.services.crm.queries import (
    build_context_for_client,
    build_context_for_employee,
    list_activities,
    list_events,
    list_opportunities,
    list_reservations,
)

__all__ = [
    # queries
    "list_opportunities",
    "list_activities",
    "list_events",
    "list_reservations",
    "build_context_for_client",
    "build_context_for_employee",
    # commands
    "create_opportunity",
    "update_opportunity",
    "delete_opportunity",
    "create_activity",
    "delete_activity",
    "create_event",
    "update_event",
    "delete_event",
    "create_reservation",
    "update_reservation",
    "delete_reservation",
    "generate_contract",
]
