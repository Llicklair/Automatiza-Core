"""Modelos de inventario: Productos y Movimientos de stock."""

from .common import (
    Base, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UUID,
    relationship, uuid, utcnow,
)


class Product(Base):
    __tablename__ = 'products'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    item_type = Column(String(50), default='product')
    sku = Column(String(100), index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    stock_quantity = Column(Integer, nullable=False, default=0)
    stock_min_alert = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')
    stock_movements = relationship('StockMovement', back_populates='product', cascade='all, delete-orphan')


class StockMovement(Base):
    __tablename__ = 'stock_movements'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'), nullable=False, index=True)
    movement_type = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    stock_after = Column(Integer, nullable=False, default=0)
    reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship('Tenant')
    product = relationship('Product', back_populates='stock_movements')
