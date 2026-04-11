"""
Herramientas para gestionar la memoria a largo plazo (TenantKnowledge).
Permite a los agentes IA persistir y consultar datos contextuales del tenant.
"""
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import delete

from app.agents.agent_tools import get_sync_db
from app.db.models.models import TenantKnowledge


@tool
def get_tenant_knowledge(tenant_id: str, category: str = "all") -> str:
    """
    Consulta la base de conocimientos y preferencias del tenant.
    Util para recordar condiciones de pago, contactos favoritos o reglas de estilo.
    Args:
        tenant_id: ID del tenant
        category: Categoria a filtrar ('all', 'billing', 'hr', 'crm', 'general')
    """
    try:
        with get_sync_db() as db:
            query = db.query(TenantKnowledge).filter(
                TenantKnowledge.tenant_id == UUID(tenant_id)
            )
            if category != "all":
                query = query.filter(TenantKnowledge.category == category)

            facts = query.all()
            if not facts:
                return f"No hay conocimientos registrados para la categoria '{category}'."

            lines = [f"- {f.key}: {f.value} [{f.category}]" for f in facts]
            return f"Memoria del Tenant ({len(facts)} hechos):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error consultando memoria: {e}"

@tool
def delete_tenant_knowledge(tenant_id: str, key: str) -> str:
    """
    Elimina un hecho o preferencia de la memoria del tenant.
    Args:
        tenant_id: ID del tenant
        key: Nombre corto del hecho a eliminar (ej: 'default_client', 'cliente_principal')
    """
    try:
        with get_sync_db() as db:
            result = db.execute(
                delete(TenantKnowledge).where(
                    TenantKnowledge.tenant_id == UUID(tenant_id),
                    TenantKnowledge.key == key,
                )
            )
            db.commit()
            if result.rowcount > 0:
                return f"Hecho '{key}' eliminado de la memoria del tenant."
            return f"No se encontró ningún hecho con la clave '{key}'."
    except Exception as e:
        return f"Error eliminando memoria: {e}"


@tool
def upsert_tenant_knowledge(tenant_id: str, key: str, value: str, category: str = "general") -> str:
    """
    Guarda o actualiza un hecho o preferencia en la memoria del tenant.
    Args:
        tenant_id: ID del tenant
        key: Nombre corto del hecho (ej: 'payment_terms', 'main_contact')
        value: Descripcion o valor del hecho
        category: Categoria (billing, hr, crm, legal, general)
    """
    try:
        with get_sync_db() as db:
            # Buscar si ya existe la llave
            existing = db.query(TenantKnowledge).filter(
                TenantKnowledge.tenant_id == UUID(tenant_id),
                TenantKnowledge.key == key
            ).first()

            if existing:
                existing.value = value
                existing.category = category
                db.commit()
                return f"Hecho '{key}' actualizado en la memoria del tenant."
            else:
                new_fact = TenantKnowledge(
                    tenant_id=UUID(tenant_id),
                    key=key,
                    value=value,
                    category=category
                )
                db.add(new_fact)
                db.commit()
                return f"Hecho '{key}' guardado en la memoria del tenant."
    except Exception as e:
        return f"Error guardando memoria: {e}"
