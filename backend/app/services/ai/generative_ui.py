"""Servicio de dominio para Generative UI.

Encapsula la lógica de negocio: keyword matching, consultas ERP,
llamadas al LLM y persistencia de interfaces generadas.
"""

import asyncio
import logging
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.generative_ui import GeneratedUI
from app.prompts import load_prompt

logger = logging.getLogger(__name__)

# â”€â”€ Keyword sets para resolución de contexto ERP â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_KW_INVOICES = {
    "factura",
    "facturación",
    "facturacion",
    "cobro",
    "pago",
    "pendiente",
    "venta",
    "ingreso",
}
_KW_CLIENTS = {"cliente", "cartera", "crm", "contacto"}
_KW_EMPLOYEES = {"empleado", "plantilla", "rrhh", "personal", "equipo", "trabajador"}
_KW_PAYROLLS = {"nómina", "nomina", "salario", "sueldo"}


# â”€â”€ Funciones de servicio â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def fetch_erp_context(prompt: str, tenant_id, db: AsyncSession) -> str:
    """Consulta datos reales del ERP según keywords del prompt.

    Returns formatted string for LLM context, or empty string if no match.
    """
    from app.db.models.billing import Invoice
    from app.db.models.crm import Client
    from app.db.models.hr import Employee, Payroll

    words = set(prompt.lower().split())
    sections: list[str] = []

    # --- Facturas ---
    if words & _KW_INVOICES:
        result = await db.execute(
            select(
                Invoice.invoice_number,
                Invoice.status,
                Invoice.amount_total,
                Invoice.date,
                Invoice.due_date,
            )
            .where(Invoice.tenant_id == tenant_id)
            .order_by(desc(Invoice.created_at))
            .limit(20)
        )
        rows = result.all()
        if rows:
            items = [
                {
                    "numero": r.invoice_number,
                    "estado": r.status,
                    "total": float(r.amount_total or 0),
                    "fecha": r.date.strftime("%Y-%m-%d") if r.date else None,
                    "vencimiento": r.due_date.strftime("%Y-%m-%d") if r.due_date else None,
                }
                for r in rows
            ]
            total = sum(i["total"] for i in items)
            pending = [i for i in items if i["estado"] in ("draft", "sent", "pending")]
            sections.append(
                f"FACTURAS ({len(items)} más recientes, total: {total:.2f}â‚¬, "
                f"pendientes: {len(pending)}, importe pendiente: {sum(i['total'] for i in pending):.2f}â‚¬):\n"
                + "\n".join(
                    f"  - {i['numero']} | {i['estado']} | {i['total']:.2f}â‚¬ | {i['fecha']} | vence {i['vencimiento']}"
                    for i in items
                )
            )

    # --- Clientes ---
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
                + "\n".join(
                    f"  - {r.name} | {r.nif or '-'} | {r.email or '-'} | {r.phone or '-'} | {r.city or '-'}"
                    for r in rows
                )
            )

    # --- Empleados ---
    if words & _KW_EMPLOYEES:
        result = await db.execute(
            select(
                Employee.name,
                Employee.department,
                Employee.role,
                Employee.base_salary,
                Employee.email,
            )
            .where(Employee.tenant_id == tenant_id)
            .order_by(desc(Employee.created_at))
            .limit(20)
        )
        rows = result.all()
        if rows:
            sections.append(
                f"EMPLEADOS ({len(rows)} más recientes):\n"
                + "\n".join(
                    f"  - {r.name} | {r.department or '-'} | {r.role or '-'} | {float(r.base_salary or 0):.2f}â‚¬"
                    for r in rows
                )
            )

    # --- Nóminas ---
    if words & _KW_PAYROLLS:
        result = await db.execute(
            select(
                Payroll.employee_id,
                Payroll.period_start,
                Payroll.period_end,
                Payroll.gross_salary,
                Payroll.net_salary,
                Payroll.status,
            )
            .where(Payroll.tenant_id == tenant_id)
            .order_by(desc(Payroll.period_start))
            .limit(20)
        )
        rows = result.all()
        if rows:
            sections.append(
                f"NÃ“MINAS ({len(rows)} más recientes):\n"
                + "\n".join(
                    f"  - {r.period_start.strftime('%Y-%m') if r.period_start else '-'} | "
                    f"Bruto {float(r.gross_salary or 0):.2f}â‚¬ | Neto {float(r.net_salary or 0):.2f}â‚¬ | {r.status}"
                    for r in rows
                )
            )

    if not sections:
        return ""

    return "\n\n--- DATOS REALES DEL ERP (usa estos datos, NO inventes) ---\n\n" + "\n\n".join(
        sections
    )


