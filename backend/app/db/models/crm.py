"""Modelos CRM: Clientes, Oportunidades y Actividades."""

from .common import (
    Base, Column, DateTime, ForeignKey, Numeric, String, Text, UUID, JSONB,
    relationship, uuid, utcnow,
)


class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    nif = Column(String(50), index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    city = Column(String(255))
    postal_code = Column(String(50))
    client_type = Column(String(50), default="customer")
    holded_id = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    invoices = relationship("Invoice", back_populates="client")


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    expected_value = Column(Numeric(10, 2), nullable=False, default=0)
    stage = Column(String(50), nullable=False, default="new")

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    client = relationship("Client")


class Activity(Base):
    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=True, index=True)

    type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    metadata_json = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    client = relationship("Client")
    opportunity = relationship("Opportunity")
