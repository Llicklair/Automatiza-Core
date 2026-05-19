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

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ─── Configuración de cap para texto libre del step previo ────────────────────
#
# Cuando un agente devuelve markdown libre (rag/chat/recruitment/custom/summary)
# y no hay claves estructuradas en `_EXTRACTABLE_KEYS`, propagamos el cuerpo de
# `response` al siguiente step. El cap evita inflar el prompt:
#
#   - Target ≈ 1k tokens del modelo destino.
#   - Si `tiktoken` está disponible, se trunca por tokens reales.
#   - Si no, se estima 4 chars/token → 4000 chars como cap por defecto.
#
# Elegimos 4000 (vs el 400 antiguo) porque era el cuello de botella reportado
# en lessons 2026-05-18: respuestas como "Factura IA-001 creada por 1815€…"
# se truncaban a 400 chars y el step N+1 perdía contexto. 4000 cubre la
# inmensa mayoría de respuestas operativas sin disparar latencia del LLM
# downstream (con prompts de ~6-8k tokens totales seguimos lejos del context
# window de Sonnet/Haiku).
_RESPONSE_PREVIEW_CAP_CHARS = 4000
_RESPONSE_PREVIEW_CAP_TOKENS = 1000


def _truncate_response_text(text: str) -> str:
    """Trunca `text` a un cap razonable (~1k tokens). Usa tiktoken si está."""
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    try:  # pragma: no cover — tiktoken puede no estar instalado
        import tiktoken  # type: ignore

        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(cleaned)
        if len(tokens) <= _RESPONSE_PREVIEW_CAP_TOKENS:
            return cleaned
        truncated = enc.decode(tokens[:_RESPONSE_PREVIEW_CAP_TOKENS])
        return truncated.rstrip() + "…"
    except Exception:
        if len(cleaned) <= _RESPONSE_PREVIEW_CAP_CHARS:
            return cleaned
        return cleaned[:_RESPONSE_PREVIEW_CAP_CHARS].rstrip() + "…"


# ─── Parser ligero de claves obvias en markdown ───────────────────────────────
#
# Cuando el agente devuelve texto humano ("Factura: IA-2026-0001 creada para
# Acme SL"), extraemos los pares más comunes vía regex y los añadimos a
# `key_data`. NO sustituye a los outputs estructurados — sólo es un fallback
# para respuestas en prosa.

# Etiquetas markdown frecuentes → clave canónica de _EXTRACTABLE_KEYS.
_MARKDOWN_LABELS: dict[str, str] = {
    "factura": "invoice_number",
    "nº factura": "invoice_number",
    "numero de factura": "invoice_number",
    "número de factura": "invoice_number",
    "cliente": "client_name",
    "nif": "client_nif",
    "cif": "client_nif",
    "empleado": "employee_name",
    "nómina": "payroll_id",
    "nomina": "payroll_id",
    "documento": "document_id",
    "archivo": "file_name",
    "fichero": "file_name",
    "oportunidad": "opportunity_id",
    "lead": "lead_name",
    "transacción": "transaction_id",
    "transaccion": "transaction_id",
    "cuenta": "bank_account",
    "iban": "bank_account",
    "concepto": "concept",
    "id": "document_id",
}

# Detecta "<Etiqueta>: <valor>" en texto plano o markdown ("**Factura:** IA-001").
# Acepta opcional **/__/* a ambos lados de la etiqueta, ":" o "—" como separador.
_MD_KV_RE = re.compile(
    r"(?:^|\n|[•\-]\s*)"                # inicio de línea o bullet
    r"[\*_]{0,2}\s*"                    # opcional negrita/cursiva apertura
    r"([A-Za-zÁÉÍÓÚáéíóúÑñ ºª]+?)"     # etiqueta
    r"\s*[\*_]{0,2}\s*"                 # opcional negrita/cursiva cierre
    r"[:\-–—]"                          # separador
    r"\s*[\*_]{0,2}\s*"                 # opcional negrita post-separador (**Factura:** valor)
    r"([^\n]+?)"                        # valor (resto de la línea)
    r"(?=\n|$)",
)

