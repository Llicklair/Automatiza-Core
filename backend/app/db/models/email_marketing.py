from sqlalchemy import Integer

from .common import (
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


class EmailTemplate(Base):
    """Plantilla de email reutilizable para campañas."""

    __tablename__ = "email_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    campaigns = relationship("EmailCampaign", back_populates="template")


class EmailCampaign(Base):
    """Campaña de email: conjunto de destinatarios + contenido + estado de envío."""

    __tablename__ = "email_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    template_id = Column(UUID(as_uuid=True), ForeignKey("email_templates.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)
    # draft | scheduled | sending | sent | failed
    status = Column(String(50), nullable=False, default="draft", index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=True, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    total_count = Column(Integer, nullable=False, default=0)
    sent_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    template = relationship("EmailTemplate", back_populates="campaigns")
    recipients = relationship("EmailCampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")


class EmailCampaignRecipient(Base):
    """Destinatario individual de una campaña con su estado de envío."""

    __tablename__ = "email_campaign_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("email_campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    # pending | sent | failed
    status = Column(String(50), nullable=False, default="pending")
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    campaign = relationship("EmailCampaign", back_populates="recipients")
