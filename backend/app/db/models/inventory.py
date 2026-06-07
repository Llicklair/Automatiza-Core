"""Modelos de inventario: Productos y Movimientos de stock."""

from sqlalchemy import UniqueConstraint

from .common import (
    UUID,
    Base,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    relationship,
    utcnow,
    uuid,
)


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    item_type = Column(String(50), default="product")
    sku = Column(String(100), index=True)
    barcode = Column(String(50), index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100), index=True)
    location = Column(String(100), index=True)
    unit = Column(String(20), nullable=False, default="ud")
    price = Column(Numeric(10, 2), nullable=False, default=0)
    cost_price = Column(Numeric(10, 2))
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    stock_quantity = Column(Integer, nullable=False, default=0)
    stock_min_alert = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True)
    reorder_quantity = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    stock_movements = relationship("StockMovement", back_populates="product", cascade="all, delete-orphan")
    lots = relationship("ProductLot", back_populates="product", cascade="all, delete-orphan")


class ProductLot(Base):
    """Lote de un producto con caducidad, para deducción FEFO (First Expired, First Out).

    Los lotes son una capa OPCIONAL de detalle sobre `Product.stock_quantity`:
    si un producto no tiene lotes, el inventario funciona exactamente igual que
    antes (solo cuenta `stock_quantity`). Cuando hay lotes, la salida de stock
    descuenta primero del lote que caduca antes (FEFO), ideal para perecederos.

    `expiry_date` es nullable: un lote sin caducidad se ordena el último.
    """

    __tablename__ = "product_lots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    warehouse_id = Column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lot_number = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=True, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    cost_price = Column(Numeric(10, 2), nullable=True)

    received_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="lots")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    movement_type = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    stock_after = Column(Integer, nullable=False, default=0)
    unit_cost = Column(Numeric(10, 2), nullable=True)
    reference = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="stock_movements")


class Warehouse(Base):
    """Almacén/tienda físico del tenant. Permite gestionar stock en varias
    ubicaciones (multi-almacén). Cada tenant tiene uno marcado como `is_default`."""

    __tablename__ = "warehouses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(150), nullable=False)
    code = Column(String(50), nullable=True)
    address = Column(String(255), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")


class ProductStock(Base):
    """Stock de un producto EN un almacén concreto. `Product.stock_quantity`
    se mantiene como total global (suma de todos los almacenes)."""

    __tablename__ = "product_stock"
    __table_args__ = (UniqueConstraint("product_id", "warehouse_id", name="uq_product_stock_product_warehouse"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    warehouse_id = Column(
        UUID(as_uuid=True), ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity = Column(Integer, nullable=False, default=0)

    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    product = relationship("Product")
    warehouse = relationship("Warehouse")
