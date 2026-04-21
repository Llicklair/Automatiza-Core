"""HR agent — payroll PDF generation helper."""

import logging
import os
from datetime import UTC, datetime
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

        upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
        if not os.path.exists(upload_dir) and os.name == "nt":
            upload_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
            )
        os.makedirs(upload_dir, exist_ok=True)

        file_name = f"Nomina_{employee.name.replace(' ', '_')}_{month}_{year}.pdf"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        new_doc = TenantDocument(
            tenant_id=UUID(tenant_id),
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
