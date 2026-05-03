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
export type { BankTransaction } from "./api/banking";
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
export type { Employee, Payroll, PayrollCalculation } from "./api/hr";
export type { Project, ProjectTask } from "./api/projects";
export type { JournalEntry, JournalLine, FixedAsset } from "./api/accounting";
export type { CompanySnapshot, ReportDoc, FiscalSnapshot } from "./api/reports";
export type { Workflow, WorkflowExecution } from "./api/workflows";
export type {
    LlmProviderEntry,
    LlmConfigResponse,
    LlmProviderConfigUpdate,
    LlmConfigUpdate,
} from "./api/tenant";
export type { IntegrationStatus, GmailMessage, DriveFile, OutlookMessage, OneDriveFile } from "./api/integrations";