async def generate_ui(
    prompt: str,
    tenant_id,
    db: AsyncSession,
    title: str | None = None,
) -> GeneratedUI:
    """Genera HTML via LLM y lo persiste.

    Raises:
        asyncio.TimeoutError: LLM tardó más de 120s.
        ValueError: LLM devolvió respuesta vacía.
    """
    from langchain_core.messages import HumanMessage, SystemMessage

    from app.core.llm_factory import get_llm_for_tenant

    erp_context = await fetch_erp_context(prompt, tenant_id, db)
    user_message = f"{prompt}\n\n{erp_context}" if erp_context else prompt

    system_prompt = load_prompt("generative_ui")

    llm = await get_llm_for_tenant(tenant_id, db, temperature=0.4)
    logger.info(
        "Generative UI: usando LLM %s para tenant %s",
        type(llm).__name__,
        tenant_id,
    )
    response = await asyncio.wait_for(
        llm.ainvoke(
            [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message),
            ]
        ),
        timeout=120,
    )

    content_html = response.content
    if not content_html or not content_html.strip():
        raise ValueError("El LLM devolvió una respuesta vacía")

    resolved_title = title or f"Interfaz â€” {prompt[:60]}{'...' if len(prompt) > 60 else ''}"

    ui = GeneratedUI(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        title=resolved_title,
        prompt=prompt,
        content_html=content_html,
        is_pinned=True,
    )
    db.add(ui)
    await db.commit()
    await db.refresh(ui)
    return ui


async def debug_llm(tenant_id, db: AsyncSession) -> dict:
    """Diagnóstico rápido: verifica que el LLM responde."""
    import shutil

    from langchain_core.messages import HumanMessage

    from app.core.llm_factory import get_llm_for_tenant

    info: dict = {
        "claude_bin_found": shutil.which("claude") or "NOT IN PATH",
        "tenant_id": str(tenant_id),
    }
    try:
        llm = await get_llm_for_tenant(tenant_id, db, temperature=0)
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


async def list_uis(
    tenant_id,
    db: AsyncSession,
    *,
    pinned_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[GeneratedUI]:
    """Lista interfaces generadas de un tenant."""
    query = (
        select(GeneratedUI)
        .where(GeneratedUI.tenant_id == tenant_id)
        .order_by(desc(GeneratedUI.created_at))
        .limit(limit)
        .offset(offset)
    )
    if pinned_only:
        query = query.where(GeneratedUI.is_pinned == True)  # noqa: E712

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_ui(ui_id: str, tenant_id, db: AsyncSession) -> GeneratedUI | None:
    """Obtiene una interfaz por id, scoped al tenant."""
    result = await db.execute(
        select(GeneratedUI).where(
            GeneratedUI.id == ui_id,
            GeneratedUI.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def update_ui(
    ui_id: str,
    tenant_id,
    db: AsyncSession,
    *,
    title: str | None = None,
    description: str | None = None,
    is_pinned: bool | None = None,
) -> GeneratedUI | None:
    """Actualización parcial de una interfaz. Retorna None si no existe."""
    ui = await get_ui(ui_id, tenant_id, db)
    if not ui:
        return None
    if title is not None:
        ui.title = title
    if description is not None:
        ui.description = description
    if is_pinned is not None:
        ui.is_pinned = is_pinned
    await db.commit()
    return ui


async def delete_ui(ui_id: str, tenant_id, db: AsyncSession) -> bool:
    """Elimina una interfaz. Retorna False si no existe."""
    ui = await get_ui(ui_id, tenant_id, db)
    if not ui:
        return False
    await db.delete(ui)
    await db.commit()
    return True
