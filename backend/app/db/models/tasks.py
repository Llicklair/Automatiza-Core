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


class PendingApproval(Base):
    __tablename__ = "pending_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    execution_id = Column(
        UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=True, index=True
    )

    action_description = Column(Text, nullable=False)
    action_payload = Column(JSONB, nullable=False)
    risk_level = Column(String(20), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    status = Column(String(20), nullable=False, default="pending", index=True)

    task = relationship("Task", back_populates="pending_approvals")
