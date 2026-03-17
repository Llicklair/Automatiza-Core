"""Paquete de modelos SQLAlchemy.

Importa todos los modulos de dominio para que Alembic detecte
todas las tablas al inspeccionar Base.metadata.
"""

from .auth import Tenant, User  # noqa: F401
from .tasks import Task, AuditLog, PendingApproval  # noqa: F401
from .tenant import TenantIntegration, TenantKnowledge, TenantDocument  # noqa: F401
from .crm import Client, Opportunity, Activity  # noqa: F401
from .billing import Invoice, InvoiceLine, Quote, QuoteLine, RecurringInvoice  # noqa: F401
from .inventory import Product, StockMovement  # noqa: F401
from .orders import SalesOrder, SalesOrderLine, PurchaseOrder, PurchaseOrderLine  # noqa: F401
from .hr import Employee, Payroll  # noqa: F401
from .accounting import JournalEntry, JournalLine, BankTransaction, FixedAsset  # noqa: F401
from .projects import Project, ProjectTask  # noqa: F401
from .calendar import Event, Reservation  # noqa: F401
from .workflows import Workflow, WorkflowExecution, DomainEvent  # noqa: F401
