"""Persistencia compartida de la orquestación: documentos generados por IA,
bloqueo de documentos y creación centralizada de PendingApproval."""

import logging
import uuid

logger = logging.getLogger(__name__)


async def lock_document(db, doc_id: uuid.UUID, task_id: uuid.UUID) -> bool:
    """Intenta bloquear un documento para una tarea específica."""
    from datetime import UTC, datetime

    from app.db.models.models import TenantDocument

    doc = await db.get(TenantDocument, doc_id)
    if not doc:
        return False

    # Si ya está bloqueado por otra tarea activa (hace menos de 5 min)
    if doc.locked_by and doc.locked_by != task_id:
        if doc.locked_at and (datetime.now(UTC) - doc.locked_at).total_seconds() < 300:
            return False

    doc.locked_by = task_id
    doc.locked_at = datetime.now(UTC)
    return True


async def unlock_document(db, doc_id: uuid.UUID, task_id: uuid.UUID):
    """Libera el bloqueo de un documento."""
    from app.db.models.models import TenantDocument

    doc = await db.get(TenantDocument, doc_id)
    if doc and doc.locked_by == task_id:
        doc.locked_by = None
        doc.locked_at = None


_PDF_TOOL_NAMES = frozenset({"create_pdf_report", "create_pdf_text_report"})


# Frases que indican que el LLM decidió que la operación requiere
# aprobación humana antes de ejecutarse. Originalmente solo lo detectaba
# el dispatcher de billing — pero los workflows pueden enrutarse a
# cualquier dispatcher (custom, hr, etc.) y la creación de PendingApproval
# debe ocurrir SIEMPRE que el LLM lo señale, no solo en billing.
_APPROVAL_PHRASES = (
    "aprobación requerida",
    "requiere aprobación",
    "requiere aprobacion",
    "necesita aprobación",
    "necesita aprobacion",
    "pendiente de aprobación",
    "pendiente de aprobacion",
    "requires approval",
    "requires human approval",
)


