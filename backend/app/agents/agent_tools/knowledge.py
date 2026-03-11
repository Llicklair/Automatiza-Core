"""
Herramientas para gestionar la memoria a largo plazo (TenantKnowledge).
Permite a los agentes IA persistir y consultar datos contextuales del tenant.
"""
from uuid import UUID
from langchain_core.tools import tool
from sqlalchemy import select, delete
from app.db.models.models import TenantKnowledge
from app.db.session import SessionLocal

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
        db = SessionLocal()
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
    finally:
        db.close()

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
        db = SessionLocal()
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
    finally:
        db.close()
