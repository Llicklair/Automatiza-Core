"""Modelos de automatizacion: Workflows, Ejecuciones y Eventos de dominio."""

from .common import (
    JSONB,
    UUID,
    Base,
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


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)

    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(JSONB, default=dict)

    action_type = Column(String(50), nullable=False)
    action_config = Column(JSONB, default=dict)

    ui_nodes = Column(JSONB, default=list)
    ui_edges = Column(JSONB, default=list)

    execution_mode = Column(
        String(20), default="reasoning", nullable=False, server_default="reasoning"
    )
    compiled_steps = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    executions = relationship(
        "WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)

    status = Column(String(50), nullable=False, default="pending")

    trigger_payload = Column(JSONB)
    result_log = Column(Text)

    node_states = Column(JSONB, default=dict)
    current_node_id = Column(String(100), nullable=True)
    paused_at = Column(DateTime(timezone=True), nullable=True)

    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True))

    workflow = relationship("Workflow", back_populates="executions")
    tenant = relationship("Tenant")


class DomainEvent(Base):
    __tablename__ = "domain_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    event_name = Column(String(100), nullable=False, index=True)
    payload = Column(JSONB)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    tenant = relationship("Tenant", back_populates="domain_events")
