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
import asyncio
import uuid
import logging
from datetime import datetime

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


# ── ERP data fetcher ──────────────────────────────────────────────────────────

# Keyword groups → which data to fetch
_KW_INVOICES = {"factura", "facturación", "facturacion", "cobro", "pago", "pendiente", "venta", "ingreso"}
_KW_CLIENTS = {"cliente", "cartera", "crm", "contacto"}
_KW_EMPLOYEES = {"empleado", "plantilla", "rrhh", "personal", "equipo", "trabajador"}
_KW_PRODUCTS = {"producto", "inventario", "stock", "catálogo", "catalogo", "artículo", "articulo"}
_KW_PAYROLLS = {"nómina", "nomina", "salario", "sueldo"}


async def _fetch_erp_context(prompt: str, tenant_id, db: AsyncSession) -> str:
    """Query real ERP data based on prompt keywords. Returns JSON string for LLM context."""
    from app.db.models.billing import Invoice
    from app.db.models.crm import Client
    from app.db.models.hr import Employee, Payroll

    words = set(prompt.lower().split())
    sections: list[str] = []

    # --- Invoices ---
    if words & _KW_INVOICES:
        result = await db.execute(
            select(
                Invoice.invoice_number, Invoice.status,
                Invoice.amount_total, Invoice.date, Invoice.due_date,
            )
            .where(Invoice.tenant_id == tenant_id)
            .order_by(desc(Invoice.created_at))
            .limit(20)
        )
        rows = result.all()
        if rows:
            items = [
                {"numero": r.invoice_number, "estado": r.status,
                 "total": float(r.amount_total or 0),
                 "fecha": r.date.strftime("%Y-%m-%d") if r.date else None,
                 "vencimiento": r.due_date.strftime("%Y-%m-%d") if r.due_date else None}
                for r in rows
            ]
            # Summary
            total = sum(i["total"] for i in items)
            pending = [i for i in items if i["estado"] in ("draft", "sent", "pending")]
            sections.append(
                f"FACTURAS ({len(items)} más recientes, total: {total:.2f}€, "
                f"pendientes: {len(pending)}, importe pendiente: {sum(i['total'] for i in pending):.2f}€):\n"
                + "\n".join(f"  - {i['numero']} | {i['estado']} | {i['total']:.2f}€ | {i['fecha']} | vence {i['vencimiento']}" for i in items)
            )

    # --- Clients ---
    if words & _KW_CLIENTS:
        result = await db.execute(
            select(Client.name, Client.email, Client.phone, Client.city, Client.nif)
            .where(Client.tenant_id == tenant_id)
            .order_by(desc(Client.created_at))
            .limit(20)
        )
        rows = result.all()
        if rows:
            sections.append(
                f"CLIENTES ({len(rows)} más recientes):\n"
                + "\n".join(f"  - {r.name} | {r.nif or '-'} | {r.email or '-'} | {r.phone or '-'} | {r.city or '-'}" for r in rows)
            )

    # --- Employees ---
    if words & _KW_EMPLOYEES:
        result = await db.execute(
            select(Employee.name, Employee.department, Employee.role, Employee.base_salary, Employee.email)
            .where(Employee.tenant_id == tenant_id)
            .order_by(desc(Employee.created_at))
            .limit(20)
        )
        rows = result.all()
        if rows:
            sections.append(
                f"EMPLEADOS ({len(rows)} más recientes):\n"
                + "\n".join(f"  - {r.name} | {r.department or '-'} | {r.role or '-'} | {float(r.base_salary or 0):.2f}€" for r in rows)
            )

    # --- Payrolls ---
    if words & _KW_PAYROLLS:
        result = await db.execute(
            select(Payroll.employee_id, Payroll.period_start, Payroll.period_end,
                   Payroll.gross_salary, Payroll.net_salary, Payroll.status)
            .where(Payroll.tenant_id == tenant_id)
            .order_by(desc(Payroll.period_start))
            .limit(20)
        )
        rows = result.all()
        if rows:
            sections.append(
                f"NÓMINAS ({len(rows)} más recientes):\n"
                + "\n".join(
                    f"  - {r.period_start.strftime('%Y-%m') if r.period_start else '-'} | "
                    f"Bruto {float(r.gross_salary or 0):.2f}€ | Neto {float(r.net_salary or 0):.2f}€ | {r.status}"
                    for r in rows)
            )

    if not sections:
        return ""

    return "\n\n--- DATOS REALES DEL ERP (usa estos datos, NO inventes) ---\n\n" + "\n\n".join(sections)


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
    created_at = Column(DateTime, default=lambda: datetime.utcnow())
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow())


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
2. Si el mensaje incluye "DATOS REALES DEL ERP", USA ESOS DATOS EXACTOS. No inventes cifras ni nombres. Si no hay datos reales, usa datos de ejemplo realistas en español.
3. Usa un estilo visual moderno, oscuro y profesional (fondo oscuro #1a1a2e, bordes sutiles, colores vibrantes para gráficos).
4. Usa SOLO estas etiquetas HTML: div, span, p, table, thead, tbody, tr, td, th, button, b, i, strong, em, h1, h2, h3, h4, ul, ol, li, img, br, hr, a.
5. NO uses <script>, <style>, <iframe>, <form>, <input>, onclick, onerror, ni ningún evento JavaScript.
6. Usa estilos inline (style="...") para todo el diseño. NO references CSS externo.
7. Los botones de acción deben tener el atributo data-erp-action="nombre_accion" y data-payload='{"key":"value"}'.
   Estos botones son de SOLO LECTURA: solo disparan consultas de datos, nunca modifican el ERP.
8. Diseña con responsive en mente: usa flexbox y porcentajes para anchos.
9. Incluye emojis como iconografía accesible (📊 📈 💰 👥 📋 etc).
10. Las tablas deben tener cabeceras claras y datos alineados.

ACCIONES DISPONIBLES (usa estos nombres exactos en data-erp-action):
  - "create-task"   → Crea tarea IA. Payload: {"intent": "descripción de lo que hacer", "domain": "billing|hr|crm|general"}
  - "view-invoice"  → Consulta factura(s) vía IA. Payload: {"id": "uuid"} o {} para listar
  - "view-employee" → Consulta empleado(s) vía IA. Payload: {"id": "uuid"} o {} para listar
  - "navigate"      → Navega a sección del ERP. Payload: {"href": "/ruta"}

Los botones NO navegan a páginas externas — crean tareas IA que consultan datos reales.

EJEMPLOS de botones válidos:
  <button data-erp-action="create-task" data-payload='{"intent":"revisar facturas pendientes","domain":"billing"}' style="...">📋 Revisar facturas</button>
  <button data-erp-action="view-invoice" data-payload='{}' style="...">📄 Ver facturas recientes</button>
  <button data-erp-action="view-employee" data-payload='{}' style="...">👥 Ver plantilla</button>

NUNCA uses:
  <button onclick="...">  ← PROHIBIDO
  <script>...</script>    ← PROHIBIDO
"""


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/debug-llm")
async def debug_llm(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Diagnóstico rápido: verifica que el LLM responde."""
    import shutil
    from app.core.llm_factory import get_llm_for_tenant
    from langchain_core.messages import HumanMessage

    info = {
        "claude_bin_found": shutil.which("claude") or "NOT IN PATH",
        "tenant_id": str(current_user.tenant_id),
    }
    try:
        llm = await get_llm_for_tenant(current_user.tenant_id, db, temperature=0)
        info["llm_class"] = type(llm).__name__
        info["llm_type"] = getattr(llm, "_llm_type", "unknown")

        response = await asyncio.wait_for(
            llm.ainvoke([HumanMessage(content="Responde solo 'OK'")]),
            timeout=30,
        )
        info["response"] = response.content[:200]
        info["status"] = "OK"
    except asyncio.TimeoutError:
        info["status"] = "TIMEOUT (30s)"
    except Exception as e:
        info["status"] = f"ERROR: {type(e).__name__}: {str(e)}"

    return info


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
        # Fetch real ERP data based on prompt keywords
        erp_context = await _fetch_erp_context(payload.prompt, current_user.tenant_id, db)
        user_message = payload.prompt
        if erp_context:
            user_message = f"{payload.prompt}\n\n{erp_context}"

        llm = await get_llm_for_tenant(current_user.tenant_id, db, temperature=0.4)
        logger.info("Generative UI: usando LLM %s para tenant %s", type(llm).__name__, current_user.tenant_id)
        response = await asyncio.wait_for(
            llm.ainvoke([
                SystemMessage(content=_SYSTEM_PROMPT),
                HumanMessage(content=user_message),
            ]),
            timeout=120,
        )
        content_html = response.content
        if not content_html or not content_html.strip():
            raise ValueError("El LLM devolvió una respuesta vacía")
    except asyncio.TimeoutError:
        logger.error("Generative UI: timeout de 120s para tenant %s", current_user.tenant_id)
        raise HTTPException(status_code=504, detail="El modelo de IA tardó demasiado en responder. Inténtalo de nuevo.")
    except ValueError as e:
        logger.error("Generative UI: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generando UI: %s", e, exc_info=True)
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
        "description": ui.description,
        "prompt": ui.prompt,
        "content_html": ui.content_html,
        "is_pinned": ui.is_pinned,
        "created_at": ui.created_at.isoformat(),
        "updated_at": ui.updated_at.isoformat() if ui.updated_at else ui.created_at.isoformat(),
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
