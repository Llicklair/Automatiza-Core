"""Modelos de pedidos: Ventas y Compras."""

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


class SalesOrder(Base):
    __tablename__ = 'sales_orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False, index=True)
    order_number = Column(String(100), index=True)
    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    expected_delivery = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default='draft')
    amount_base = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    amount_total = Column(Numeric(10, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    quote_id = Column(UUID(as_uuid=True), ForeignKey('quotes.id'), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')
    client = relationship('Client')
    lines = relationship('SalesOrderLine', back_populates='order', cascade='all, delete-orphan')


class SalesOrderLine(Base):
    __tablename__ = 'sales_order_lines'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('sales_orders.id'), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    discount_percentage = Column(Numeric(5, 2), default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    total = Column(Numeric(10, 2), nullable=False, default=0)

    order = relationship('SalesOrder', back_populates='lines')
    product = relationship('Product')


class PurchaseOrder(Base):
    __tablename__ = 'purchase_orders'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id'), nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey('clients.id'), nullable=False, index=True)
    order_number = Column(String(100), index=True)
    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    expected_delivery = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default='draft')
    amount_base = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    amount_total = Column(Numeric(10, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship('Tenant')
    supplier = relationship('Client')
    lines = relationship('PurchaseOrderLine', back_populates='order', cascade='all, delete-orphan')


class PurchaseOrderLine(Base):
    __tablename__ = 'purchase_order_lines'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey('purchase_orders.id'), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey('products.id'), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    total = Column(Numeric(10, 2), nullable=False, default=0)

    order = relationship('PurchaseOrder', back_populates='lines')
    product = relationship('Product')
