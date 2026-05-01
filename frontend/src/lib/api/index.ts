/**
 * Barrel re-export — reconstructs the `api` object with the exact same shape
 * as the original monolithic api.ts for full backward compatibility.
 *
 * Usage: import { api } from "@/lib/api"
 */

import { auth } from "./auth";
import { tasks, approvals } from "./tasks";
import { documents } from "./documents";
import { erp } from "./erp";
import { banking } from "./banking";
import { analytics } from "./analytics";
import { crm } from "./crm";
import { hr } from "./hr";
import { projects } from "./projects";
import { accounting } from "./accounting";
import { reports, advisory } from "./reports";
import { workflows } from "./workflows";
import { tenant } from "./tenant";
import { admin } from "./admin";
import { integrations } from "./integrations";
import { system } from "./system";
import { templatesApi } from "./templates";
import { albaranes } from "./albaranes";
import { aiEmployees } from "./ai_employees";
import { recruitment } from "./recruitment";
import { scanner } from "./scanner";
import { messaging } from "./messaging";
import { hrDocuments } from "./hr_documents";
import { generativeUI } from "./generative_ui";

// ── Re-export the api object with the original shape ─────────────────────────
export const api = {
    auth,
    tasks,
    approvals,
    documents,
    erp,
    banking,
    analytics,
    crm,
    hr,
    projects,
    accounting,
    reports,
    advisory,
    workflows,
    tenant,
    admin,
    integrations,
    system,
    templates: templatesApi,
    albaranes,
    aiEmployees,
    recruitment,
    scanner,
    messaging,
    hrDocuments,
    generativeUI,
};

// ── Re-export all interfaces from domain modules ─────────────────────────────
export type { Task, AuditEntry, Approval } from "./tasks";
export type { ContractPreviewHtml, Document } from "./documents";
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
} from "./erp";
export type { BankTransaction } from "./banking";
export type { AnalyticsDashboard } from "./analytics";
export type { AnalyticsCashflowEntry } from "./analytics";
export type { AnalyticsTopCliente } from "./analytics";
export type { AnalyticsEstadoFactura } from "./analytics";
export type { AnalyticsFacturas } from "./analytics";
export type { AnalyticsRRHH } from "./analytics";
export type { AnalyticsBanca } from "./analytics";
export type { AnalyticsIA } from "./analytics";
export type { AnalyticsClientes } from "./analytics";
export type { Opportunity, Activity, EventItem, Reservation } from "./crm";
export type { Employee, Payroll, PayrollCalculation } from "./hr";
export type { Project, ProjectTask } from "./projects";
export type { JournalEntry, JournalLine, FixedAsset } from "./accounting";
export type { CompanySnapshot, ReportDoc, FiscalSnapshot } from "./reports";
export type { Workflow, WorkflowExecution } from "./workflows";
export type {
    LlmProviderEntry,
    LlmConfigResponse,
    LlmProviderConfigUpdate,
    LlmConfigUpdate,
    ClaudeCodeSetupResponse,
} from "./tenant";
export type { IntegrationStatus, GmailMessage, DriveFile, OutlookMessage, OneDriveFile } from "./integrations";
export type { DeliveryNote, DeliveryNoteLine, DeliveryNoteCreate } from "./albaranes";
export type { AIEmployee, ActivityEntry } from "./ai_employees";
export type { RecruitmentPosition, Candidate } from "./recruitment";
export type { ScannerToken, ScannedProduct, StockMovementResult } from "./scanner";
export type { TelegramConnectResponse, TelegramStatus } from "./messaging";
export type { HRDocument, HRDocumentGeneratePayload } from "./hr_documents";
export type { GenerativeInterface } from "./generative_ui";
