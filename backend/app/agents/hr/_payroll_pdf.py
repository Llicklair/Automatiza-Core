"""HR agent — payroll PDF generation helper."""

import asyncio
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import Employee, Tenant, TenantDocument

logger = logging.getLogger(__name__)


async def _generate_and_save_payroll_pdf(
    tenant_id: str,
    employee: Employee,
    payroll_numbers: dict,
    start_date: datetime,
    end_date: datetime,
    month: int,
    year: int,
) -> tuple[str | None, str | None]:
    """Generate payroll PDF, save to disk, register TenantDocument. Returns (document_id, error_msg)."""
    try:
        from app.services.pdf import generate_payroll_pdf

        async with AsyncSessionLocal() as db:
            res_t = await db.execute(select(Tenant).where(Tenant.id == UUID(tenant_id)))
            tenant_obj = res_t.scalar_one_or_none()
            try:
                from app.services.template_service import get_default_theme

                payroll_theme = await get_default_theme(UUID(tenant_id), "payroll", db)
            except Exception as _e:
                logger.warning("Error cargando tema nómina para tenant %s: %s", tenant_id, _e)
                payroll_theme = None

        payroll_pdf_data = {
            "employee": {
                "name": employee.name,
                "nif": employee.nif,
                "position": employee.role or "Empleado",
                "department": employee.department or "General",
            },
            "company": {
                "name": tenant_obj.name if tenant_obj else "Empresa Cliente",
                "nif": "B-00000000",
                "address": "Calle Falsa 123, Madrid",
            },
            "period_start": start_date.isoformat(),
            "period_end": end_date.isoformat(),
            "issue_date": datetime.now(UTC).isoformat(),
            **payroll_numbers,
        }

        pdf_bytes = generate_payroll_pdf(payroll_pdf_data, payroll_theme)

        from app.agents.agent_tools.reports import _resolve_upload_dir
        upload_dir = _resolve_upload_dir("nominas")

        file_name = f"Nomina_{employee.name.replace(' ', '_')}_{month}_{year}.pdf"
        file_path = os.path.join(upload_dir, file_name)
        await asyncio.to_thread(Path(file_path).write_bytes, pdf_bytes)

        # task_id del contexto async — permite que _save_ai_result_as_document
        # (helper compartido) detecte que ya hay PDF para esta task y no
        # genere un snapshot duplicado.
        from app.core.tenant_context import get_current_task
        current_task_id = get_current_task()
        task_uuid = UUID(current_task_id) if current_task_id else None

        new_doc = TenantDocument(
            tenant_id=UUID(tenant_id),
            task_id=task_uuid,
            file_name=file_name,
            file_path=file_path,
            file_type="application/pdf",
            file_size=len(pdf_bytes),
            category="nominas",
            status="completed",
        )
        async with AsyncSessionLocal() as db_doc:
            db_doc.add(new_doc)
            await db_doc.commit()
            await db_doc.refresh(new_doc)
            return str(new_doc.id), None
    except Exception as e:
        return None, str(e)
