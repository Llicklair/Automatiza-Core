"""
Agente especializado en la gestión de Workflows y Automatizaciones.
Permite al usuario crear, modificar o desactivar reglas de negocio mediante lenguaje natural.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models.models import Workflow
from app.api.v1.schemas.tasks import StepResult


@dataclass
class WorkflowAgentResult:
    success: bool
    action: str  # create | update | delete | list | toggle
    workflow_id: str | None = None
    workflow_name: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    compiled_steps: list[dict[str, Any]] | None = None


# ─── Herramientas para el Agente (Simuladas en modo Prompt) ───────────────────

_COMPILE_STEPS_PROMPT = """\
Eres un compilador de pasos de workflow para AutomatizaPyme.
Dado un workflow con su configuración (nombre, descripción, trigger, instrucción de acción),
genera una lista CONCRETA y ORDENADA de pasos de ejecución deterministas.

Devuelve SIEMPRE un JSON válido con este formato:
{
  "steps": [
    {
      "agent": "billing|hr|documents|banking|crm|compliance|excel|email|rag",
      "action": "nombre_de_la_accion",
      "params": {
        "intent": "Instrucción concreta en lenguaje natural para este agente"
      }
    }
  ]
}

REGLAS:
1. Cada paso debe poder ejecutarse de forma independiente con la instrucción en "intent".
2. Infiere el "agent" correcto: billing (facturas), hr (nóminas/empleados), email (correos),
   documents (archivos/OCR), banking (banca), crm (clientes/oportunidades),
   compliance (fiscal/AEAT), excel (informes/hojas de cálculo), rag (consultas de documentos).
3. El "action" es un identificador snake_case descriptivo (ej: generate_invoices, send_email_notification).
4. Si la instrucción requiere múltiples pasos encadenados, genera un paso por cada agente implicado.
5. Mantén el orden lógico de ejecución: primero la acción principal, luego las secundarias (emails, notificaciones, etc.).
"""

_SYSTEM_PROMPT = """\
Eres el Agente de Automatizaciones (Workflow Agent).
Tu tarea es gestionar las reglas de automatización de la plataforma.

FORMATO DE RESPUESTA:
Debes responder SIEMPRE en formato JSON válido con esta estructura:
{
  "action": "create" | "update" | "delete" | "list" | "toggle",
  "name": "Nombre descriptivo del workflow",
  "description": "Explicación de qué hace",
  "trigger_type": "event_based" | "schedule_based",
  "trigger_config": {
     "events": ["invoice_created"] (si es event_based),
     "cron": "0 0 1 * *" (si es schedule_based, formato cron standard)
  },
  "action_type": "create_task",
  "action_config": {
     "instruction": "Lo que la IA debe hacer cuando se dispare",
     "domain": "billing" | "hr" | "documents" | "banking" | "coordinator"
  },
  "ui_nodes": [
     {"id": "node-1", "type": "trigger", "position": {"x": 50, "y": 50}, "data": {"label": "Inicio (Cron/Evento)"}},
     {"id": "node-2", "type": "action", "position": {"x": 50, "y": 150}, "data": {"label": "Paso 1: Descripción", "domain": "billing"}}
  ],
  "ui_edges": [
     {"id": "edge-1", "source": "node-1", "target": "node-2", "type": "smoothstep"}
  ],
  "is_active": true,
  "workflow_id": "UUID si es actualización o borrado"
}

REGLAS:
1. Si el usuario pide algo como "hazme la nómina todos los meses", usa trigger_type='schedule_based' y cron='0 0 1 * *'.
2. Si el usuario pide "avísame cuando se cree una factura", usa trigger_type='event_based' y events=['invoice_created'].
3. IMPORTANTE (GRAFO UI): Si "action" es "create", TIENES que generar una topología de Nodos y Aristas (`ui_nodes` y `ui_edges`) lógica representando los pasos internos de la instrucción.
    - El nodo-1 SIEMPRE debe ser el trigger (type: "trigger").
    - Coloca las posiciones ('x', 'y') en cascada descendente (y: 50, 150, 250, etc.).
    - Crea nodos de tipo `action` extraídos de las intenciones (ej un nodo para buscar info, otro para crear algo y otro de email). Conecta los nodos con `ui_edges`.
    - CADA nodo de tipo `action` DEBE incluir un campo `"domain"` en sus `data` (ej: "billing", "hr", "email", etc.) para que el orquestador sepa a qué agente llamar.
