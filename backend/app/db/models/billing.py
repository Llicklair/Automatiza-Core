"""Modelos de facturacion: Facturas, Presupuestos y Recurrentes."""

from sqlalchemy import Index, UniqueConstraint, text

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
    __table_args__ = (UniqueConstraint("tenant_id", "serie", "year", name="uq_invoice_series_tenant_serie_year"),)

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
    # Unicidad del número correlativo SOLO para las facturas que emitimos
    # nosotros (issued/rectificativa). Las recibidas llevan el número del
    # proveedor, que puede repetirse entre proveedores y coincidir con el
    # nuestro, por lo que quedan fuera del índice (índice único parcial).
    __table_args__ = (
        Index(
            "uq_invoices_tenant_number_emitted",
            "tenant_id",
            "invoice_number",
            unique=True,
            postgresql_where=text("invoice_type IN ('issued', 'rectificativa')"),
            sqlite_where=text("invoice_type IN ('issued', 'rectificativa')"),
        ),
    )

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
    # Datos de ejemplo del onboarding: se muestran en listados/analítica para que
    # el producto "se vea vivo", pero quedan FUERA de toda declaración fiscal
    # (303/130/390/libro registro/VeriFactu). Borrables de golpe. Ver
    # services/onboarding/seed.py. Las facturas demo NO consumen la serie
    # correlativa (numeración "DEMO-").
    is_demo = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    notes = Column(Text)
    terms = Column(Text)
    external_id = Column(String(255))
    document_id = Column(UUID(as_uuid=True), ForeignKey("tenant_documents.id"), nullable=True)

    # Rectificativa / abono (RD 1619/2012 Art. 15): enlaza a la factura original
    # que minora y guarda el motivo. NULL en una factura ordinaria.
    rectifies_invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True, index=True)
    rectification_reason = Column(Text, nullable=True)

    verifactu_status = Column(String(30), nullable=True)  # None | "sent" | "error"
    verifactu_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Régimen fiscal especial (Modelo 303, casillas 10-13/16-26/36-39).
    # None = régimen general interior.
    fiscal_regime = Column(String(30), nullable=True)
    # intracomunitario | isp | recargo_equivalencia

    # Retención IRPF Art. 95 LIRPF (facturas recibidas de profesionales).
    # Alimenta el Modelo 111 (perceptores profesionales).
    retencion_irpf_rate = Column(Numeric(5, 2), nullable=True)  # p.ej. 15.00
    retencion_irpf_amount = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    client = relationship("Client", back_populates="invoices")
    document = relationship("TenantDocument", foreign_keys=[document_id])
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")
    rectifies = relationship("Invoice", remote_side=[id], foreign_keys=[rectifies_invoice_id])


class VerifactuRecord(Base):
    """Registro Verifactu append-only encadenado por hash (RD 1007/2023 Art. 8).

    Cada factura genera exactamente un registro (índice UNIQUE en `invoice_id`).
    El `huella` se calcula como SHA-256 del payload canónico que incluye los
    campos clave (NIF emisor, serie, número, fecha, importe) Y la `huella_anterior`
    del último registro del mismo tenant. La cadena es independiente por tenant.

    Append-only enforced en Postgres mediante triggers PL/pgSQL (ver migración
    0011). En tests SQLite la inmutabilidad se verifica solo a nivel código.
    """

    __tablename__ = "verifactu_chain"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False, unique=True)

    huella = Column(String(64), nullable=False)
    huella_anterior = Column(String(64), nullable=True)
    payload_canonico = Column(Text, nullable=False)

    nif_emisor = Column(String(20), nullable=False)
    serie_factura = Column(String(16), nullable=False)
    numero_factura = Column(String(100), nullable=False)
    fecha_emision = Column(DateTime(timezone=True), nullable=False)
    importe_total = Column(Numeric(12, 2), nullable=False)

    is_backfilled = Column(Boolean, nullable=False, default=False)
    backfilled_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    invoice = relationship("Invoice", foreign_keys=[invoice_id])


class VerifactuConfig(Base):
    """Configuración del modo de remisión Verifactu por tenant (FAC.MODE).

    `mode` ∈ {voluntary, no_remission}. La ausencia de fila equivale al
    default `no_remission`. Solo se persiste al editar desde Settings.
    """

    __tablename__ = "verifactu_config"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, unique=True, index=True)
    mode = Column(String(32), nullable=False, default="no_remission")
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


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
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
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
    lines = relationship("DeliveryNoteLine", back_populates="delivery_note", cascade="all, delete-orphan")
    client = relationship("Client", foreign_keys=[client_id])


class DeliveryNoteLine(Base):
    __tablename__ = "delivery_note_lines"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    albaran_id = Column(UUID(as_uuid=True), ForeignKey("delivery_notes.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 3), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), nullable=False, default=21)
    total = Column(Numeric(10, 2), nullable=False, default=0)
    delivery_note = relationship("DeliveryNote", back_populates="lines")
