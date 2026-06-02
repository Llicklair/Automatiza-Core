"""Analytics aggregation services for dashboard endpoints + product event tracking (OPS.MET)."""

from app.services.analytics.dashboard import (
    DEMO_TX_PREFIX,
    get_dashboard,
    iter_months_back,
    latest_period_with_data,
)
from app.services.analytics.events import (
    CANONICAL_EVENTS,
    track_event,
)

__all__ = [
    "CANONICAL_EVENTS",
    "DEMO_TX_PREFIX",
    "get_dashboard",
    "iter_months_back",
    "latest_period_with_data",
    "track_event",
]
