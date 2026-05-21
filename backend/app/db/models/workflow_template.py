"""Modelo de plantilla de workflow para el marketplace (F3.10)."""

import uuid

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.db.base import Base
from app.db.models.common import utcnow


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(120), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(60), nullable=False)
    author = Column(String(120), nullable=True)

    trigger_type = Column(String(50), nullable=False)
    trigger_config = Column(JSONB, nullable=False, default=dict)
    action_type = Column(String(50), nullable=False)
    action_config = Column(JSONB, nullable=False, default=dict)

    execution_mode = Column(String(20), nullable=False, default="reasoning")
    compiled_steps = Column(JSONB, nullable=True)

    tags = Column(JSONB, nullable=True)
    is_official = Column(Boolean, nullable=False, default=True)
    downloads_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
