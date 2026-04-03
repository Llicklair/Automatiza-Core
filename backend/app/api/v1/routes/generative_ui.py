"""Sandbox de UI Generativa — Interfaces permanentes generadas por IA.

Las interfaces generadas se renderizan con GenerativeUI.tsx (sanitización DOMPurify)
y se comunican con el ERP en una sola dirección (lectura). Nunca mutan datos del ERP
directamente para no comprometer el monolito.

Endpoints:
  POST   /generative-ui/generate — Genera HTML a partir de prompt del usuario
  GET    /generative-ui/history  — Lista interfaces guardadas del tenant
  GET    /generative-ui/{id}     — Devuelve una interfaz específica
  PATCH  /generative-ui/{id}     — Actualiza título/descripción
  DELETE /generative-ui/{id}     — Elimina una interfaz
"""
import uuid
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, String, Text, DateTime, Boolean, JSON, select, desc
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import Base, get_db
from app.db.models.auth import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/generative-ui", tags=["generative-ui"])


# ── Modelo DB ──────────────────────────────────────────────────────────────────

class GeneratedUI(Base):
    """Interfaz HTML generada por IA y anclada como sección permanente.
    La comunicación con el ERP es unidireccional: solo lectura de datos,
    nunca escritura para proteger el monolito."""
    __tablename__ = "generated_uis"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    prompt = Column(Text, nullable=False)         # The user's original prompt
    content_html = Column(Text, nullable=False)   # Sanitized HTML output
    is_pinned = Column(Boolean, default=True)     # True = pinned in sidebar/dashboard
    metadata_json = Column(JSON, nullable=True)   # Extra config (refresh interval, data sources, etc.)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))


# ── Schemas ────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    title: str | None = None

class GeneratedUIOut(BaseModel):
    id: str
    title: str
    description: str | None
    prompt: str
    content_html: str
    is_pinned: bool
    created_at: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)

class UpdateUIRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    is_pinned: bool | None = None


# ── System Prompt ──────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """Eres un diseñador de interfaces de datos para un ERP empresarial.
El usuario describe lo que quiere ver y tú generas HTML+CSS inline que se renderizará dentro de un contenedor seguro.

REGLAS:
1. Responde SOLO con el HTML, sin explicaciones fuera del código.
2. Usa un estilo visual moderno, oscuro y profesional (fondo oscuro #1a1a2e, bordes sutiles, colores vibrantes para gráficos).
3. Usa SOLO estas etiquetas HTML: div, span, p, table, thead, tbody, tr, td, th, button, b, i, strong, em, h1, h2, h3, h4, ul, ol, li, img, br, hr, a.
4. NO uses <script>, <style>, <iframe>, <form>, <input>, onclick, onerror, ni ningún evento JavaScript.
5. Usa estilos inline (style="...") para todo el diseño. NO references CSS externo.
6. Si el usuario solicita datos del ERP (ventas, facturas, empleados), usa datos de ejemplo realistas en español.
7. Los botones de acción deben tener el atributo data-erp-action="nombre_accion" y data-payload='{"key":"value"}'.
   Estos botones son de SOLO LECTURA: solo disparan consultas de datos, nunca modifican el ERP.
8. Diseña con responsive en mente: usa flexbox y porcentajes para anchos.
9. Incluye emojis como iconografía accesible (📊 📈 💰 👥 📋 etc).
10. Las tablas deben tener cabeceras claras y datos alineados.

EJEMPLOS de botones válidos:
  <button data-erp-action="view_invoices" data-payload='{"month":"current"}' style="...">Ver facturas del mes</button>
  <button data-erp-action="view_employees" data-payload='{"department":"all"}' style="...">Ver plantilla</button>

NUNCA uses:
  <button onclick="...">  ← PROHIBIDO
  <script>...</script>    ← PROHIBIDO
"""


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_ui(
    payload: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera una interfaz HTML a partir del prompt del usuario."""
    from langchain_core.messages import SystemMessage, HumanMessage
    from app.core.llm_factory import get_llm_for_tenant

    try:
        llm = await get_llm_for_tenant(current_user.tenant_id, db, temperature=0.4)
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=payload.prompt),
        ])
        content_html = response.content
    except Exception as e:
        logger.error("Error generando UI: %s", e)
        raise HTTPException(status_code=500, detail=f"Error al generar la interfaz: {str(e)}")

    # Auto-generate title if not provided
    title = payload.title or f"Interfaz — {payload.prompt[:60]}{'...' if len(payload.prompt) > 60 else ''}"

    ui = GeneratedUI(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        title=title,
        prompt=payload.prompt,
        content_html=content_html,
        is_pinned=True,
    )
    db.add(ui)
    await db.commit()
    await db.refresh(ui)

    return {
        "id": str(ui.id),
        "title": ui.title,
        "content_html": ui.content_html,
        "is_pinned": ui.is_pinned,
        "created_at": ui.created_at.isoformat(),
    }


@router.get("/history", response_model=list[GeneratedUIOut])
async def list_generated_uis(
    pinned_only: bool = Query(False),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(GeneratedUI)
        .where(GeneratedUI.tenant_id == current_user.tenant_id)
        .order_by(desc(GeneratedUI.created_at))
        .limit(limit)
        .offset(offset)
    )
    if pinned_only:
        query = query.where(GeneratedUI.is_pinned == True)  # noqa: E712

    result = await db.execute(query)
    uis = result.scalars().all()
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
    result = await db.execute(
        select(GeneratedUI).where(
            GeneratedUI.id == ui_id,
            GeneratedUI.tenant_id == current_user.tenant_id,
        )
    )
    ui = result.scalar_one_or_none()
    if not ui:
        raise HTTPException(status_code=404, detail="Interfaz no encontrada")
    return {
        "id": str(ui.id),
        "title": ui.title,
        "description": ui.description,
        "prompt": ui.prompt,
        "content_html": ui.content_html,
        "is_pinned": ui.is_pinned,
        "created_at": ui.created_at.isoformat(),
    }


@router.patch("/{ui_id}")
async def update_generated_ui(
    ui_id: str,
    payload: UpdateUIRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GeneratedUI).where(
            GeneratedUI.id == ui_id,
            GeneratedUI.tenant_id == current_user.tenant_id,
        )
    )
    ui = result.scalar_one_or_none()
    if not ui:
        raise HTTPException(status_code=404, detail="Interfaz no encontrada")

    if payload.title is not None:
        ui.title = payload.title
    if payload.description is not None:
        ui.description = payload.description
    if payload.is_pinned is not None:
        ui.is_pinned = payload.is_pinned

    await db.commit()
    return {"id": str(ui.id), "title": ui.title, "is_pinned": ui.is_pinned}


@router.delete("/{ui_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generated_ui(
    ui_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(GeneratedUI).where(
            GeneratedUI.id == ui_id,
            GeneratedUI.tenant_id == current_user.tenant_id,
        )
    )
    ui = result.scalar_one_or_none()
    if not ui:
        raise HTTPException(status_code=404, detail="Interfaz no encontrada")
    await db.delete(ui)
    await db.commit()