# UUID v4-ish (acepta cualquier forma estándar 8-4-4-4-12 hex).
_UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


def _parse_markdown_entities(text: str) -> dict[str, Any]:
    """Extrae pares clave→valor obvios de un markdown/texto libre.

    Reconoce patrones "Etiqueta: valor", incluyendo variantes con negrita
    (**Factura:** IA-001). Mapea la etiqueta a una clave canónica de
    `_EXTRACTABLE_KEYS` cuando se identifica; si no, ignora la línea.

    Devuelve `{}` si no se extrae nada. Pensado como FALLBACK — no debe
    sobrescribir entidades estructuradas que ya estén en `output`.
    """
    if not text:
        return {}
    found: dict[str, Any] = {}
    for m in _MD_KV_RE.finditer(text):
        label_raw = m.group(1).strip().lower().strip("*_ ")
        value = m.group(2).strip().strip("*_ .,;")
        if not value or len(value) > 300:
            continue
        canonical = _MARKDOWN_LABELS.get(label_raw)
        if canonical is None:
            # También probamos sin espacios internos por si la etiqueta vino
            # como "ID factura" → buscar "id" o "factura" como heurística.
            words = label_raw.split()
            if len(words) <= 2:
                for w in words:
                    canonical = _MARKDOWN_LABELS.get(w)
                    if canonical:
                        break
        if canonical and canonical not in found:
            found[canonical] = value
    # Si encontramos un UUID y no había document_id/invoice_id explícito, úsalo.
    if "document_id" not in found and "invoice_id" not in found:
        uuid_match = _UUID_RE.search(text)
        if uuid_match:
            found.setdefault("document_id", uuid_match.group(0))
    return found


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

        # Capturar el texto humano del agente (response) cuando exista. Sin esto,
        # cuando el output no contiene claves estructuradas en _EXTRACTABLE_KEYS
        # (mayoría de casos: rag, chat, recruitment, custom, summary) el siguiente
        # step recibe "Paso N (agent): action ✅" sin DATOS, y el LLM del step N+1
        # responde "no tengo acceso a los datos del paso N".
        response_text = output.get("response") or output.get("summary") or output.get("result")
        response_preview = None
        if isinstance(response_text, str) and response_text.strip():
            # Cap basado en tokens del modelo destino (≈1k tokens). Antes 400
            # chars truncaba respuestas legítimas (lessons 2026-05-18). Si el
            # output es estructurado, este preview no se renderiza (ver
            # build_enriched_intent); sólo se usa como fallback de prosa.
            response_preview = _truncate_response_text(response_text)

            # Parser ligero de markdown: extrae "Factura: IA-001", "Cliente: X",
            # UUIDs, etc. Sólo si no había la clave ya estructurada en `output`
            # (no pisamos datos canónicos).
            try:
                md_entities = _parse_markdown_entities(response_text)
            except Exception as e:  # pragma: no cover — defensivo
                logger.debug("Markdown parser falló: %s", e)
                md_entities = {}
            for k, v in md_entities.items():
                # Sólo añadir si NO existía ya (vía _extract_entities arriba).
                if k not in self.entities:
                    self.entities[k] = v

        summary = {
            "agent": agent,
            "action": action,
            "success": success,
            "key_data": key_data,
            "response_preview": response_preview,
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
            # Si no hay key_data estructurado pero sí hay texto de respuesta,
            # incluirlo para que el siguiente agente vea qué dijo el anterior.
            preview = step.get("response_preview")
            if preview and not step["key_data"]:
                # Indentar a 2 espacios para legibilidad del LLM
                indented = "\n  ".join(preview.splitlines())
                lines.append(f"  respuesta: {indented}")

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
