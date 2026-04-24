"""Asesoria Documental — Generacion de documentos laborales con IA.

Endpoints:
  POST /hr/documents/generate  — Genera un borrador con LLM
  GET  /hr/documents           — Lista documentos generados del tenant
  GET  /hr/documents/{id}      — Detalle de un documento
  POST /hr/documents/{id}/approve — Marca como aprobado
  DELETE /hr/documents/{id}    — Elimina un borrador
"""

import logging

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.hr_documents import GenerateRequest, HRDocumentOut
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.services.hr import documents as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr/documents", tags=["hr-documents"])


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_hr_document(
    payload: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera un borrador de documento laboral usando el LLM."""
    try:
        return await svc.generate_document(
            doc_type=payload.doc_type,
            instructions=payload.instructions,
            employee_name=payload.employee_name,
            employee_id=payload.employee_id,
            tenant_id=current_user.tenant_id,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[HRDocumentOut])
async def list_hr_documents(
    doc_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista documentos generados del tenant, filtrados opcionalmente."""
    return await svc.list_documents(
        tenant_id=current_user.tenant_id,
        db=db,
        doc_type=doc_type,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.get("/{doc_id}")
async def get_hr_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.get_document(doc_id, current_user.tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{doc_id}/approve")
async def approve_hr_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.approve_document(doc_id, current_user.tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hr_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_document(doc_id, current_user.tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
