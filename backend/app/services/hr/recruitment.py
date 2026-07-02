"""Backward-compatibility shim — implementation in queries.py / commands.py."""

from app.services.hr.commands import (
    analyze_cv_standalone,
    create_position,
    update_candidate_status,
    upload_cv,
)
from app.services.hr.queries import (
    VALID_CANDIDATE_STATUSES,
    list_candidates,
    list_positions,
)

__all__ = [
    "list_positions",
    "create_position",
    "list_candidates",
    "upload_cv",
    "update_candidate_status",
    "analyze_cv_standalone",
    "VALID_CANDIDATE_STATUSES",
]