4. Si no entiendes la petición, devuelve un error lógico en el campo 'error'.
"""

async def _compile_deterministic_steps(
    name: str,
    description: str,
    trigger_type: str,
    action_instruction: str,
) -> list[dict[str, Any]]:
    """
    Hace una segunda llamada al LLM para compilar los pasos concretos
    de ejecución determinista del workflow. Se llama una sola vez al crear la regla.
    """
    from app.core.llm_factory import get_llm
    llm = get_llm(temperature=0, format_output="json")

    context = (
        f"Workflow: {name}\n"
        f"Descripción: {description}\n"
        f"Tipo de trigger: {trigger_type}\n"
        f"Instrucción de acción: {action_instruction}"
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=_COMPILE_STEPS_PROMPT),
            HumanMessage(content=context),
        ])
        parsed = json.loads(response.content)
        steps = parsed.get("steps", [])
        if not isinstance(steps, list):
            steps = []
        return steps
    except Exception:
        # Si falla la compilación, devolvemos un paso genérico para no bloquear la creación
        return [{"agent": "skill", "action": "execute_workflow", "params": {"intent": action_instruction}}]


async def run_workflow_agent(
    user_intent: str,
    tenant_id: str,
    user_id: str | None = None,
    task_id: str | None = None,
    execution_mode: str = "reasoning",
) -> WorkflowAgentResult:
    """
    Orquestación del agente de workflows: LLM -> Interpretación -> DB -> Resultado.

    Args:
        execution_mode: 'reasoning' (por defecto) o 'deterministic'.
            En modo 'deterministic', tras el parse inicial se compilan los pasos
            concretos del workflow mediante una segunda llamada al LLM y se
            almacenan en compiled_steps para ejecución directa sin LLM posterior.
    """
    try:
        # 1. Consultar al LLM para extraer la estructura del workflow
        from app.core.llm_factory import get_llm
        llm = get_llm(temperature=0, format_output="json")
        
        # Inyectar lista de workflows actuales si la intención parece una actualización
        current_context = ""
        if any(w in user_intent.lower() for w in ["modifica", "actualiza", "cambia", "borra", "quita", "desactiva"]):
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Workflow).where(Workflow.tenant_id == uuid.UUID(tenant_id)))
                wfs = result.scalars().all()
                if wfs:
                    current_context = "\nWorkflows actuales del tenant:\n" + "\n".join(
                        f"- ID: {w.id}, Nombre: {w.name}, Trigger: {w.trigger_type}, Activo: {w.is_active}" 
                        for w in wfs
                    )

        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM_PROMPT + current_context),
            HumanMessage(content=user_intent),
        ])

        try:
            plan = json.loads(response.content)
        except Exception:
            return WorkflowAgentResult(success=False, action="parse", error="No se pudo parsear el plan del LLM.")

        action = plan.get("action", "create")
        
        # 2. Ejecutar la acción contra la base de datos
        async with AsyncSessionLocal() as db:
            if action == "create":
                wf_name = plan.get("name", "Nueva Automática")
                wf_description = plan.get("description", "")
                wf_trigger_type = plan.get("trigger_type", "event_based")
                wf_action_config = plan.get("action_config", {})
                wf_action_instruction = wf_action_config.get("instruction", wf_description or wf_name)

                # Compilar pasos deterministas si se solicita ese modo
                compiled_steps = None
                if execution_mode == "deterministic":
                    compiled_steps = await _compile_deterministic_steps(
                        name=wf_name,
                        description=wf_description,
                        trigger_type=wf_trigger_type,
                        action_instruction=wf_action_instruction,
                    )

                new_wf = Workflow(
                    tenant_id=uuid.UUID(tenant_id),
                    created_by=uuid.UUID(user_id) if user_id else None,
                    name=wf_name,
                    description=wf_description,
                    trigger_type=wf_trigger_type,
                    trigger_config=plan.get("trigger_config", {}),
                    action_type=plan.get("action_type", "create_task"),
                    action_config=wf_action_config,
                    ui_nodes=plan.get("ui_nodes", []),
                    ui_edges=plan.get("ui_edges", []),
                    is_active=plan.get("is_active", True),
                    execution_mode=execution_mode,
                    compiled_steps=compiled_steps,
                )
                db.add(new_wf)
                await db.commit()
                await db.refresh(new_wf)
                return WorkflowAgentResult(
                    success=True,
                    action="create",
                    workflow_id=str(new_wf.id),
                    workflow_name=new_wf.name,
                    data=plan,
                    compiled_steps=compiled_steps,
                )

            elif action in ["update", "toggle", "delete"]:
                wf_id = plan.get("workflow_id")
                if not wf_id:
                    # Intento de búsqueda por nombre si no viene el ID (robusto para el usuario)
                    res = await db.execute(
                        select(Workflow).where(
                            Workflow.tenant_id == uuid.UUID(tenant_id),
                            Workflow.name.ilike(f"%{plan.get('name')}%")
                        ).limit(1)
                    )
                    existing_wf = res.scalar_one_or_none()
                else:
                    existing_wf = await db.get(Workflow, uuid.UUID(wf_id))

                if not existing_wf or str(existing_wf.tenant_id) != tenant_id:
                    return WorkflowAgentResult(success=False, action=action, error="No se encontró el workflow indicado.")

                if action == "delete":
                    await db.delete(existing_wf)
                    await db.commit()
                    return WorkflowAgentResult(success=True, action="delete", workflow_id=str(existing_wf.id))

                # Update / Toggle
                if "is_active" in plan:
                    existing_wf.is_active = plan["is_active"]
                if "trigger_config" in plan:
                    existing_wf.trigger_config = plan["trigger_config"]
                if "action_config" in plan:
                    existing_wf.action_config = plan["action_config"]
                
                await db.commit()
                return WorkflowAgentResult(
                    success=True, 
                    action=action, 
                    workflow_id=str(existing_wf.id), 
                    workflow_name=existing_wf.name,
                    data=plan
                )

            elif action == "list":
                res = await db.execute(select(Workflow).where(Workflow.tenant_id == uuid.UUID(tenant_id)))
                wfs = res.scalars().all()
                data_list = [{"id": str(w.id), "name": w.name, "active": w.is_active} for w in wfs]
                return WorkflowAgentResult(success=True, action="list", data={"workflows": data_list})

        return WorkflowAgentResult(success=False, action=action, error="Accion no soportada o error en DB.")

    except Exception as e:
        import traceback
        return WorkflowAgentResult(success=False, action="error", error=str(e), data={"trace": traceback.format_exc()})
