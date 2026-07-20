"""Modelos de TPV (Punto de Venta).

Una `PosSession` representa una sesión de venta abierta por un usuario
(cajero) sobre un tenant. Solo puede haber una sesión `open` por
(tenant_id, user_id) — garantizado con un índice único parcial en la
migración 0025.

Al cerrar (checkout), la sesión guarda el método de pago, los totales
agregados, y descuenta stock atómicamente por cada línea con product_id
asociado (StockMovement.reference = "POS_SESSION:<session_id>").

No emite factura automáticamente — la integración con `create_invoice`
y Verifactu queda como fase 2 (botón opcional "generar factura
simplificada" sobre una sesión cerrada).
"""

from .common import (
    UUID,
    Base,
    Column,
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


class PosSession(Base):
    __tablename__ = "pos_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="open")  # open | closed | cancelled
    payment_method = Column(String(20), nullable=True)  # cash | card (null hasta checkout)
    amount_subtotal = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    amount_total = Column(Numeric(10, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    # Factura simplificada (F2) emitida a partir de esta sesión cerrada (fase 2 TPV).
    # NULL mientras no se ha facturado; enlaza el ticket con su Invoice y sirve de
    # guard de idempotencia (una sesión se factura una sola vez).
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True, index=True)

    opened_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    tenant = relationship("Tenant")
    lines = relationship("PosSessionLine", back_populates="session", cascade="all, delete-orphan")


class PosSessionLine(Base):
    __tablename__ = "pos_session_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("pos_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), nullable=False, default=21)
    total = Column(Numeric(10, 2), nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    session = relationship("PosSession", back_populates="lines")
