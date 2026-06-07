"""
Herramientas del agente CRM.
"""

from datetime import UTC, datetime
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.agents.agent_tools.clients import search_client
from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.reports import create_pdf_report, create_pdf_text_report
from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Opportunity

# ─── Etapas del embudo (única fuente de verdad) ──────────────────────────────
# Debe coincidir con el frontend (crm/embudo-de-ventas) y el tipo de la API
# (frontend/src/lib/api/crm.ts). Si añades una etapa, actualízala también allí.
VALID_STAGES: tuple[str, ...] = ("new", "qualified", "proposal", "won", "lost")
_STAGES_HELP = ", ".join(f"'{s}'" for s in VALID_STAGES)

# ─── Herramientas ────────────────────────────────────────────────────────────


@tool
async def list_opportunities(tenant_id: str, stage: str = "all") -> str:
    """
    Lista las oportunidades de venta del CRM, opcionalmente filtradas por fase.
    Args:
        tenant_id: ID del tenant
        stage: Fase a filtrar ('new', 'qualified', 'proposal', 'won', 'lost', 'all')
    """
    return await _list_opportunities_async(tenant_id, stage)


async def _list_opportunities_async(tenant_id: str, stage: str) -> str:
    try:
        async with AsyncSessionLocal() as db:
            query = (
                select(Opportunity)
                .filter(Opportunity.tenant_id == UUID(tenant_id))
                .options(selectinload(Opportunity.client))
            )
            if stage != "all":
                query = query.filter(Opportunity.stage == stage)
            query = query.order_by(Opportunity.created_at.desc())
            result = await db.execute(query)
            opps = result.scalars().all()

            if not opps:
                return f"No hay oportunidades{' en la fase ' + stage if stage != 'all' else ''}."

            lines = []
            for opp in opps:
                client_name = opp.client.name if opp.client else "Cliente desconocido"
                lines.append(
                    f"- [{opp.stage.upper()}] {opp.title} | "
                    f"Cliente: {client_name} | "
                    f"Valor: {float(opp.expected_value or 0):.2f}EUR | "
                    f"ID: {opp.id}"
                )
            return f"Oportunidades ({len(opps)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listando oportunidades: {str(e)}"


@tool
async def create_opportunity(
    tenant_id: str, client_nif: str, title: str, expected_value: float = 0, stage: str = "new"
) -> str:
    """
    Crea una nueva Oportunidad de Venta (Lead) en el CRM para un cliente existente.
    Args:
        tenant_id: ID del tenant
        client_nif: NIF del cliente/lead
        title: Nombre de la oportunidad
        expected_value: Valor esperado en euros
        stage: Fase ('new', 'qualified', 'proposal', 'won', 'lost')
    """
    # Validate inputs
    try:
        _val = float(expected_value) if isinstance(expected_value, str) else expected_value
        if _val < 0:
            return f"Error: el valor esperado no puede ser negativo (recibido: {expected_value})."
        expected_value = _val
    except (ValueError, TypeError):
        return f"Error: valor esperado inválido '{expected_value}'. Debe ser un número."

    if stage not in VALID_STAGES:
        return f"Error: etapa inválida '{stage}'. Opciones válidas: {_STAGES_HELP}."

    return await _create_opportunity_async(tenant_id, client_nif, title, expected_value, stage)


async def _create_opportunity_async(
    tenant_id: str, client_nif: str, title: str, expected_value: float, stage: str
) -> str:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Client).filter(Client.tenant_id == UUID(tenant_id), Client.nif == client_nif)
            )
            client = result.scalars().first()

            if not client:
                return f"Error: No se encontro ningun cliente con NIF {client_nif}. Verifica el NIF o usa list_clients."

            opp = Opportunity(
                tenant_id=UUID(tenant_id),
                client_id=client.id,
                title=title,
                expected_value=expected_value,
                stage=stage,
            )
            db.add(opp)
            await db.commit()
            await db.refresh(opp)
            return f"Oportunidad '{title}' creada para {client.name} en fase '{stage}'. Valor: {expected_value}EUR. ID: {opp.id}"
    except Exception as e:
        return f"Error creando oportunidad: {str(e)}"


@tool
async def update_opportunity_stage(
    tenant_id: str, opportunity_id: str, new_stage: str, notes: str = ""
) -> str:
    """
    Mueve una Oportunidad de Venta de una fase a otra en el Embudo.
    Args:
        tenant_id: ID del tenant
        opportunity_id: ID de la oportunidad a mover
        new_stage: Nueva fase ('new', 'qualified', 'proposal', 'won', 'lost')
        notes: Nota opcional sobre el cambio de etapa
    """
    if new_stage not in VALID_STAGES:
        return f"Error: Fase '{new_stage}' invalida. Usa una de: {_STAGES_HELP}."

    return await _update_opportunity_stage_async(tenant_id, opportunity_id, new_stage, notes)


