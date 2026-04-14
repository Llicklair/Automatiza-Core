"""Sandbox de UI Generativa — Interfaces permanentes generadas por IA.

Las interfaces generadas se renderizan con GenerativeUI.tsx (sanitización DOMPurify)
y se comunican con el ERP en una sola dirección (lectura). Nunca mutan datos del ERP
directamente para no comprometer el monolito.

Endpoints:
  GET    /generative-ui/debug-llm — Diagnóstico rápido del LLM
  POST   /generative-ui/generate  — Genera HTML a partir de prompt del usuario
  GET    /generative-ui/history   — Lista interfaces guardadas del tenant
  GET    /generative-ui/{id}      — Devuelve una interfaz específica
  PATCH  /generative-ui/{id}      — Actualiza título/descripción
  DELETE /generative-ui/{id}      — Elimina una interfaz
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.generative_ui import GenerateRequest, GeneratedUIOut, UpdateUIRequest
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.services.ai import generative_ui as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generative-ui", tags=["generative-ui"])


@router.get("/debug-llm")
async def debug_llm(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Diagnóstico rápido: verifica que el LLM responde."""
    return await svc.debug_llm(current_user.tenant_id, db)


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_ui(
    payload: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera una interfaz HTML a partir del prompt del usuario."""
    try:
        ui = await svc.generate_ui(
            payload.prompt, current_user.tenant_id, db, title=payload.title,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="El modelo de IA tardó demasiado en responder. Inténtalo de nuevo.",
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generando UI: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al generar la interfaz: {str(e)}")

    return GeneratedUIOut(
        id=str(ui.id),
        title=ui.title,
        description=ui.description,
        prompt=ui.prompt,
        content_html=ui.content_html,
        is_pinned=ui.is_pinned,
        created_at=ui.created_at.isoformat(),
        updated_at=ui.updated_at.isoformat() if ui.updated_at else ui.created_at.isoformat(),
    )


@router.get("/history", response_model=list[GeneratedUIOut])
async def list_generated_uis(
    pinned_only: bool = Query(False),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    uis = await svc.list_uis(
        current_user.tenant_id, db, pinned_only=pinned_only, limit=limit, offset=offset,
    )
    return [
        GeneratedUIOut(
            id=str(u.id),
            title=u.title,
            description=u.description,
            prompt=u.prompt,
            content_html=u.content_html,
            is_pinned=u.is_pinned,
            created_at=u.created_at.isoformat(),
            updated_at=u.updated_at.isoformat() if u.updated_at else u.created_at.isoformat(),
        )
        for u in uis
    ]


@router.get("/{ui_id}")
async def get_generated_ui(
    ui_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ui = await svc.get_ui(ui_id, current_user.tenant_id, db)
    if not ui:
        raise HTTPException(status_code=404, detail="Interfaz no encontrada")
    return GeneratedUIOut(
        id=str(ui.id),
        title=ui.title,
        description=ui.description,
        prompt=ui.prompt,
        content_html=ui.content_html,
        is_pinned=ui.is_pinned,
        created_at=ui.created_at.isoformat(),
        updated_at=ui.updated_at.isoformat() if ui.updated_at else ui.created_at.isoformat(),
    )


@router.patch("/{ui_id}")
async def update_generated_ui(
    ui_id: str,
    payload: UpdateUIRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ui = await svc.update_ui(
        ui_id, current_user.tenant_id, db,
        title=payload.title, description=payload.description, is_pinned=payload.is_pinned,
    )
    if not ui:
        raise HTTPException(status_code=404, detail="Interfaz no encontrada")
    return {"id": str(ui.id), "title": ui.title, "is_pinned": ui.is_pinned}


@router.delete("/{ui_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generated_ui(
    ui_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.delete_ui(ui_id, current_user.tenant_id, db):
        raise HTTPException(status_code=404, detail="Interfaz no encontrada")