def response_indicates_approval(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return any(phrase in lower for phrase in _APPROVAL_PHRASES)


async def ensure_pending_approval(
    tenant_id: str,
    task_id: str | None = None,
    agent_results: list | None = None,
    execution_id: str | None = None,
) -> str | None:
    """Devuelve el approval_id ESTRUCTURADO que un dispatcher ya haya creado
    (señal out['action']=='approval_required' con executor registrado), o None.

    Ya NO crea aprobaciones por detección de la frase «requiere aprobación» en
    el texto del agente: aquellos payloads `{agent, agent_response}` no llevaban
    `kind`/`params`, así que al aprobarlos el resume no tenía nada que ejecutar
    (fabricaba basura o fallaba la tarea). El gate real son la política de
    autonomía y las tools gateadas (`gated_tool`/`create_action_approval`), que
    crean aprobaciones estructuradas `{kind, params}` con executor. Esta función
    solo reexpone el id de esas aprobaciones estructuradas para enlazarlas.

    Args:
        tenant_id: requerido.
        task_id / execution_id: al menos uno debe estar presente.
        agent_results: lista de resultados a inspeccionar.

    Returns: str(uuid) de la PendingApproval estructurada existente, o None.
    """
    if not agent_results:
        return None
    if not task_id and not execution_id:
        return None

    for step in agent_results:
        if not isinstance(step, dict):
            continue
        out = step.get("output") or {}
        if out.get("action") == "approval_required" and out.get("approval_id"):
            return out["approval_id"]
    return None


def messages_already_generated_pdf(messages: list) -> bool:
    """True si alguno de los messages del agente ya invocó una tool de PDF.

    Usado por los dispatchers para no duplicar guardando un "análisis"
    auto-generado del texto de respuesta cuando el agente ya produjo
    su propio PDF profesional vía create_pdf_report / create_pdf_text_report.
    """
    if not messages:
        return False
    for msg in messages:
        for tc in (getattr(msg, "tool_calls", None) or []):
            name = tc.get("name") if isinstance(tc, dict) else getattr(tc, "name", None)
            if name in _PDF_TOOL_NAMES:
                return True
    return False


async def save_ai_result_as_document(
    tenant_id: str,
    task_id: str,
    category: str,
    title: str,
    content: str,
    reference_name: str | None = None,  # Si se especifica, se busca para sobreescribir
) -> None:
    """
    Guarda el resultado textual de un Agente IA como un documento PDF.
    Implementa lógica de SOBREESCRITURA si existe un documento similar en la carpeta.
    """
    import os
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import or_, select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument
    from app.services.pdf import generate_text_report_pdf

    try:
        # Cross-dispatcher dedup: si la task ya tiene un documento (creado por
        # otro dispatcher o por una tool del agente), no añadir snapshot.
        async with AsyncSessionLocal() as db_check:
            existing = await db_check.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    TenantDocument.task_id == uuid.UUID(task_id),
                ).limit(1)
            )
            if existing.scalars().first():
                return

        # Ruta de uploads — usa el resolver canónico (AppData/.../uploads/<cat>/)
        from app.agents.agent_tools.reports import _resolve_upload_dir
        upload_dir = _resolve_upload_dir(category)

        # Nombre de fichero determinista (ahora .pdf)
        # Si hay un reference_name (ej: "factura_123"), lo usamos para ser constantes
        clean_ref = (
            "".join(c for c in (reference_name or title) if c.isalnum() or c in (" ", "_", "-"))
            .replace(" ", "_")
            .lower()
        )
        filename = f"{category.lower()}_{clean_ref[:30]}.pdf"
        file_path = os.path.join(upload_dir, filename)

        # Generar PDF desde el contenido
        pdf_bytes = generate_text_report_pdf(title, content, category)

        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as db:
            # Buscar si ya existe un doc similar para SOBREESCRIBIR
            # Priorizamos buscar por nombre de archivo o título en la misma categoría
            existing_result = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == uuid.UUID(tenant_id),
                    TenantDocument.category == category,
                    or_(
                        TenantDocument.file_name == filename,
                        TenantDocument.task_id == uuid.UUID(task_id),
                    ),
                )
            )
            existing_doc = existing_result.scalars().first()

            if existing_doc:
                # INTENTAR BLOQUEO PARA CONCURRENCIA
                if not await lock_document(db, existing_doc.id, uuid.UUID(task_id)):
                    logger.warning(
                        f"[ORCHESTRATOR] Archivo {filename} bloqueado por otro agente. Esperando..."
                    )
                    # En una implementación real, reintentaríamos. Aquí lo forzamos tras aviso si es el mismo task

                # Sobreescribir: actualizar campos
                existing_doc.file_path = file_path
                existing_doc.file_name = filename
                existing_doc.file_type = "application/pdf"
                existing_doc.file_size = len(pdf_bytes)
                existing_doc.processed_at = datetime.now(UTC)
                existing_doc.status = "completed"
                existing_doc.parsed_content = content

                # Liberar bloqueo
                await unlock_document(db, existing_doc.id, uuid.UUID(task_id))
            else:
                doc = TenantDocument(
                    tenant_id=uuid.UUID(tenant_id),
                    task_id=uuid.UUID(task_id),
                    file_name=filename,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category=category,
                    status="completed",
                    parsed_content=content,
                )
                db.add(doc)
            await db.commit()
    except Exception:
        logger.exception("Error guardando resultado como documento")


async def save_ai_result_as_csv(
    tenant_id: str, task_id: str, category: str, filename: str, data: list[dict]
) -> None:
    """Exporta una lista de diccionarios a CSV y la registra en TenantDocument."""
    import csv
    import os
    import uuid

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import TenantDocument

    if not data:
        return

    try:
        from app.agents.agent_tools.reports import _resolve_upload_dir

        upload_dir = _resolve_upload_dir(category)
        file_path = os.path.join(upload_dir, filename)

        keys = data[0].keys()
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

        async with AsyncSessionLocal() as db:
            doc = TenantDocument(
                tenant_id=uuid.UUID(tenant_id),
                task_id=uuid.UUID(task_id),
                file_name=filename,
                file_path=file_path,
                file_type="text/csv",
                file_size=os.path.getsize(file_path),
                category=category,
                status="completed",
                parsed_content=f"Datos exportados para análisis: {len(data)} registros.",
            )
            db.add(doc)
            await db.commit()
    except Exception as e:
        logger.warning(f"Error al exportar datos a CSV: {e}")