async def _update_opportunity_stage_async(
    tenant_id: str, opportunity_id: str, new_stage: str, notes: str
) -> str:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Opportunity).filter(
                    Opportunity.tenant_id == UUID(tenant_id), Opportunity.id == UUID(opportunity_id)
                )
            )
            opp = result.scalars().first()

            if not opp:
                return f"Error: Oportunidad con ID {opportunity_id} no encontrada."

            old_stage = opp.stage
            opp.stage = new_stage

            await db.commit()

            msg = f"Oportunidad '{opp.title}' movida de '{old_stage}' a '{new_stage}'."
            if notes:
                msg += f" Nota: {notes}"
            return msg
    except Exception as e:
        return f"Error actualizando oportunidad: {str(e)}"


@tool
async def qualify_leads(tenant_id: str) -> str:
    """
    Analiza todas las oportunidades en fase 'new' y sugiere cuáles cualificar
    basándose en el valor esperado y el tiempo en pipeline.
    Args:
        tenant_id: ID del tenant
    """
    return await _qualify_leads_async(tenant_id)


async def _qualify_leads_async(tenant_id: str) -> str:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Opportunity).filter(
                    Opportunity.tenant_id == UUID(tenant_id), Opportunity.stage == "new"
                )
            )
            new_opps = result.scalars().all()

            if not new_opps:
                return "No hay leads en fase 'new' para analizar."

            suggestions = []
            for opp in new_opps:
                if opp.created_at:
                    now = datetime.now(UTC)
                    op_date = opp.created_at
                    if op_date.tzinfo is None:
                        op_date = op_date.replace(tzinfo=UTC)
                    days_in_pipeline = (now - op_date).days
                else:
                    days_in_pipeline = 0

                value = float(opp.expected_value or 0)

                if value > 5000 or days_in_pipeline < 7:
                    priority = "ALTA"
                    action = "Cualificar ahora — llamar al cliente esta semana"
                elif value > 1000:
                    priority = "MEDIA"
                    action = "Enviar propuesta inicial"
                else:
                    priority = "BAJA"
                    action = "Mantener en seguimiento pasivo"

                suggestions.append(
                    f"- [{priority}] {opp.title} | {days_in_pipeline} dias en pipeline | "
                    f"Valor: {value:.2f}EUR → Accion: {action}"
                )

            return (
                f"Analisis de {len(new_opps)} leads en fase 'new':\n"
                + "\n".join(suggestions)
                + "\n\nPuedo mover automaticamente los leads de alta prioridad a 'qualified' si me lo indicas."
            )
    except Exception as e:
        return f"Error analizando leads: {str(e)}"


@tool
async def create_client(
    tenant_id: str,
    name: str,
    nif: str = "",
    email: str = "",
    phone: str = "",
    address: str = "",
    city: str = "",
    postal_code: str = "",
    client_type: str = "customer",
) -> str:
    """
    Crea un nuevo cliente en el sistema.
    Args:
        tenant_id: ID del tenant
        name: Nombre o razón social del cliente (obligatorio)
        nif: NIF/CIF del cliente
        email: Email de contacto
        phone: Teléfono
        address: Dirección
        city: Ciudad
        postal_code: Código postal
        client_type: Tipo de cliente ('customer' o 'supplier')
    """
    try:
        async with AsyncSessionLocal() as db:
            new_client = Client(
                tenant_id=UUID(tenant_id),
                name=name,
                nif=nif or None,
                email=email or None,
                phone=phone or None,
                address=address or None,
                city=city or None,
                postal_code=postal_code or None,
                client_type=client_type,
            )
            db.add(new_client)
            try:
                await db.commit()
                await db.refresh(new_client)
            except IntegrityError:
                await db.rollback()
                return f"Error: Ya existe un cliente con NIF '{nif}' o email '{email}'."
            return f"Cliente '{name}' creado correctamente. ID: {new_client.id}. NIF: {nif or 'no especificado'}."
    except Exception as e:
        return f"Error creando cliente: {str(e)}"


tools = [
    list_opportunities,
    create_opportunity,
    update_opportunity_stage,
    qualify_leads,
    search_client,
    create_client,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    create_pdf_report,
    create_pdf_text_report,
]


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated

tools = _isolated(tools)
