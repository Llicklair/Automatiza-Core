import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


def utcnow():
    return datetime.now(UTC)


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    nif = Column(String(9), unique=True, nullable=False, index=True)
    plan = Column(String(50), nullable=False, default="starter")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    users = relationship("User", back_populates="tenant")
    tasks = relationship("Task", back_populates="tenant")
    domain_events = relationship("DomainEvent", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(200))
    role = Column(String(50), nullable=False, default="user")  # admin|user|viewer
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True))

    tenant = relationship("Tenant", back_populates="users")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    status = Column(
        String(50), nullable=False, default="pending",
        index=True
        # pending | planning | executing | awaiting_approval | done | failed | cancelled
    )
    domain = Column(String(100), nullable=False, index=True)
    # billing | documents | compliance | hr | customer_service
    user_intent = Column(Text)
    plan = Column(JSONB)
    current_step = Column(BigInteger, default=0)
    agent_results = Column(JSONB, default=list)
    requires_human_approval = Column(Boolean, default=False)
    error_message = Column(Text)
    additional_metadata = Column(JSONB, default=dict)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    tenant = relationship("Tenant", back_populates="tasks")
    audit_entries = relationship("AuditLog", back_populates="task")
    pending_approvals = relationship("PendingApproval", back_populates="task")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    agent_name = Column(Text, nullable=False)
    action_type = Column(Text, nullable=False)
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    llm_prompt = Column(Text)           # Prompt enviado al LLM
    llm_response = Column(Text)         # Respuesta raw del LLM
    validation_result = Column(JSONB)   # Resultado de validación determinista
    status = Column(String(50), nullable=False)
    # success | failed | rejected | pending_approval | skipped
    error_detail = Column(Text)

    executed_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    task = relationship("Task", back_populates="audit_entries")


