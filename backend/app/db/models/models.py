"""Re-exportador de compatibilidad.

Todos los modelos viven ahora en modulos de dominio separados.
Este archivo garantiza que cualquier import existente del tipo:
    from app.db.models.models import Tenant, User, ...
siga funcionando sin cambios.
"""

from .common import utcnow  # noqa: F401

# --- Auth ---
from .auth import Tenant, User, PasswordResetToken  # noqa: F401

# --- Tasks & Audit ---
from .tasks import Task, AuditLog, PendingApproval  # noqa: F401

# --- Tenant config ---
from .tenant import TenantIntegration, TenantKnowledge, TenantDocument, TenantLlmConfig  # noqa: F401

# --- CRM ---
from .crm import Client, Opportunity, Activity  # noqa: F401

# --- Billing ---
from .billing import Invoice, InvoiceLine, InvoiceSeries, Quote, QuoteLine, RecurringInvoice  # noqa: F401

# --- Inventory ---
from .inventory import Product, StockMovement  # noqa: F401

# --- Orders ---
from .orders import SalesOrder, SalesOrderLine, PurchaseOrder, PurchaseOrderLine  # noqa: F401

# --- HR ---
from .hr import Employee, Payroll, RecruitmentPosition, Candidate  # noqa: F401

# --- Accounting ---
from .accounting import JournalEntry, JournalLine, BankTransaction, FixedAsset  # noqa: F401

# --- Projects ---
from .projects import Project, ProjectTask  # noqa: F401

# --- Calendar ---
from .calendar import Event, Reservation  # noqa: F401

# --- Workflows ---
from .workflows import Workflow, WorkflowExecution, DomainEvent  # noqa: F401

# --- AI Employees ---
from .ai_employees import AIEmployee, AgentSkill, TokenLedger, ActivityEntry  # noqa: F401
