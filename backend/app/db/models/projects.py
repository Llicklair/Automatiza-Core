"""Modelos de gestion de proyectos."""

from .common import (
    UUID,
    Base,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    relationship,
    utcnow,
    uuid,
)


class Project(Base):
    __tablename__ = 'projects'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=True)

    name = Column(String(255), nullable=False)
    description = Column(Text)
    budget = Column(Numeric(10, 2), default=0)
    status = Column(String(50), default='active')

    start_date = Column(DateTime(timezone=True), default=utcnow)
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')
    client = relationship('Client')
    project_tasks = relationship('ProjectTask', back_populates='project', cascade='all, delete-orphan')


class ProjectTask(Base):
    __tablename__ = 'project_tasks'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey('projects.id'), nullable=True, index=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)

    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default='todo')

    start_date = Column(DateTime(timezone=True), default=utcnow)
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')
    project = relationship('Project', back_populates='project_tasks')
    assignee = relationship('User')
