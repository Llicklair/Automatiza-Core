"""Modelos para el sistema de Empleados IA (AIEmployee).

Tablas:
  - ai_employees    — Perfiles de agentes virtuales por tenant
  - agent_skills    — Mapping many-to-many de tools autorizadas por empleado
  - employee_memory — Memoria persistente clave/valor del empleado
  - token_ledger    — Log inmutable de costes LLM por invocación
  - activity_feed   — Timeline cronológico de acciones completadas por agentes
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base
from app.db.models.common import utcnow


class AIEmployee(Base):
    __tablename__ = "ai_employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Ana Valdés"
    role = Column(String(100), nullable=False)  # e.g., "Directora Financiera"
    domain = Column(String(50), nullable=False)  # e.g., "billing", "hr" — usado para routing
    system_prompt = Column(Text, nullable=False)
    budget_limit_usd = Column(Numeric(10, 2), default=10.00)
    status = Column(String(20), nullable=False, default="idle")  # idle | working | paused | blocked
    is_builtin = Column(Boolean, nullable=False, default=False)  # True = agente pre-instalado
    icon = Column(String(10), nullable=True)  # emoji personalizado del agente
    avatar_color = Column(String(20), nullable=True)  # color del círculo avatar: violet, amber, blue…
    doc_folder = Column(String(200), nullable=True)  # carpeta de documentación asignada por el coordinador

    # Contrato mínimo del custom (≥2 de 4 capacidades verificables —
    # aplicación en capa de servicios, no a nivel BD).
    scope = Column(JSONB, nullable=True)  # {clients, categories, filters}
    memory_enabled = Column(Boolean, nullable=False, default=False)
    knowledge_enabled = Column(Boolean, nullable=False, default=False)
    workflows = Column(JSONB, nullable=True)  # [{name, cron, steps}]

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class EmployeeMemory(Base):
    """Memoria persistente clave/valor del AIEmployee.

    Una entrada por (employee_id, key). `value` es JSONB libre para que el
    agente decida la forma (lista, dict, string). `importance` permite poda
    futura (descartar entradas de baja importancia cuando crezca).

    Sólo se usa si `ai_employees.memory_enabled = True`.
    """

    __tablename__ = "employee_memory"
    __table_args__ = (
        # uq_employee_memory_employee_key declarada en la migración 0032
        {},
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    key = Column(String(160), nullable=False)
    value = Column(JSONB, nullable=False)
    importance = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class AgentSkill(Base):
    """Tabla de autorización many-to-many: qué tools puede invocar cada empleado.
    Si una tool no está aquí, el agente no puede ejecutarla físicamente."""

    __tablename__ = "agent_skills"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ai_employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_module = Column(String(255), nullable=False)  # e.g., "billing.create_invoice"


class TokenLedger(Base):
    """Log inmutable append-only de cada invocación LLM.
    Nunca se actualiza ni se borra. Permite auditoría y control de presupuesto."""

    __tablename__ = "token_ledger"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("ai_employees.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(UUID(as_uuid=True), nullable=True)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(10, 6), nullable=False)
    llm_provider = Column(String(50), nullable=True)  # "anthropic", "openai", "groq", "claude_code"
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)


class ActivityEntry(Base):
    """Timeline cronológico de acciones completadas por agentes.
    Append-only. Escrito por tools, leído por el dashboard."""

    __tablename__ = "activity_feed"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("ai_employees.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(UUID(as_uuid=True), nullable=True)
    category = Column(String(30), nullable=False)  # "billing", "hr", "inventory", "system"
    icon = Column(String(10), nullable=False, default="📋")
    message = Column(Text, nullable=False)  # En primera persona: "He enviado..."
    metadata_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, index=True)
