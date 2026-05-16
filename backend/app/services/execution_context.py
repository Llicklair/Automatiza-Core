"""
ExecutionContext: contexto compartido entre pasos de una ejecución multiagente.

Problema que resuelve:
    El Coordinador General ejecuta pasos en secuencia (billing → email → excel).
    Cada agente solo recibía la intención original del usuario, sin saber qué
    hicieron los agentes anteriores. Si billing creó la factura F-001, el agente
    de email no sabía qué factura adjuntar.

Solución:
    Antes de cada paso, construimos un ExecutionContext que:
    1. Recoge los outputs de todos los pasos anteriores (agent_results)
    2. Extrae entidades clave (invoice_id, employee_name, client_name, etc.)
    3. Genera un "enriched_intent" = intención original + resumen del contexto

    El enriched_intent se pasa como current_intent al agente siguiente.

Uso (en dispatch_node, antes de llamar al agente):
    ctx = ExecutionContext.from_state(state)
    enriched = ctx.build_enriched_intent()
    # Pasar enriched_intent al agente en lugar de user_intent crudo
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ─── Entidades que se extraen automáticamente de los resultados ───────────────

_EXTRACTABLE_KEYS = [
    # Billing
    "invoice_id",
    "invoice_number",
    "amount_base",
    "amount_total",
    "vat_rate",
    "client_name",
    "client_nif",
    # HR
    "employee_id",
    "employee_name",
    "payroll_id",
    "net_salary",
    # Documents
    "document_id",
    "document_type",
    "file_path",
    "file_name",
    # CRM
    "opportunity_id",
    "lead_name",
    # Banking
    "transaction_id",
    "bank_account",
    # General
    "concept",
    "notes",
]


@dataclass
class ExecutionContext:
    """
    Contexto acumulado de todos los pasos ejecutados hasta el momento.

    Attributes:
        tenant_id:       ID del tenant
        task_id:         ID de la tarea raíz
        user_id:         ID del usuario que lanzó la tarea
        user_intent:     Intención original del usuario (sin modificar)
        step_summaries:  Resumen de cada paso ejecutado: [(agent, action, key_data)]
        entities:        Entidades extraídas de los resultados (invoice_id, etc.)
        previous_outputs: Lista completa de outputs de pasos anteriores
    """

    tenant_id: str
    task_id: str
    user_id: str
    user_intent: str
    step_summaries: list[dict] = field(default_factory=list)
    entities: dict[str, Any] = field(default_factory=dict)
    previous_outputs: list[dict] = field(default_factory=list)
    tenant_knowledge: list[dict] = field(default_factory=list)

    @classmethod
    def from_state(cls, state: dict) -> ExecutionContext:
        """
        Construye el ExecutionContext desde el estado del orquestador.
        Extrae entidades de todos los agent_results previos.
        """
        ctx = cls(
            tenant_id=state.get("tenant_id", ""),
            task_id=state.get("task_id", ""),
            user_id=state.get("user_id", ""),
            user_intent=state.get("user_intent", ""),
            tenant_knowledge=state.get("tenant_knowledge", []),
        )

        for result in state.get("agent_results", []):
            ctx._ingest_result(result)

        return ctx

    def _ingest_result(self, result: dict) -> None:
        """Procesa un AgentResult y extrae entidades y resumen."""
        agent = result.get("agent", "unknown")
        output = result.get("output", {}) or {}
        success = result.get("success", False)

        if not isinstance(output, dict):
            output = {"raw": str(output)}

        # Extraer entidades conocidas del output (búsqueda recursiva 1 nivel)
        self._extract_entities(output)

        # También buscar dentro de extracted_data (billing agent)
        extracted = output.get("extracted_data") or {}
        if isinstance(extracted, dict):
            self._extract_entities(extracted)

        # Construir resumen legible del paso
        action = output.get("action", "ejecutado")
        key_data = {k: v for k, v in output.items() if k in _EXTRACTABLE_KEYS and v}

        summary = {
            "agent": agent,
            "action": action,
            "success": success,
            "key_data": key_data,
        }

        self.step_summaries.append(summary)
        self.previous_outputs.append(output)

    def _extract_entities(self, data: dict) -> None:
        """Extrae entidades conocidas de un dict de output."""
        for key in _EXTRACTABLE_KEYS:
            if key in data and data[key] is not None:
                self.entities[key] = data[key]

    def build_enriched_intent(self, current_instruction: str = None) -> str:
        """
        Genera la intención enriquecida que recibirá el próximo agente.

        Formato:
            <instrucción del paso o intención original>

            --- Contexto de pasos anteriores ---
            Paso 1 (billing): draft_created
              · invoice_id: abc-123
              · client_name: Acme SL
              · amount_total: 1815.00
            ...

            Entidades disponibles:
              · invoice_id: abc-123
              · client_name: Acme SL
        """
        base_intent = current_instruction or self.user_intent

        if not self.step_summaries and not current_instruction:
            return self.user_intent  # Sin pasos previos ni instrucción → intención pura

        lines = [base_intent, "", "--- Contexto de pasos anteriores ---"]

        for i, step in enumerate(self.step_summaries, start=1):
            status_icon = "✅" if step["success"] else "❌"
            lines.append(f"Paso {i} ({step['agent']}): {step['action']} {status_icon}")
            for k, v in step["key_data"].items():
                lines.append(f"  · {k}: {v}")

        if self.entities:
            lines.append("")
            lines.append("Entidades disponibles para este paso:")
            for k, v in self.entities.items():
                lines.append(f"  · {k}: {v}")

        if self.tenant_knowledge:
            lines.append("")
            lines.append("--- Conocimiento y Preferencias del Tenant ---")
            for fact in self.tenant_knowledge:
                lines.append(f"  · {fact.get('key')}: {fact.get('value')} ({fact.get('category')})")

        return "\n".join(lines)

    def get_entity(self, key: str, default: Any = None) -> Any:
        """Acceso directo a una entidad extraída. Ej: ctx.get_entity('invoice_id')"""
        return self.entities.get(key, default)

    def has_step_from(self, agent: str) -> bool:
        """Devuelve True si ya se ejecutó un paso de ese agente."""
        return any(s["agent"] == agent for s in self.step_summaries)

    def last_result_from(self, agent: str) -> dict | None:
        """Devuelve el último output del agente indicado o None."""
        for step, output in zip(reversed(self.step_summaries), reversed(self.previous_outputs)):
            if step["agent"] == agent:
                return output
        return None

    def to_dict(self) -> dict:
        """Serializa el contexto para logging o auditoría."""
        return {
            "tenant_id": self.tenant_id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "entities": self.entities,
            "steps": len(self.step_summaries),
            "step_summaries": self.step_summaries,
        }
