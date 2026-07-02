"""Node handlers: init_tenant_node and load_knowledge_node."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.agents.orchestrator.state import OrchestratorState, TaskStatus
from app.core.llm_factory import get_llm_for_tenant, set_tenant_llm_context
from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantKnowledge, TenantLlmConfig
from app.services.encryption import decrypt_credentials

logger = logging.getLogger(__name__)


async def init_tenant_node(state: OrchestratorState) -> dict:
    """Carga el LLM del tenant en el ContextVar ANTES de cualquier nodo que use LLM.
    Valida que el proveedor esté habilitado y tenga credenciales."""
    tenant_id = state.get("tenant_id")
    if not tenant_id:
        return {
            "status": TaskStatus.FAILED,
            "error_message": "Falta tenant_id — no se puede ejecutar sin contexto de empresa",
        }

    # Defensa multi-tenant: setear el ContextVar para que TODAS las tools
    # invocadas en este flujo (orchestrator + built-in + custom) usen este
    # tenant_id, ignorando cualquier valor que el LLM intente pasar.
    from app.agents.tenant_context import set_active_tenant

    set_active_tenant(tenant_id)

    try:
        async with AsyncSessionLocal() as db:
            cfg_result = await db.execute(select(TenantLlmConfig).where(TenantLlmConfig.tenant_id == UUID(tenant_id)))
            cfg = cfg_result.scalar_one_or_none()
            if cfg and cfg.encrypted_keys:
                keys = decrypt_credentials(cfg.encrypted_keys)
                provider = cfg.active_llm_provider
                pdata = keys.get(provider, {})
                if not pdata.get("enabled", True):
                    return {
                        "status": TaskStatus.FAILED,
                        "error_message": (
                            f"El proveedor de IA '{provider}' está desactivado. "
                            "Actívalo en Configuración → API Keys."
                        ),
                    }
                _tenant_llm = await get_llm_for_tenant(tenant_id, db, temperature=0)
                set_tenant_llm_context(_tenant_llm, provider)
                logger.info("[INIT] LLM del tenant cargado: provider=%s", provider)
            else:
                logger.info("[INIT] Sin config LLM para tenant %s, usando global", tenant_id)
    except ValueError:
        raise
    except Exception as e:
        logger.warning("No se pudo precargar LLM del tenant: %s", e)

    return {}


async def load_knowledge_node(state: OrchestratorState) -> dict:
    """Carga hechos y preferencias del TenantKnowledge para inyectar en el contexto."""
    tenant_id = state.get("tenant_id")
    if not tenant_id:
        return {"tenant_knowledge": []}

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TenantKnowledge).where(TenantKnowledge.tenant_id == UUID(tenant_id)))
            facts = result.scalars().all()
            knowledge_list = [{"key": f.key, "value": f.value, "category": f.category} for f in facts]
            return {
                "tenant_knowledge": knowledge_list,
                "additional_metadata": {
                    **(state.get("additional_metadata") or {}),
                    "started_at": datetime.now(UTC).isoformat(),
                },
            }
    except Exception as e:
        logger.warning(f"Error cargando conocimiento: {e}")
        return {
            "tenant_knowledge": [],
            "additional_metadata": {
                **(state.get("additional_metadata") or {}),
                "started_at": datetime.now(UTC).isoformat(),
            },
        }
