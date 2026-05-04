"""Paquete de modelos SQLAlchemy.

Importa todos los modulos de dominio para que Alembic detecte
todas las tablas al inspeccionar Base.metadata.
"""

from .accounting import BankTransaction, FixedAsset, JournalEntry, JournalLine  # noqa: F401
from .alerts import AlertLog  # noqa: F401
from .ai_employees import ActivityEntry, AgentSkill, AIEmployee, TokenLedger  # noqa: F401
from .auth import ClientPortalToken, PasswordResetToken, Tenant, User  # noqa: F401
from .billing import (  # noqa: F401
    Invoice,
    InvoiceLine,
    InvoiceSeries,
    Quote,
    QuoteLine,
    RecurringInvoice,
)
from .calendar import Event, Reservation  # noqa: F401
from .crm import Activity, Client, Opportunity  # noqa: F401
from .generative_ui import GeneratedUI  # noqa: F401
from .hr import Candidate, Employee, Payroll, RecruitmentPosition  # noqa: F401
from .hr_documents import HRDocument  # noqa: F401
from .inventory import Product, StockMovement  # noqa: F401
from .orders import PurchaseOrder, PurchaseOrderLine, SalesOrder, SalesOrderLine  # noqa: F401
from .projects import Project, ProjectTask  # noqa: F401
from .tasks import AuditLog, PendingApproval, Task  # noqa: F401
from .tenant import (  # noqa: F401
    TenantDocument,
    TenantIntegration,
    TenantKnowledge,
    TenantLlmConfig,
)
from .workflows import DomainEvent, Workflow, WorkflowExecution  # noqa: F401
