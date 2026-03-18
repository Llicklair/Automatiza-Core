"""
Dispatcher de documentos (documents agent).
"""
import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary
from app.agents.orchestrator.helpers import (
    _save_ai_result_as_document,
    _classify_document_category,
)

logger = logging.getLogger(__name__)


async def _dispatch_documents(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de documentos (OCR + clasificación + subida a Holded)."""
    import uuid

    from sqlalchemy import select

    from app.agents.documents_agent import run_documents_agent
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument, TenantIntegration
    from app.services.encryption import decrypt_credentials

    tenant_id = state["tenant_id"]
    task_id   = state["task_id"]
    azure_endpoint = azure_key = holded_key = None
    file_bytes: bytes | None = None
    file_name: str | None = None
    file_content_type: str | None = None

    async with AsyncSessionLocal() as db:
        # ── Credenciales de Azure (OCR) ──────────────────────────────────
        az_result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                TenantIntegration.integration_type == "azure_forms",
                TenantIntegration.is_active.is_(True),
            )
        )
        az_integration = az_result.scalars().first()
        if az_integration:
            try:
                creds = decrypt_credentials(az_integration.encrypted_credentials)
                azure_endpoint = creds.get("endpoint")
                azure_key      = creds.get("api_key")
            except Exception as e:
                logger.warning("Error al descifrar credenciales de Azure Forms para tenant %s: %s", tenant_id, e)

        # ── Credenciales de Holded (adjunto al contacto) ─────────────────
        hld_result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                TenantIntegration.integration_type == "holded",
                TenantIntegration.is_active.is_(True),
            )
        )
        hld_integration = hld_result.scalars().first()
        if hld_integration:
            try:
                creds = decrypt_credentials(hld_integration.encrypted_credentials)
                holded_key = creds.get("api_key")
            except Exception as e:
                logger.warning("Error al descifrar credenciales de Holded para tenant %s: %s", tenant_id, e)

        # ── Leer el archivo desde disco (buscar por task_id) ─────────────
        doc_result = await db.execute(
            select(TenantDocument).where(TenantDocument.task_id == uuid.UUID(task_id))
        )
        linked_doc = doc_result.scalars().first()
        if linked_doc and linked_doc.file_path:
            try:
                with open(linked_doc.file_path, "rb") as f:
                    file_bytes = f.read()
                file_name = linked_doc.file_name
                file_content_type = linked_doc.file_type or "application/pdf"
            except Exception as e:
                logger.warning("Error al leer archivo del documento vinculado %s desde disco: %s", linked_doc.file_path, e)

    agent_result = await run_documents_agent(
        user_intent=state.get("current_intent", state["user_intent"]),
        file_bytes=file_bytes,
        file_content_type=file_content_type or "application/pdf",
        azure_endpoint=azure_endpoint,
        azure_api_key=azure_key,
        holded_api_key=holded_key,
        holded_file_name=file_name,
        holded_file_content_type=file_content_type,
        tenant_id=tenant_id,
        document_id=task_id,
    )

    holded_info = agent_result.holded_upload or {}

    # Archivar siempre el resultado del análisis de documentos
    await _save_ai_result_as_document(
        tenant_id=tenant_id,
        task_id=state["task_id"],
        category=_classify_document_category(agent_result.document_type),
        title=f"Análisis Documento — {file_name or 'Sin Nombre'}",
        content=(
            f"Tipo detectado: {agent_result.document_type}\n"
            f"Entidades: {agent_result.classified.key_entities if agent_result.classified else 'N/A'}\n"
            f"Acción Holded: {holded_info.get('reason', 'N/A')}"
        )
    )

    _doc_output = {
        "document_type":   agent_result.document_type,
        "classified":      agent_result.classified.model_dump() if agent_result.classified else None,
        "requires_review": agent_result.requires_review,
        "holded_adjunto":  holded_info.get("uploaded", False),
        "holded_contacto": holded_info.get("contact_name", ""),
        "holded_reason":   holded_info.get("reason", ""),
    }
    return {
        "subtask_id": subtask["id"],
        "agent": "documents",
        "success": agent_result.success,
        "output": _doc_output,
        "summary": _format_summary("documents", _doc_output, agent_result.success, agent_result.error),
        "error": agent_result.error,
    }
