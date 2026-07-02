"""Modelos de tareas, auditoría y aprobaciones."""

from .common import (
    JSONB,
    UUID,
    Base,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    relationship,
    utcnow,
    uuid,
)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    status = Column(String(50), nullable=False, default="pending", index=True)
    domain = Column(String(100), nullable=False, index=True)
    user_intent = Column(Text)
    plan = Column(JSONB)
    current_step = Column(BigInteger, default=0)
    agent_results = Column(JSONB, default=list)
    requires_human_approval = Column(Boolean, default=False)
    error_message = Column(Text)
    additional_metadata = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Soft-delete: cleanup_tasks() marca is_deleted=True en lugar de DELETE
    # para no romper FK desde audit_log (tabla WORM, mig 0012). Las queries de
    # listado filtran is_deleted=False.
    is_deleted = Column(Boolean, default=False, nullable=False, server_default="false")

    tenant = relationship("Tenant", back_populates="tasks")
    audit_entries = relationship("AuditLog", back_populates="task")
    pending_approvals = relationship("PendingApproval", back_populates="task")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    agent_name = Column(Text, nullable=False)
    action_type = Column(Text, nullable=False)
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    llm_prompt = Column(Text)
    llm_response = Column(Text)
    validation_result = Column(JSONB)
    status = Column(String(50), nullable=False)
    error_detail = Column(Text)

    executed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    task = relationship("Task", back_populates="audit_entries")


class AgentExecutionTrace(Base):
    """Traza append-only por cada invocación de agente LLM (AI Act / SEC.WORM).

    Cumple Art. 12 Reglamento UE 2024/1689 (logging automático ≥ 6 meses) y
    refuerza la defensa Art. 6(3) — cada acción del agente queda registrada
    con prompt+modelo+tokens para reconstrucción posterior.

    Append-only en Postgres mediante triggers PL/pgSQL anti-UPDATE/DELETE
    (ver migración 0012). En SQLite la inmutabilidad solo está enforced en
    código (los tests verifican el patrón).

    Hashes en lugar de prompts/outputs en plano para minimizar superficie
    PII en logs y permitir comparación de regresión sin guardar el contenido
    completo. Los prompts versionados viven en BD aparte (AI.4 gobernanza).
    """

    __tablename__ = "agent_execution_trace"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    execution_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)

    agent_name = Column(String(100), nullable=False)
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)

    prompt_hash = Column(String(64), nullable=True)  # SHA-256 del prompt completo
    prompt_version = Column(String(100), nullable=True)  # commit hash / tag
    tool_calls_json = Column(JSONB, nullable=True)
    output_hash = Column(String(64), nullable=True)

    tokens_in = Column(Integer, nullable=True)
    tokens_out = Column(Integer, nullable=True)
    cost_eur = Column(Numeric(10, 4), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    status = Column(String(30), nullable=False, default="ok")  # ok | error | aborted
    error_class = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class PendingApproval(Base):
    __tablename__ = "pending_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=True, index=True)

    action_description = Column(Text, nullable=False)
    action_payload = Column(JSONB, nullable=False)
    risk_level = Column(String(20), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    status = Column(String(20), nullable=False, default="pending", index=True)

    task = relationship("Task", back_populates="pending_approvals")


# Valores convencionales para `PendingApproval.risk_level` cuando se trata
# de aprobación obligatoria humana para actos fiscales (SEC.APR).
RISK_LEVEL_MANDATORY_HUMAN_FISCAL = "MANDATORY_HUMAN_FISCAL"


class FiscalApprovalLog(Base):
    """Log append-only de aprobaciones humanas de actos fiscales (SEC.APR).

    Ningún modelo AEAT (303/130/347/390/111/190/...) puede salir hacia
    presentación telemática sin un registro en esta tabla. El registro
    captura: quién aprueba, qué borrador concreto se aprueba (hash), texto
    de confirmación tipeado, IP, user-agent y timestamp.

    Append-only enforced en Postgres mediante triggers PL/pgSQL
    (migración 0013). Conservación mínima 5 años por LGT Art. 70.
    """

    __tablename__ = "fiscal_approval_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    pending_approval_id = Column(UUID(as_uuid=True), ForeignKey("pending_approvals.id"), nullable=True, index=True)

    model_aeat = Column(String(10), nullable=False)  # "303", "130", "347", "390", "111", "190"
    period_quarter = Column(Integer, nullable=True)  # 1..4 si trimestral
    period_year = Column(Integer, nullable=False)

    payload_hash = Column(String(64), nullable=False)  # SHA-256 del borrador exacto aprobado
    pdf_path = Column(String(500), nullable=True)  # ruta al PDF firmado guardado
    approval_text = Column(Text, nullable=False)  # texto literal tipeado por el usuario
    decision = Column(String(20), nullable=False)  # "approved" | "rejected"
    rejection_reason = Column(Text, nullable=True)

    # Trazabilidad de quien firma (para juicio civil/contencioso-administrativo).
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class IdempotencyKey(Base):
    """Clave de idempotencia persistente para jobs del scheduler/workers.

    Sin tenant_id: es una tabla de sistema (la clave ya incluye operación y
    entidad). Sobrevive reinicios — evita p.ej. emitir dos veces una factura
    recurrente si la app se reinicia dentro de la ventana del cron.
    """

    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    payload = Column(Text, nullable=True)  # JSON con executed_at/result
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
