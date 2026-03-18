"""
Dispatcher de facturación (billing agent).
"""
import logging
from datetime import UTC, datetime, timedelta

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary
from app.agents.orchestrator.helpers import (
    _lock_document,
    _unlock_document,
    _save_ai_result_as_document,
    _save_ai_result_as_csv,
)

logger = logging.getLogger(__name__)


async def _dispatch_billing(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el billing agent y traduce su resultado al formato del orquestador."""
    import uuid

    from sqlalchemy import select

    from app.agents.billing_agent import run_billing_agent
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import PendingApproval, TenantIntegration
    from app.services.encryption import decrypt_credentials

    tenant_id = state["tenant_id"]

    # Obtener API key de Holded si está configurada (opcional — modo local funciona sin Holded)
    holded_api_key: str | None = None
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                TenantIntegration.integration_type == "holded",
                TenantIntegration.is_active.is_(True),
            )
        )
        integration = result.scalars().first()

    if integration:
        try:
            creds = decrypt_credentials(integration.encrypted_credentials)
            holded_api_key = creds.get("api_key")
        except Exception:
            holded_api_key = None  # Fallo al descifrar → modo local

    agent_result = await run_billing_agent(
        user_intent=state.get("current_intent", state["user_intent"]),
        tenant_id=tenant_id,
        holded_api_key=holded_api_key,
        task_id=state["task_id"],
    )

    if agent_result.action == "approval_required":
        # Guardar en BD para que el dashboard lo muestre
        async with AsyncSessionLocal() as db:
            approval = PendingApproval(
                task_id=uuid.UUID(state["task_id"]),
                tenant_id=uuid.UUID(tenant_id),
                action_description=(
                    f"Crear factura de {agent_result.extracted_data.get('amount_base', '?')}€ "
                    f"+ IVA {agent_result.extracted_data.get('vat_rate', '?')}% "
                    f"a {agent_result.extracted_data.get('client_name', '?')}"
                ),
                action_payload=agent_result.extracted_data or {},
                risk_level="high",
                expires_at=datetime.now(UTC) + timedelta(hours=2),
            )
            db.add(approval)
            await db.commit()
            await db.refresh(approval)
            approval_id = str(approval.id)

        return {
            "subtask_id": subtask["id"],
            "agent": "billing",
            "success": True,
            "output": {"action": "approval_required", "approval_id": approval_id},
            "error": None,
        }

    _billing_output = {
        "action": agent_result.action,
        "holded_invoice_id": agent_result.holded_invoice_id,
        "extracted_data": agent_result.extracted_data,
        "warnings": agent_result.validation_warnings,
    }
    _billing_error = agent_result.error or (
        "; ".join(agent_result.validation_errors) if agent_result.validation_errors else None
    )
    billing_result = {
        "subtask_id": subtask["id"],
        "agent": "billing",
        "success": agent_result.success,
        "output": _billing_output,
        "summary": _format_summary("billing", _billing_output, agent_result.success, _billing_error),
        "error": _billing_error,
    }

    # Guardar resultado como documento PDF si fue exitoso (factura)
    if agent_result.success and agent_result.action == "draft_created":
        await _save_billing_result_as_pdf(
            state=state,
            agent_result=agent_result,
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
        )

    # Exportar a CSV si es un informe/consulta para que Excel pueda cruzarlo
    if agent_result.success and agent_result.action == "summary" and "invoices" in agent_result.extracted_data:
        # 1. Guardar CSV para procesamiento del agente de Excel
        await _save_ai_result_as_csv(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="facturas",
            filename=f"listado_facturas_{state['task_id'][:8]}.csv",
            data=agent_result.extracted_data["invoices"]
        )
        # 2. Guardar reporte legible en el Scanner (carpeta Facturas)
        invoices_text = "\n".join([
            f"- {i['numero']}: {i['cliente']} ({i['total']}€) - {i['estado']}"
            for i in agent_result.extracted_data["invoices"]
        ])
        await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=state["task_id"],
            category="facturas",
            title=f"Listado de Facturas — {state['task_id'][:8]}",
            content=f"Reporte de facturación solicitado.\nTotal facturado: {agent_result.extracted_data.get('total', 0)}€\n\nDetalle:\n{invoices_text}"
        )

    return billing_result


async def _save_billing_result_as_pdf(
    state: OrchestratorState,
    agent_result,
    tenant_id: str,
    task_id: str,
) -> None:
    """
    Genera un PDF real de la factura creada por el billing agent IA
    y lo registra en TenantDocument (categoría 'facturas').
    Si ya existe un documento con el mismo task_id, lo sobreescribe.
    """
    import os
    import uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Tenant, TenantDocument
    from app.services.pdf_service import generate_invoice_pdf

    try:
        data = agent_result.extracted_data or {}
        _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
        upload_dir = os.path.normpath(os.path.join(_THIS_DIR, "..", "..", "uploads"))
        os.makedirs(upload_dir, exist_ok=True)

        # Datos de la empresa emisora: priorizar los que vengan del prompt (issuer_*),
        # y si no existen, usar los del tenant como valor por defecto.
        async with AsyncSessionLocal() as db:
            tenant_obj = await db.get(Tenant, uuid.UUID(tenant_id))
        company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
        company_nif = data.get("issuer_nif") or (tenant_obj.nif if tenant_obj else "B00000000")
        company_address = data.get("issuer_address") or "Calle Principal, 1 · Madrid"
        company_email = data.get("issuer_email") or ""

        # Nombre de fichero determinista para poder sobreescribir en actualizaciones IA
        # Si los datos traen un número de factura real, lo usamos como clave de sobreescritura
        invoice_ref = data.get("invoice_number") or f"ia_{task_id[:8]}"
        filename = f"factura_{invoice_ref.replace('/', '_').lower()}.pdf"
        file_path = os.path.join(upload_dir, filename)

        # Construir datos para el PDF
        invoice_number = f"IA-{task_id[:8].upper()}"
        invoice_data = {
            "number": invoice_number,
            "date": data.get("invoice_date") or datetime.now().strftime("%Y-%m-%d"),
            "amount_base": float(data.get("amount_base") or 0),
            "tax_amount": round(
                float(data.get("amount_base") or 0) * float(data.get("vat_rate") or 21) / 100, 2
            ),
            "amount_total": round(
                float(data.get("amount_base") or 0) * (1 + float(data.get("vat_rate") or 21) / 100), 2
            ),
            "client": {
                "name": data.get("client_name") or "Cliente",
                "nif": data.get("client_nif") or "",
                "email": "",
                "address": "",
            },
            "company": {
                "name": company_name,
                "nif": company_nif,
                "address": company_address,
                "phone": "",
                "email": company_email,
            },
            "lines": [
                {
                    "description": data.get("concept") or "Servicio",
                    "quantity": 1.0,
                    "unit_price": float(data.get("amount_base") or 0),
                    "tax_percentage": float(data.get("vat_rate") or 21),
                    "total": round(
                        float(data.get("amount_base") or 0) * (1 + float(data.get("vat_rate") or 21) / 100), 2
                    ),
                }
            ],
        }
        if data.get("notes"):
            invoice_data["notes"] = data["notes"]
        if data.get("payment_terms") or data.get("payment_method"):
            invoice_data["payment_terms"] = data.get("payment_terms") or data.get("payment_method")

        pdf_bytes = generate_invoice_pdf(invoice_data)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as db:
            from sqlalchemy import or_
            existing_result = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    TenantDocument.category == "facturas",
                    or_(
                        TenantDocument.file_name == filename,
                        TenantDocument.task_id == uuid.UUID(task_id)
                    )
                )
            )
            existing_doc = existing_result.scalars().first()

            if existing_doc:
                # Bloqueo para concurrencia
                if not await _lock_document(db, existing_doc.id, uuid.UUID(task_id)):
                    logger.warning(f"[ORCHESTRATOR] Factura {filename} bloqueada. Reintentando...")

                # Sobreescribir el PDF existente
                existing_doc.file_path = file_path
                existing_doc.file_name = filename
                existing_doc.file_type = "application/pdf"
                existing_doc.file_size = len(pdf_bytes)
                existing_doc.processed_at = datetime.now(UTC)
                existing_doc.status = "completed"
                parsed = (
                    f"Factura IA: {invoice_number}\n"
                    f"Cliente: {data.get('client_name', 'N/A')}\n"
                    f"Concepto: {data.get('concept', 'N/A')}\n"
                    f"Base: {data.get('amount_base', 0)}€  IVA: {data.get('vat_rate', 21)}%\n"
                    f"Total: {invoice_data['amount_total']:.2f}€"
                )
                existing_doc.parsed_content = parsed
                # Desbloqueo
                await _unlock_document(db, existing_doc.id, uuid.UUID(task_id))
            else:
                parsed = (
                    f"Factura IA: {invoice_number}\n"
                    f"Cliente: {data.get('client_name', 'N/A')}\n"
                    f"Concepto: {data.get('concept', 'N/A')}\n"
                    f"Base: {data.get('amount_base', 0)}€  IVA: {data.get('vat_rate', 21)}%\n"
                    f"Total: {invoice_data['amount_total']:.2f}€"
                )
                doc = TenantDocument(
                    tenant_id=uuid.UUID(tenant_id),
                    task_id=uuid.UUID(task_id),
                    file_name=filename,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category="facturas",
                    status="completed",
                    parsed_content=parsed,
                )
                db.add(doc)
            await db.commit()
    except Exception:
        import traceback
        traceback.print_exc()
