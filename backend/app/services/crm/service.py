# Backward-compatibility shim — implementation in queries.py / commands.py.
from app.services.crm.commands import (
    create_activity,
    create_event,
    create_opportunity,
    create_reservation,
    delete_activity,
    delete_event,
    delete_opportunity,
    delete_reservation,
    update_event,
    update_opportunity,
    update_reservation,
)
from app.services.crm.queries import (
    list_activities,
    list_events,
    list_opportunities,
    list_reservations,
)

__all__ = [
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
]
