"""Re-exportador de compatibilidad.

Todos los modelos viven ahora en modulos de dominio separados.
Este archivo garantiza que cualquier import existente del tipo:
    from app.db.models.models import Tenant, User, ...
siga funcionando sin cambios.
"""

# --- Accounting ---
from .accounting import BankTransaction, FixedAsset, JournalEntry, JournalLine  # noqa: F401

# --- AI Employees ---
from .ai_employees import ActivityEntry, AgentSkill, AIEmployee, TokenLedger  # noqa: F401

# --- Auth ---
from .auth import PasswordResetToken, Tenant, User  # noqa: F401

# --- Billing ---
from .billing import (  # noqa: F401
    Invoice,
    InvoiceLine,
    InvoiceSeries,
    Quote,
    QuoteLine,
    RecurringInvoice,
)

# --- Calendar ---
from .calendar import Event, Reservation  # noqa: F401
from .common import utcnow  # noqa: F401

# --- CRM ---
from .crm import Activity, Client, Opportunity  # noqa: F401

# --- HR ---
from .hr import Candidate, Employee, Payroll, RecruitmentPosition  # noqa: F401

# --- Inventory ---
from .inventory import Product, StockMovement  # noqa: F401

# --- Orders ---
from .orders import PurchaseOrder, PurchaseOrderLine, SalesOrder, SalesOrderLine  # noqa: F401

# --- Projects ---
from .projects import Project, ProjectTask  # noqa: F401

# --- Tasks & Audit ---
from .tasks import AuditLog, PendingApproval, Task  # noqa: F401

# --- Tenant config ---
from .tenant import (  # noqa: F401
    TenantDocument,
    TenantIntegration,
    TenantKnowledge,
    TenantLlmConfig,
)

# --- Workflows ---
from .workflows import DomainEvent, Workflow, WorkflowExecution  # noqa: F401
