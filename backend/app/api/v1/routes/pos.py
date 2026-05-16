"""Rutas TPV (Punto de Venta)."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.pos import (
    PosCheckoutRequest,
    PosLineAdd,
    PosLineUpdate,
    PosSessionResponse,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.sales import pos as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pos", tags=["pos"])


@router.get("/sessions/current", response_model=PosSessionResponse | None)
@limiter.limit("60/minute")
async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_current_session(
        db, current_user.tenant_id, current_user.id
    )


@router.post(
    "/sessions",
    response_model=PosSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def open_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.open_session(
            db, current_user.tenant_id, current_user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/sessions", response_model=list[PosSessionResponse])
@limiter.limit("30/minute")
async def list_sessions(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    only_mine: bool = Query(default=False),
    limit: int = Query(default=50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_sessions(
        db,
        current_user.tenant_id,
        user_id=current_user.id if only_mine else None,
        status=status_filter,
        limit=limit,
    )


@router.get("/sessions/{session_id}", response_model=PosSessionResponse)
@limiter.limit("60/minute")
async def get_session(
    request: Request,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc._get_session_for_user(  # noqa: SLF001 — helper interno reutilizado
            db, current_user.tenant_id, session_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/sessions/{session_id}/lines",
    response_model=PosSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("120/minute")
async def add_line(
    request: Request,
    session_id: UUID,
    payload: PosLineAdd,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.add_line(
            db, current_user.tenant_id, session_id, payload.model_dump()
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.patch(
    "/sessions/{session_id}/lines/{line_id}",
    response_model=PosSessionResponse,
)
@limiter.limit("60/minute")
async def update_line(
    request: Request,
    session_id: UUID,
    line_id: UUID,
    payload: PosLineUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_line_quantity(
            db,
            current_user.tenant_id,
            session_id,
            line_id,
            payload.quantity,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete(
    "/sessions/{session_id}/lines/{line_id}",
    response_model=PosSessionResponse,
)
@limiter.limit("60/minute")
async def remove_line(
    request: Request,
    session_id: UUID,
    line_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.remove_line(
            db, current_user.tenant_id, session_id, line_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/sessions/{session_id}/checkout", response_model=PosSessionResponse
)
@limiter.limit("30/minute")
async def checkout(
    request: Request,
    session_id: UUID,
    payload: PosCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.checkout(
            db,
            current_user.tenant_id,
            session_id,
            current_user.id,
            payload.payment_method,
            payload.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post(
    "/sessions/{session_id}/cancel", response_model=PosSessionResponse
)
@limiter.limit("30/minute")
async def cancel_session(
    request: Request,
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.cancel_session(
            db, current_user.tenant_id, session_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
