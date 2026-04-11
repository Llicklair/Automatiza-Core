"""Modelos de calendario: Eventos y Reservas."""

from .common import (
    UUID,
    Base,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    relationship,
    utcnow,
    uuid,
)


class Event(Base):
    __tablename__ = 'events'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    type = Column(String(50), default='meeting')
    location_or_link = Column(String(255))
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    client = relationship('Client')


class Reservation(Base):
    __tablename__ = 'reservations'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey('products.id'), nullable=True)

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    status = Column(String(50), default='pending')
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    client = relationship('Client')
    resource = relationship('Product')
