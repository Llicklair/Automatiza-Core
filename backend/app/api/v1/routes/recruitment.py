"""
Endpoints para gestion de reclutamiento.
GET/POST puestos, GET candidatos, POST upload CV, PATCH estado candidato.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.recruitment import (
    CandidateResponse,
    PositionCreate,
    PositionResponse,
    StatusUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.middleware.rate_limit import limiter
from app.services import recruitment_service as svc

logger = logging.getLogger(__name__)
router = APIRouter()


# -- Positions ----------------------------------------------------------------


@router.get("/positions", response_model=list[PositionResponse])
@limiter.limit("30/minute")
async def list_positions(
    request: Request,
    status_filter: str = "all",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.list_positions(db, current_user.tenant_id, status_filter)


@router.post("/positions", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_position(
    request: Request,
    payload: PositionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.create_position(db, current_user.tenant_id, payload.model_dump())


# -- Candidates ---------------------------------------------------------------


@router.get("/positions/{position_id}/candidates", response_model=list[CandidateResponse])
@limiter.limit("30/minute")
async def list_candidates(
    request: Request,
    position_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await svc.list_candidates(db, current_user.tenant_id, position_id)


@router.post("/positions/{position_id}/upload-cv", response_model=CandidateResponse)
@limiter.limit("10/minute")
async def upload_cv(
    request: Request,
    position_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Sube un CV (PDF), lo parsea con IA, puntua y guarda el candidato."""
    try:
        return await svc.upload_cv(
            db, current_user.tenant_id, position_id, file.filename, file.file
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.patch("/candidates/{candidate_id}/status", response_model=CandidateResponse)
@limiter.limit("30/minute")
async def update_candidate_status(
    request: Request,
    candidate_id: UUID,
    payload: StatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return await svc.update_candidate_status(
            db, current_user.tenant_id, candidate_id, payload.status
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/analyze-cv")
@limiter.limit("10/minute")
async def analyze_cv_standalone(
    request: Request,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    """Analiza un CV sin asociarlo a ningun puesto. Devuelve datos extraidos por IA."""
    try:
        return await svc.analyze_cv_standalone(file.filename, file.file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
