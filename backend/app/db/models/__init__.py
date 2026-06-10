"""Paquete de modelos SQLAlchemy.

Importa todos los modulos de dominio para que Alembic detecte
todas las tablas al inspeccionar Base.metadata.
"""

from .accounting import BankTransaction, FixedAsset, JournalEntry, JournalLine  # noqa: F401
from .ai_employees import (  # noqa: F401
    ActivityEntry,
    AgentSkill,
    AIEmployee,
    EmployeeMemory,
    TokenLedger,
)
from .alerts import AlertLog  # noqa: F401
from .auth import (  # noqa: F401
    ClientPortalToken,
    PasswordResetToken,
    Tenant,
    TenantRegapStatus,
    User,
    UserInvitation,
)
from .billing import (  # noqa: F401
    Invoice,
    InvoiceLine,
    InvoiceSeries,
    Quote,
    QuoteLine,
    RecurringInvoice,
    VerifactuConfig,
)
from .calendar import Event, Reservation  # noqa: F401
from .crm import Activity, Client, Opportunity  # noqa: F401
from .generative_ui import GeneratedUI  # noqa: F401
from .hr import Candidate, Employee, Payroll, RecruitmentPosition  # noqa: F401
from .hr_documents import HRDocument  # noqa: F401
from .inventory import Product, ProductLot, ProductStock, StockMovement, Warehouse  # noqa: F401
from .notifications import Notification  # noqa: F401
from .orders import PurchaseOrder, PurchaseOrderLine, SalesOrder, SalesOrderLine  # noqa: F401
from .pos import PosSession, PosSessionLine  # noqa: F401
from .projects import Project, ProjectTask  # noqa: F401
from .reconciliation import ReconciliationRejection  # noqa: F401
from .signed_document import SignedDocument  # noqa: F401
from .supplier_learning import InvoiceScanCache, SupplierInvoiceTemplate  # noqa: F401
from .tasks import AuditLog, IdempotencyKey, PendingApproval, Task  # noqa: F401
from .treasury import SepaRemittance, SepaRemittanceOrder  # noqa: F401
from .tenant import (  # noqa: F401
    AutonomyPolicy,
    TenantDocument,
    TenantIntegration,
    TenantKnowledge,
    TenantLlmConfig,
    TenantOnboarding,
)
from .workflow_template import WorkflowTemplate  # noqa: F401
from .workflows import DomainEvent, Workflow, WorkflowExecution  # noqa: F401
from .marketing import Campaign, ScheduledPost, SocialAccount  # noqa: F401
from .email_marketing import EmailCampaign, EmailCampaignRecipient, EmailTemplate  # noqa: F401
