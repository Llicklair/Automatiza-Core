"""
Endpoints para gestión de plantillas de documentos (facturas, nóminas, excel).
GET/POST/PUT/DELETE + POST /preview
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.billing import DocumentTemplate
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────


class TemplateCreate(BaseModel):
    name: str
    template_type: str = "invoice"  # invoice | payroll | excel
    layout_style: str = "modern"
    accent_color: str = "#6366f1"
    font_family: str = "helvetica"
    logo_position: str = "left"
    header_style: str = "color_band"
    table_style: str = "striped"
    footer_text: str | None = None
    is_default: bool = False


class TemplateUpdate(BaseModel):
    name: str | None = None
    layout_style: str | None = None
    accent_color: str | None = None
    font_family: str | None = None
    logo_position: str | None = None
    header_style: str | None = None
    table_style: str | None = None
    footer_text: str | None = None
    is_default: bool | None = None


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    template_type: str
    layout_style: str
    accent_color: str
    font_family: str
    logo_position: str
    header_style: str
    table_style: str
    footer_text: str | None
    is_default: bool

    model_config = ConfigDict(from_attributes=True)


class PreviewRequest(BaseModel):
    template_type: str = "invoice"
    layout_style: str = "modern"
    accent_color: str = "#6366f1"
    font_family: str = "helvetica"
    logo_position: str = "left"
    header_style: str = "color_band"
    table_style: str = "striped"
    footer_text: str | None = None


# ── CRUD ─────────────────────────────────────────────────────────────────────


@router.get("", response_model=list[TemplateResponse])
@limiter.limit("30/minute")
async def list_templates(
    request: Request,
    template_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    q = select(DocumentTemplate).where(DocumentTemplate.tenant_id == current_user.tenant_id)
    if template_type:
        q = q.where(DocumentTemplate.template_type == template_type)
    result = await db.execute(q.order_by(DocumentTemplate.created_at))
    return result.scalars().all()


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_template(
    request: Request,
    payload: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    # Si is_default, quitar default anterior del mismo tipo
    if payload.is_default:
        await _clear_default(db, current_user.tenant_id, payload.template_type)

    tpl = DocumentTemplate(
        tenant_id=current_user.tenant_id,
        **payload.model_dump(),
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.put("/{template_id}", response_model=TemplateResponse)
@limiter.limit("30/minute")
async def update_template(
    request: Request,
    template_id: UUID,
    payload: TemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tpl = await _get_or_404(db, template_id, current_user.tenant_id)

    if payload.is_default:
        tpl_type = payload.template_type if hasattr(payload, "template_type") else tpl.template_type
        await _clear_default(db, current_user.tenant_id, tpl_type)

    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(tpl, k, v)

    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_template(
    request: Request,
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tpl = await _get_or_404(db, template_id, current_user.tenant_id)
    await db.delete(tpl)
    await db.commit()


@router.post("/{template_id}/set-default", response_model=TemplateResponse)
@limiter.limit("30/minute")
async def set_default(
    request: Request,
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tpl = await _get_or_404(db, template_id, current_user.tenant_id)
    await _clear_default(db, current_user.tenant_id, tpl.template_type)
    tpl.is_default = True
    await db.commit()
    await db.refresh(tpl)
    return tpl


# ── Seed defaults ────────────────────────────────────────────────────────────

_PRESET_TEMPLATES = [
    {
        "name": "Modern Indigo",
        "layout_style": "modern",
        "accent_color": "#6366f1",
        "font_family": "helvetica",
        "logo_position": "left",
        "header_style": "color_band",
        "table_style": "striped",
    },
    {
        "name": "Classic Green",
        "layout_style": "classic",
        "accent_color": "#10b981",
        "font_family": "times",
        "logo_position": "left",
        "header_style": "line_only",
        "table_style": "bordered",
    },
    {
        "name": "Minimal Slate",
        "layout_style": "minimal",
        "accent_color": "#1e293b",
        "font_family": "helvetica",
        "logo_position": "right",
        "header_style": "none",
        "table_style": "clean",
    },
    {
        "name": "Bold Red",
        "layout_style": "bold",
        "accent_color": "#ef4444",
        "font_family": "helvetica",
        "logo_position": "left",
        "header_style": "dark_band",
        "table_style": "accent_header",
    },
]


@router.post("/seed-defaults", response_model=list[TemplateResponse])
@limiter.limit("30/minute")
async def seed_defaults(
    request: Request,
    template_type: str = "invoice",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crea plantillas preestablecidas para un tipo si el tenant no tiene ninguna."""
    existing = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.tenant_id == current_user.tenant_id,
            DocumentTemplate.template_type == template_type,
        )
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="Ya existen plantillas de este tipo")

    created = []
    for i, preset in enumerate(_PRESET_TEMPLATES):
        tpl = DocumentTemplate(
            tenant_id=current_user.tenant_id,
            template_type=template_type,
            is_default=(i == 0),
            footer_text=None,
            **preset,
        )
        db.add(tpl)
        created.append(tpl)
    await db.commit()
    for tpl in created:
        await db.refresh(tpl)
    return created