class PendingApproval(Base):
    __tablename__ = "pending_approvals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=True, index=True)  # Vincula approval gates

    action_description = Column(Text, nullable=False)
    action_payload = Column(JSONB, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low | medium | high | critical
    expires_at = Column(DateTime(timezone=True), nullable=False)

    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    status = Column(String(20), nullable=False, default="pending", index=True)
    # pending | approved | rejected | expired

    task = relationship("Task", back_populates="pending_approvals")


class TenantIntegration(Base):
    __tablename__ = "tenant_integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    integration_type = Column(String(50), nullable=False)
    # holded | gmail | outlook | belvo | azure_form | onedrive | gdrive
    encrypted_credentials = Column(Text)  # AES-256 / Fernet, cifrado por tenant
    is_active = Column(Boolean, default=True, nullable=False)
    last_sync_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    config = Column(JSONB, default=dict)  # Configuración adicional (scopes, etc.)


class TenantKnowledge(Base):
    __tablename__ = "tenant_knowledge"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    key = Column(String(255), nullable=False, index=True) # e.g. "payment_terms", "default_vat"
    value = Column(Text, nullable=False)
    category = Column(String(50), default="general") # billing | hr | crm | legal
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class TenantDocument(Base):
    __tablename__ = "tenant_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True, index=True)

    file_name = Column(String(500), nullable=False)
    file_type = Column(String(100))  # application/pdf, image/png, etc.
    file_path = Column(Text, nullable=False)  # path on disk
    file_size = Column(BigInteger, default=0)

    status = Column(String(50), nullable=False, default="uploaded", index=True)
    # uploaded | processing | processed | failed
    parsed_content = Column(Text)  # extracted text / OCR result
    category = Column(String(50), nullable=True, index=True) # Carpeta destino (facturas, nominas, rrhh, etc.)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    processed_at = Column(DateTime(timezone=True))
    
    # Control de concurrencia para agentes (Locking)
    locked_by = Column(UUID(as_uuid=True), nullable=True) # ID de la Task que bloquea el archivo
    locked_at = Column(DateTime(timezone=True), nullable=True)


# ─── ERP Models (Local Independence) ────────────────────────────────────────

class Product(Base):
    """Catálogo de Productos y Servicios."""
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    item_type = Column(String(50), default="product")  # product | service
    sku = Column(String(100), index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0) # IVA por defecto
    stock_quantity = Column(Integer, nullable=False, default=0)
    stock_min_alert = Column(Integer, nullable=False, default=0)  # Alerta si baja de este nivel

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    stock_movements = relationship("StockMovement", back_populates="product", cascade="all, delete-orphan")


class StockMovement(Base):
    """Movimientos de almacén: entradas, salidas y ajustes de inventario."""
    __tablename__ = "stock_movements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False, index=True)
    movement_type = Column(String(50), nullable=False)  # entrada | salida | ajuste
    quantity = Column(Integer, nullable=False)           # Positivo o negativo
    stock_after = Column(Integer, nullable=False, default=0)  # Stock resultante
    reference = Column(String(255), nullable=True)       # Nº factura, albarán, etc.
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship("Tenant")
    product = relationship("Product", back_populates="stock_movements")

class Client(Base):
    """CRM / Contactos / Clientes / Proveedores."""
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    nif = Column(String(50), index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    address = Column(Text)
    city = Column(String(255))
    postal_code = Column(String(50))
    client_type = Column(String(50), default="customer") # customer | supplier | lead
    holded_id = Column(String(255), nullable=True)  # ID del contacto en Holded (si se sincronizó)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    invoices = relationship("Invoice", back_populates="client")


class Invoice(Base):
    """Facturación."""
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
    
    status = Column(String(50), nullable=False, default="draft") # draft | pending | paid | cancelled
    invoice_type = Column(String(50), nullable=False, default="issued") # issued | received
    notes = Column(Text)
    terms = Column(Text)
    
    # Referencia cruzada (si se sincronizó con Holded alguna vez)
    external_id = Column(String(255))

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    client = relationship("Client", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    """Líneas de detalle de una Factura."""
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
    """Presupuestos."""
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
    
    status = Column(String(50), nullable=False, default="draft") # draft | sent | accepted | rejected
    notes = Column(Text)
    terms = Column(Text)
    
    # Si viene de una oportunidad en el CRM
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    client = relationship("Client")
    lines = relationship("QuoteLine", back_populates="quote", cascade="all, delete-orphan")


class QuoteLine(Base):
    """Líneas de los presupuestos."""
    __tablename__ = "quote_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    
    description = Column(String(255), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    
    # Calculados
    total_line = Column(Numeric(10, 2), nullable=False, default=0)

    quote = relationship("Quote", back_populates="lines")
    product = relationship("Product")


class Employee(Base):
    """RRHH."""
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    nif = Column(String(50), index=True)
    name = Column(String(255), nullable=False)
    department = Column(String(100))
    role = Column(String(100))
    base_salary = Column(Numeric(10, 2))
    status = Column(String(50), default="active") # active | inactive | leave

    join_date = Column(DateTime(timezone=True))
    contract_end_date = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")


class Opportunity(Base):
    """CRM: Oportunidades comerciales / Leads."""
    __tablename__ = "opportunities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    expected_value = Column(Numeric(10, 2), nullable=False, default=0)
    stage = Column(String(50), nullable=False, default="new")
    # new | qualified | proposal | won | lost

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    client = relationship("Client")

class Activity(Base):
    """CRM: Historial de acciones (Llamadas, Emails, Notas)."""
    __tablename__ = "activities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True, index=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=True, index=True)
    
    type = Column(String(50), nullable=False) # call | email | note | meeting_log
    description = Column(Text, nullable=False)
    
    # Metadata opcional ej: duracion_llamada, sentiment_ia
    metadata_json = Column(JSONB, default={})

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    client = relationship("Client")
    opportunity = relationship("Opportunity")

class Event(Base):
    """Eventos de Calendario (Reuniones, Recordatorios, Vencimientos)."""
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    type = Column(String(50), default="meeting") # meeting | reminder | task_deadline
    location_or_link = Column(String(255))
    
    # Asociación Opcional
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    client = relationship("Client")

class Reservation(Base):
    """Reservas para uso de servicios físicos o digitales (salas, coches, franjas horarias dictadas por clientes)."""
    __tablename__ = "reservations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False)
    resource_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True) # Que servicio se reserva

    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    
    status = Column(String(50), default="pending") # pending | confirmed | cancelled | completed
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    
    client = relationship("Client")
    resource = relationship("Product")


class Payroll(Base):
    """Nóminas de Empleados."""
    __tablename__ = "payrolls"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    employee_id = Column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False, index=True)
    
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    issue_date = Column(DateTime(timezone=True), nullable=False)
    
    base_salary = Column(Numeric(10, 2), nullable=False)
    deductions = Column(Numeric(10, 2), default=0)
    net_salary = Column(Numeric(10, 2), nullable=False)
    
    status = Column(String(50), default="draft") # draft | paid | sent
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    employee = relationship("Employee")


class Project(Base):
    """Gestión de Proyectos: Proyectos."""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=True) # Opcional, si es para un cliente
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    budget = Column(Numeric(10, 2), default=0)
    status = Column(String(50), default="active") # active | completed | on_hold
    
    start_date = Column(DateTime(timezone=True), default=utcnow)
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    client = relationship("Client")
    project_tasks = relationship("ProjectTask", back_populates="project", cascade="all, delete-orphan")


class ProjectTask(Base):
    """Gestión de Proyectos: Tareas individuales."""
    __tablename__ = "project_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True, index=True)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="todo") # todo | in_progress | done
    
    start_date = Column(DateTime(timezone=True), default=utcnow)
    due_date = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    project = relationship("Project", back_populates="project_tasks")
    assignee = relationship("User")


class BankTransaction(Base):
    """Integración PSD2: Transacciones bancarias para conciliación."""
    __tablename__ = "bank_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    date = Column(Date, nullable=False)
    description = Column(String(255), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False) # Positivo ingreso, negativo gasto
    balance = Column(Numeric(10, 2))
    status = Column(String(50), default="unreconciled") # unreconciled | reconciled | ignored
    
    # ID de factura a la cual está asociada (conciliación)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    tenant = relationship("Tenant")
    invoice = relationship("Invoice")


# --- Accounting ---
class JournalEntry(Base):
    """Contabilidad: Asiento Contable (Libro Diario)."""
    __tablename__ = "journal_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    
    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    description = Column(String(500), nullable=False)
    reference_id = Column(String(255), nullable=True) # ID externo para enlazar con factura/nomina
    
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    
    tenant = relationship("Tenant")
    lines = relationship("JournalLine", back_populates="entry", cascade="all, delete-orphan")


class JournalLine(Base):
    """Contabilidad: Línea de apunte (Debe / Haber)."""
    __tablename__ = "journal_lines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), nullable=False, index=True)
    
    account_code = Column(String(50), nullable=False, index=True) # Ej: "430.0000", "700.0000", "572.0000"
    account_name = Column(String(255), nullable=True)
    
    debit = Column(Numeric(15, 2), default=0)  # Debe
    credit = Column(Numeric(15, 2), default=0) # Haber
    
    entry = relationship("JournalEntry", back_populates="lines")
    tenant = relationship("Tenant")


# ─── Workflows & Automations ────────────────────────────────────────────────

class Workflow(Base):
    """Reglas de automatización definidas por el usuario o la IA."""
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True) # None si lo creó el sistema
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    
    trigger_type = Column(String(50), nullable=False) 
    # event_based (ej. on_invoice_created) | schedule_based (ej. cron) | manual (ej. boton en UI)
    trigger_config = Column(JSONB, default=dict) # {"event": "invoice.created"} o {"cron": "0 0 1 * *"}
    
    action_type = Column(String(50), nullable=False)
    # create_task (lanza un Agente de LangGraph) | webhook | email
    action_config = Column(JSONB, default=dict) # {"agent": "hr", "intent": "Genera la nómina..."}
    
    # --- UI Graph Layout (Map) ---
    ui_nodes = Column(JSONB, default=list) # Array de nodos visuales. Ej: [{id: '1', type: 'trigger', position: {x: 0, y: 0}}]
    ui_edges = Column(JSONB, default=list) # Array de aristas/conexiones. Ej: [{id: 'e1-2', source: '1', target: '2'}]

    # --- Modo de ejecución ---
    execution_mode = Column(String(20), default="reasoning", nullable=False, server_default="reasoning")
    # 'reasoning'     → El orquestador LLM interpreta la instrucción en tiempo real en cada ejecución.
    # 'deterministic' → Los pasos se compilan una sola vez al crear la regla y se ejecutan directamente sin LLM.
    compiled_steps = Column(JSONB, nullable=True)
    # Ejemplo: [{"agent": "billing", "action": "...", "params": {"intent": "..."}}]

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowExecution(Base):
    """Registro histórico de cada vez que se dispara un Workflow."""
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflows.id"), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True) # Si la acción disparó una tarea de agente

    status = Column(String(50), nullable=False, default="pending")
    # pending | running | success | failed | paused

    trigger_payload = Column(JSONB) # Datos que lanzaron el evento (ej. la ID de la factura)
    result_log = Column(Text)       # Logs o error devuelto por la ejecución

    # --- Node Engine fields ---
    node_states = Column(JSONB, default=dict)  # {"node-1": {"status": "completed", "output": {...}, ...}}
    current_node_id = Column(String(100), nullable=True)  # Nodo en ejecución (para resume)
    paused_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp de pausa

    started_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True))

    workflow = relationship("Workflow", back_populates="executions")
    tenant = relationship("Tenant")


