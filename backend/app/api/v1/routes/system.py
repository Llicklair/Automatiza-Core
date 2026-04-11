"""System routes — frontend error reporting and diagnostics."""

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/system", tags=["system"])
logger = logging.getLogger("frontend_errors")


class FrontendError(BaseModel):
    message: str = Field(..., max_length=2000)
    stack: str | None = Field(None, max_length=5000)
    url: str | None = Field(None, max_length=500)
    component: str | None = Field(None, max_length=200)
    digest: str | None = Field(None, max_length=100)
    timestamp: str | None = None


@router.post("/frontend-errors", status_code=204)
async def report_frontend_error(payload: FrontendError, request: Request):
    """Receive and log errors from the frontend error boundaries."""
    logger.warning(
        "FRONTEND_ERROR component=%s url=%s message=%s digest=%s",
        payload.component or "unknown",
        payload.url or "-",
        payload.message[:200],
        payload.digest or "-",
    )
    if payload.stack:
        logger.debug("FRONTEND_ERROR_STACK:\n%s", payload.stack[:3000])
    return None
