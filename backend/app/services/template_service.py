"""
Business logic for document template management.
Services raise ValueError / LookupError â€” routes translate to HTTP responses.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import DocumentTemplate

logger = logging.getLogger(__name__)

# â”€â”€ Preset templates â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

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


# â”€â”€ Internal helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def _get_or_raise(db: AsyncSession, template_id: UUID, tenant_id) -> DocumentTemplate:
    result = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.id == template_id,
            DocumentTemplate.tenant_id == tenant_id,
        )
    )
    tpl = result.scalars().first()
    if not tpl:
        raise LookupError("Plantilla no encontrada")
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


# â”€â”€ CRUD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def list_templates(
    db: AsyncSession, tenant_id, template_type: str | None = None
) -> list[DocumentTemplate]:
    q = select(DocumentTemplate).where(DocumentTemplate.tenant_id == tenant_id)
    if template_type:
        q = q.where(DocumentTemplate.template_type == template_type)
    result = await db.execute(q.order_by(DocumentTemplate.created_at))
    return list(result.scalars().all())


async def create_template(db: AsyncSession, tenant_id, data: dict) -> DocumentTemplate:
    if data.get("is_default"):
        await _clear_default(db, tenant_id, data.get("template_type", "invoice"))

    tpl = DocumentTemplate(tenant_id=tenant_id, **data)
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def update_template(
    db: AsyncSession, template_id: UUID, tenant_id, data: dict
) -> DocumentTemplate:
    tpl = await _get_or_raise(db, template_id, tenant_id)

    if data.get("is_default"):
        tpl_type = data.get("template_type", tpl.template_type)
        await _clear_default(db, tenant_id, tpl_type)

    for k, v in data.items():
        setattr(tpl, k, v)

    await db.commit()
    await db.refresh(tpl)
    return tpl


async def delete_template(db: AsyncSession, template_id: UUID, tenant_id) -> None:
    tpl = await _get_or_raise(db, template_id, tenant_id)
    db.delete(tpl)
    await db.commit()


async def set_default(db: AsyncSession, template_id: UUID, tenant_id) -> DocumentTemplate:
    tpl = await _get_or_raise(db, template_id, tenant_id)
    await _clear_default(db, tenant_id, tpl.template_type)
    tpl.is_default = True
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def seed_defaults(
    db: AsyncSession, tenant_id, template_type: str = "invoice"
) -> list[DocumentTemplate]:
    existing = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.tenant_id == tenant_id,
            DocumentTemplate.template_type == template_type,
        )
    )
    if existing.scalars().first():
        raise ValueError("Ya existen plantillas de este tipo")

    created: list[DocumentTemplate] = []
    for i, preset in enumerate(_PRESET_TEMPLATES):
        tpl = DocumentTemplate(
            tenant_id=tenant_id,
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


# â”€â”€ Preview PDF generation â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


def generate_preview(theme_config: dict) -> bytes:
    """Generate a sample PDF with the given theme configuration."""
    template_type = theme_config.get("template_type", "invoice")

    if template_type == "payroll":
        return _generate_payroll_sample(theme_config)
    elif template_type == "albaran":
        return _generate_albaran_sample(theme_config)
    elif template_type == "excel":
        return _generate_excel_sample(theme_config)
    else:
        return _generate_invoice_sample(theme_config)


def _generate_invoice_sample(theme_config: dict) -> bytes:
    from app.services.pdf import generate_invoice_pdf

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
                "address": "Avenida de la Constitucion 5, 41001 Sevilla",
            },
            "lines": [
                {
                    "description": "Servicio de consultoria empresarial",
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
                    "description": "Soporte tecnico mensual",
                    "quantity": 3,
                    "unit_price": 200.00,
                    "tax_percentage": 21,
                    "total": 726.00,
                },
            ],
            "amount_base": 2050.00,
            "tax_amount": 430.50,
            "amount_total": 2480.50,
            "payment_terms": "Transferencia bancaria -- 30 dias neto",
            "notes": "Gracias por confiar en nuestros servicios.",
        },
        theme_config,
    )


def _generate_payroll_sample(theme_config: dict) -> bytes:
    from app.services.pdf import generate_payroll_pdf

    return generate_payroll_pdf(
        {
            "company": {
                "name": "Mi Empresa S.L.",
                "nif": "B12345678",
                "address": "Calle Mayor 1, 28001 Madrid",
            },
            "employee": {
                "name": "Ana Garcia Lopez",
                "nif": "12345678A",
                "position": "Responsable de Operaciones",
                "department": "Administracion",
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
    from app.services.pdf import generate_albaran_pdf

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
                    "description": "Producto A -- Lote 2026-03",
                    "quantity": 50,
                    "unit_price": 12.50,
                    "tax_percentage": 21,
                    "total": 756.25,
                },
                {
                    "description": "Producto B -- Ref. XK-200",
                    "quantity": 20,
                    "unit_price": 45.00,
                    "tax_percentage": 21,
                    "total": 1089.00,
                },
                {
                    "description": "Embalaje y manipulacion",
                    "quantity": 1,
                    "unit_price": 30.00,
                    "tax_percentage": 21,
                    "total": 36.30,
                },
            ],
            "amount_base": 1555.00,
            "tax_amount": 326.55,
            "amount_total": 1881.55,
            "notes": "Mercancia entregada en almacen del cliente. Conforme.",
        },
        theme_config,
    )


def _generate_excel_sample(theme_config: dict) -> bytes:
    from app.services.pdf import generate_invoice_pdf

    return generate_invoice_pdf(
        {
            "doc_title": "EXPORTACION EXCEL",
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
                "name": "Exportacion de datos",
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


# â”€â”€ Shared utility (used by agents and other services) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def get_default_theme(tenant_id, template_type: str, db: AsyncSession) -> dict | None:
    """Return theme config for the default template of a type.
    Falls back to the first available template if none is marked default."""
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
