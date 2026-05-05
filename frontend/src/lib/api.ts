/**
 * Re-export from modular api/ directory for backward compatibility.
 * All consumers importing from "@/lib/api" continue to work unchanged.
 */
export { api } from "./api/index";

// Re-export all types
export type { Task, AuditEntry, Approval } from "./api/tasks";
export type { Document } from "./api/documents";
export type {
    Client,
    Invoice,
    InvoiceLine,
    Product,
    StockMovement,
    Quote,
    QuoteLine,
    SalesOrder,
    SalesOrderLine,
    PurchaseOrder,
    PurchaseOrderLine,
    RecurringInvoice,
    RecurringLineItem,
} from "./api/erp";
export type { BankTransaction, InvoiceSuggestion, ReconciliationSuggestion } from "./api/banking";
export type {
    AnalyticsDashboard,
    AnalyticsCashflowEntry,
    AnalyticsTopCliente,
    AnalyticsEstadoFactura,
    AnalyticsFacturas,
    AnalyticsRRHH,
    AnalyticsBanca,
    AnalyticsIA,
    AnalyticsClientes,
} from "./api/analytics";
export type { Opportunity, Activity, EventItem, Reservation } from "./api/crm";
export type { Employee, Payroll, PayrollCalculation, WorkSchedule, AttendanceRecord, LeaveRequest, Expense } from "./api/hr";
export type { Project, ProjectTask } from "./api/projects";
export type { JournalEntry, JournalLine, FixedAsset } from "./api/accounting";
export type { CompanySnapshot, ReportDoc, FiscalSnapshot } from "./api/reports";
export type { Workflow, WorkflowExecution } from "./api/workflows";
export type {
    LlmProviderEntry,
    LlmConfigResponse,
    LlmProviderConfigUpdate,
    LlmConfigUpdate,
    CertificateStatus,
} from "./api/tenant";
export type { IntegrationStatus, GmailMessage, DriveFile, OutlookMessage, OneDriveFile } from "./api/integrations";
export type { SearchResult, PortalData } from "./api/index";
export type { AlertEntry } from "./api/alerts";
export type { UnifiedCalendarEvent } from "./api/calendar_unified";
export type {
    User,
    UserCreate,
    UserUpdate,
    Invitation,
    InvitationCreated,
    InvitationCreate,
    InvitationPublic,
    InvitationAccept,
    InvitationAcceptResponse,
} from "./api/users";