# ── Preview ──────────────────────────────────────────────────────────────────


@router.post("/preview")
@limiter.limit("30/minute")
async def preview_template(
    request: Request,
    payload: PreviewRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Genera un PDF de muestra con la configuración de tema enviada."""
    theme_config = payload.model_dump()

    try:
        if payload.template_type == "payroll":
            pdf_bytes = _generate_payroll_sample(theme_config)
        elif payload.template_type == "albaran":
            pdf_bytes = _generate_albaran_sample(theme_config)
        elif payload.template_type == "excel":
            pdf_bytes = _generate_excel_sample(theme_config)
        else:
            pdf_bytes = _generate_invoice_sample(theme_config)
    except Exception as e:
        logger.exception("Error generando preview de plantilla")
        raise HTTPException(status_code=500, detail=f"Error generando preview: {e}")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=preview.pdf"},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _get_or_404(db: AsyncSession, template_id: UUID, tenant_id) -> DocumentTemplate:
    result = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.id == template_id,
            DocumentTemplate.tenant_id == tenant_id,
        )
    )
    tpl = result.scalars().first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return tpl


async def _clear_default(db: AsyncSession, tenant_id, template_type: str):
    result = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.tenant_id == tenant_id,
            DocumentTemplate.template_type == template_type,
            DocumentTemplate.is_default.is_(True),
        )
    )
    for tpl in result.scalars().all():
        tpl.is_default = False


def _generate_invoice_sample(theme_config: dict) -> bytes:
    from app.services.pdf_invoices import generate_invoice_pdf

    return generate_invoice_pdf(
        {
            "number": "F-2026-0042",
            "date": "2026-03-27T00:00:00",
            "company": {
                "name": "Mi Empresa S.L.",
                "nif": "B12345678",
                "address": "Calle Mayor 1, 28001 Madrid",
                "phone": "+34 91 000 0000",
                "email": "contacto@miempresa.es",
            },
            "client": {
                "name": "Cliente Ejemplo S.A.",
                "nif": "A98765432",
                "email": "cliente@ejemplo.com",
                "address": "Avenida de la Constitución 5, 41001 Sevilla",
            },
            "lines": [
                {
                    "description": "Servicio de consultoría empresarial",
                    "quantity": 10,
                    "unit_price": 120.00,
                    "tax_percentage": 21,
                    "total": 1452.00,
                },
                {
                    "description": "Licencia de software anual",
                    "quantity": 1,
                    "unit_price": 850.00,
                    "tax_percentage": 21,
                    "total": 1028.50,
                },
                {
                    "description": "Soporte técnico mensual",
                    "quantity": 3,
                    "unit_price": 200.00,
                    "tax_percentage": 21,
                    "total": 726.00,
                },
            ],
            "amount_base": 2050.00,
            "tax_amount": 430.50,
            "amount_total": 2480.50,
            "payment_terms": "Transferencia bancaria — 30 días neto",
            "notes": "Gracias por confiar en nuestros servicios.",
        },
        theme_config,
    )


def _generate_payroll_sample(theme_config: dict) -> bytes:
    from app.services.pdf_hr import generate_payroll_pdf

    return generate_payroll_pdf(
        {
            "company": {
                "name": "Mi Empresa S.L.",
                "nif": "B12345678",
                "address": "Calle Mayor 1, 28001 Madrid",
            },
            "employee": {
                "name": "Ana García López",
                "nif": "12345678A",
                "position": "Responsable de Operaciones",
                "department": "Administración",
            },
            "period_start": "2026-03-01T00:00:00",
            "period_end": "2026-03-31T00:00:00",
            "issue_date": "2026-03-27T00:00:00",
            "base_salary": 2200.00,
            "ss_contingencias_comunes": 103.40,
            "ss_desempleo": 34.10,
            "ss_formacion_profesional": 2.20,
            "ss_mei": 2.86,
            "irpf": 330.00,
            "irpf_rate": 15.0,
            "other_deductions": 0.0,
            "net_salary": 1727.44,
        },
        theme_config,
    )


def _generate_albaran_sample(theme_config: dict) -> bytes:
    from app.services.pdf_albaranes import generate_albaran_pdf

    return generate_albaran_pdf(
        {
            "albaran_number": "ALB-2026-0015",
            "date": "2026-03-27T00:00:00",
            "status": "confirmed",
            "issuer_name": "Mi Empresa S.L.",
            "issuer_nif": "B12345678",
            "issuer_address": "Calle Mayor 1, 28001 Madrid",
            "client_name": "Cliente Ejemplo S.A.",
            "client_nif": "A98765432",
            "lines": [
                {
                    "description": "Producto A — Lote 2026-03",
                    "quantity": 50,
                    "unit_price": 12.50,
                    "tax_percentage": 21,
                    "total": 756.25,
                },
                {
                    "description": "Producto B — Ref. XK-200",
                    "quantity": 20,
                    "unit_price": 45.00,
                    "tax_percentage": 21,
                    "total": 1089.00,
                },
                {
                    "description": "Embalaje y manipulación",
                    "quantity": 1,
                    "unit_price": 30.00,
                    "tax_percentage": 21,
                    "total": 36.30,
                },
            ],
            "amount_base": 1555.00,
            "tax_amount": 326.55,
            "amount_total": 1881.55,
            "notes": "Mercancía entregada en almacén del cliente. Conforme.",
        },
        theme_config,
    )


def _generate_excel_sample(theme_config: dict) -> bytes:
    from app.services.pdf_invoices import generate_invoice_pdf

    return generate_invoice_pdf(
        {
            "doc_title": "EXPORTACIÓN EXCEL",
            "number": "EXP-2026-0008",
            "date": "2026-03-27T00:00:00",
            "company": {
                "name": "Mi Empresa S.L.",
                "nif": "B12345678",
                "address": "Calle Mayor 1, 28001 Madrid",
                "phone": "+34 91 000 0000",
                "email": "contacto@miempresa.es",
            },
            "client": {
                "name": "Exportación de datos",
                "nif": "",
                "email": "",
                "address": "Vista previa del estilo de tabla",
            },
            "lines": [
                {
                    "description": "Ventas Enero 2026",
                    "quantity": 1,
                    "unit_price": 15200.00,
                    "tax_percentage": 0,
                    "total": 15200.00,
                },
                {
                    "description": "Ventas Febrero 2026",
                    "quantity": 1,
                    "unit_price": 18400.00,
                    "tax_percentage": 0,
                    "total": 18400.00,
                },
                {
                    "description": "Ventas Marzo 2026",
                    "quantity": 1,
                    "unit_price": 12800.00,
                    "tax_percentage": 0,
                    "total": 12800.00,
                },
            ],
            "amount_base": 46400.00,
            "tax_amount": 0.0,
            "amount_total": 46400.00,
            "payment_terms": "",
            "notes": "Datos de ejemplo para vista previa de estilo.",
        },
        theme_config,
    )


async def get_default_theme(tenant_id, template_type: str, db: AsyncSession) -> dict | None:
    """Obtiene la config de la plantilla por defecto de un tipo. Usada por agentes.
    Si ninguna está marcada como default, devuelve la primera disponible del tipo."""
    result = await db.execute(
        select(DocumentTemplate)
        .where(
            DocumentTemplate.tenant_id == tenant_id,
            DocumentTemplate.template_type == template_type,
        )
        .order_by(DocumentTemplate.is_default.desc(), DocumentTemplate.created_at)
    )
    tpl = result.scalars().first()
    if not tpl:
        return None
    return {
        "accent_color": tpl.accent_color,
        "font_family": tpl.font_family,
        "layout_style": tpl.layout_style,
        "logo_position": tpl.logo_position,
        "header_style": tpl.header_style,
        "table_style": tpl.table_style,
        "footer_text": tpl.footer_text,
    }
