"""Modelos CRM: Clientes, Oportunidades y Actividades."""

from sqlalchemy import Index, text

from .common import (
    JSONB,
    UUID,
    Base,
    Boolean,
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


class Client(Base):
    __tablename__ = "clients"

    # Partial UNIQUE: un cliente con NIF determinado solo puede existir una vez
    # por tenant. Particulares sin NIF (None) o nif='' se permiten múltiples
    # (esos no entran en Modelo 347, no rompen reports). Cierra race condition
    # del upsert en agents/billing/_invoice_create_async.py.
    __table_args__ = (
        Index(
            "clients_unique_nif_per_tenant",
            "tenant_id", "nif",
            unique=True,
            postgresql_where=text("nif IS NOT NULL AND nif <> ''"),
            sqlite_where=text("nif IS NOT NULL AND nif != ''"),
        ),
    )

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
    # Opt-in RGPD: solo los clientes con consentimiento reciben email marketing
    marketing_consent = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    # Dato de ejemplo del onboarding (borrable de golpe). Ver onboarding/seed.py.
    is_demo = Column(Boolean, nullable=False, default=False, server_default=text("false"))

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
    opportunity_id = Column(
        UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=True, index=True
    )

    type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    metadata_json = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    client = relationship("Client")
    opportunity = relationship("Opportunity")