class FixedAsset(Base):
    """Inmovilizado material e inmaterial con cuadro de amortización."""
    __tablename__ = "fixed_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=True)  # equipment, furniture, vehicle, intangible, other
    description = Column(Text, nullable=True)
    purchase_date = Column(Date, nullable=False)
    purchase_value = Column(Numeric(15, 2), nullable=False)
    useful_life_years = Column(Numeric(5, 2), nullable=False, default=5)
    residual_value = Column(Numeric(15, 2), nullable=False, default=0)
    depreciation_method = Column(String(50), nullable=False, default="linear")
    status = Column(String(50), nullable=False, default="active")  # active, disposed
    account_code = Column(String(50), nullable=True, default="213")
    reference_invoice = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    tenant = relationship("Tenant")


class SalesOrder(Base):
    """Pedidos de venta: paso intermedio entre presupuesto y factura."""
    __tablename__ = "sales_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    order_number = Column(String(100), index=True)
    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    expected_delivery = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="draft")  # draft | confirmed | processing | shipped | delivered | cancelled
    amount_base = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    amount_total = Column(Numeric(10, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    # Referencia a presupuesto origen (si viene de uno)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    client = relationship("Client")
    lines = relationship("SalesOrderLine", back_populates="order", cascade="all, delete-orphan")


class SalesOrderLine(Base):
    """Líneas de un pedido de venta."""
    __tablename__ = "sales_order_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    discount_percentage = Column(Numeric(5, 2), default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    total = Column(Numeric(10, 2), nullable=False, default=0)

    order = relationship("SalesOrder", back_populates="lines")
    product = relationship("Product")


class PurchaseOrder(Base):
    """Pedidos de compra a proveedores."""
    __tablename__ = "purchase_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    supplier_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    order_number = Column(String(100), index=True)
    date = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    expected_delivery = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(50), nullable=False, default="draft")  # draft | sent | confirmed | received | cancelled
    amount_base = Column(Numeric(10, 2), nullable=False, default=0)
    tax_amount = Column(Numeric(10, 2), default=0)
    amount_total = Column(Numeric(10, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    supplier = relationship("Client")
    lines = relationship("PurchaseOrderLine", back_populates="order", cascade="all, delete-orphan")


class PurchaseOrderLine(Base):
    """Líneas de un pedido de compra."""
    __tablename__ = "purchase_order_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.id"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)
    description = Column(String(500), nullable=False)
    quantity = Column(Numeric(10, 2), nullable=False, default=1)
    unit_price = Column(Numeric(10, 2), nullable=False, default=0)
    tax_percentage = Column(Numeric(5, 2), default=21.0)
    total = Column(Numeric(10, 2), nullable=False, default=0)

    order = relationship("PurchaseOrder", back_populates="lines")
    product = relationship("Product")


class RecurringInvoice(Base):
    """Plantilla de factura recurrente. Celery la procesa y genera facturas periódicamente."""
    __tablename__ = "recurring_invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)                    # Nombre de la recurrencia
    interval_type = Column(String(50), nullable=False, default="monthly")  # monthly | quarterly | yearly | weekly
    next_run_date = Column(Date, nullable=False)
    last_run_date = Column(Date, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Plantilla de factura (líneas como JSON)
    lines_json = Column(JSONB, nullable=False, default=list)      # [{description, quantity, unit_price, tax_percentage}]
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    tenant = relationship("Tenant")
    client = relationship("Client")


class DomainEvent(Base):
    """Registro histórico y formal de sucesos de negocio (Event-Driven Architecture)."""
    __tablename__ = "domain_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    event_name = Column(String(100), nullable=False, index=True)  # ej: invoice_created, employee_onboarded
    payload = Column(JSONB)  # Datos relevantes (ids, importes, nombres)

    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    tenant = relationship("Tenant", back_populates="domain_events")
