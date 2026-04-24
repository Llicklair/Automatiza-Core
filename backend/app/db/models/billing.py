"""Modelos de facturacion: Facturas, Presupuestos y Recurrentes."""

from sqlalchemy import UniqueConstraint

from .common import (
    JSONB,
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


class InvoiceSeries(Base):
    """Controla la numeración correlativa de facturas por serie y año."""

    __tablename__ = "invoice_series"
    __table_args__ = (
        UniqueConstraint("tenant_id", "serie", "year", name="uq_invoice_series_tenant_serie_year"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    serie = Column(String(10), nullable=False, default="F")
    year = Column(Integer, nullable=False)
    last_number = Column(Integer, nullable=False, default=0)
    prefix = Column(String(20), nullable=False, default="F")

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    invoice_number = Column(String(100), index=True)
    date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True))

    amount_base = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    amount_total = Column(Numeric(10, 2), nullable=False, default=0)

    status = Column(String(50), nullable=False, default="draft")
    invoice_type = Column(String(50), nullable=False, default="issued")
    notes = Column(Text)
    terms = Column(Text)
    external_id = Column(String(255))

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    client = relationship("Client", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"))

    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    discount_percentage = Column(Numeric(5, 2), default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    total = Column(Numeric(10, 2), nullable=False, default=0)

    invoice = relationship("Invoice", back_populates="lines")


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    quote_number = Column(String(100), index=True)
    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    valid_until = Column(DateTime(timezone=True))

    amount_base = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    amount_total = Column(Numeric(10, 2), nullable=False, default=0)

    status = Column(String(50), nullable=False, default="draft")
    notes = Column(Text)
    terms = Column(Text)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    client = relationship("Client")
    lines = relationship("QuoteLine", back_populates="quote", cascade="all, delete-orphan")


class QuoteLine(Base):
    __tablename__ = "quote_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id = Column(
        UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    total_line = Column(Numeric(10, 2), nullable=False, default=0)

    quote = relationship("Quote", back_populates="lines")
    product = relationship("Product")


class RecurringInvoice(Base):
    __tablename__ = "recurring_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    interval_type = Column(String(50), nullable=False, default="monthly")
    next_run_date = Column(Date, nullable=False)
    last_run_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    lines_json = Column(JSONB, nullable=False, default=list)
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    client = relationship("Client", foreign_keys=[client_id])


class DocumentTemplate(Base):
    """Plantillas visuales para facturas, nóminas y excels por tenant."""

    __tablename__ = "document_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Identificación
    name = Column(String(100), nullable=False)
    template_type = Column(String(20), nullable=False)  # invoice | payroll | excel
    is_default = Column(Boolean, nullable=False, default=False)

    # Preset de layout (define disposición global)
    layout_style = Column(String(20), nullable=False, default="modern")
    # modern | classic | minimal | bold

    # Color y tipografía
    accent_color = Column(String(7), nullable=False, default="#6366f1")  # hex
    font_family = Column(String(20), nullable=False, default="helvetica")
    # helvetica | times | courier

    # Opciones de layout
    logo_position = Column(String(10), nullable=False, default="left")  # left|center|right
    header_style = Column(String(20), nullable=False, default="color_band")
    # color_band | line_only | none
    table_style = Column(String(20), nullable=False, default="striped")
    # striped | clean | bordered

    # Datos del pie y notas
    footer_text = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")


class DeliveryNote(Base):
    __tablename__ = "delivery_notes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)
    albaran_number = Column(String(50), nullable=False)
    date = Column(Date, nullable=False, default=lambda: __import__("datetime").date.today())
    status = Column(String(20), nullable=False, default="draft")  # draft, confirmed, delivered
    notes = Column(Text, nullable=True)
    amount_base = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), nullable=False, default=0)
    amount_total = Column(Numeric(10, 2), nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    lines = relationship(
        "DeliveryNoteLine", back_populates="delivery_note", cascade="all, delete-orphan"
    )
    client = relationship("Client", foreign_keys=[client_id])


class DeliveryNoteLine(Base):
    __tablename__ = "delivery_note_lines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    albaran_id = Column(
        UUID(as_uuid=True), ForeignKey("delivery_notes.id", ondelete="CASCADE"), nullable=False
    )
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), nullable=False, default=21)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    delivery_note = relationship("DeliveryNote", back_populates="lines")
