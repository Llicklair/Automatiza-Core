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
import { alertsApi } from "./alerts";
import { calendarUnified } from "./calendar_unified";
import { users } from "./users";
import { regap } from "./regap";
import { autonomy } from "./autonomy";
import { onboarding } from "./onboarding";
import { notificationsApi } from "./notifications";
import { verifactuConfig } from "./verifactuConfig";
import { presentacion } from "./presentacion";
import { pos } from "./pos";
import { modelosAeat } from "./modelosAeat";
import { request } from "./client";

// ── Portal types ─────────────────────────────────────────────────────────────
export interface PortalData {
    employee: import("./hr").Employee | null;
    payrolls: import("./hr").Payroll[];
    leave_requests: import("./hr").LeaveRequest[];
    schedule?: import("./hr").WorkSchedule[];
    active_attendance?: import("./hr").AttendanceRecord | null;
    read_only?: boolean;
}

export interface SearchResult {
    type: "employee" | "client" | "invoice";
    id: string;
    label: string;
    sublabel: string;
    href: string;
}

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
    alerts: alertsApi,
    calendarUnified,
    users,
    regap,
    autonomy,
    onboarding,
    notifications: notificationsApi,
    verifactuConfig,
    presentacion,
    pos,
    modelosAeat,
    search: (q: string) => request<SearchResult[]>(`/api/v1/search?q=${encodeURIComponent(q)}`),
    importBulk: {
        employees: (rows: Record<string, string>[]) =>
            request<{ imported: number; errors: { row: number; reason: string }[] }>("/api/v1/import/employees", { method: "POST", body: JSON.stringify({ rows }) }),
        clients: (rows: Record<string, string>[]) =>
            request<{ imported: number; errors: { row: number; reason: string }[] }>("/api/v1/import/clients", { method: "POST", body: JSON.stringify({ rows }) }),
        products: (rows: Record<string, string>[]) =>
            request<{ imported: number; errors: { row: number; reason: string }[] }>("/api/v1/import/products", { method: "POST", body: JSON.stringify({ rows }) }),
    },
    portal: {
        me: () => request<PortalData>("/api/v1/portal/me"),
        meAs: (employeeId: string) =>
            request<PortalData>(`/api/v1/portal/as/${employeeId}`),
        clockIn: (notes?: string) =>
            request<import("./hr").AttendanceRecord>("/api/v1/portal/clock-in", {
                method: "POST",
                body: JSON.stringify({ notes }),
            }),
        clockOut: () =>
            request<import("./hr").AttendanceRecord>("/api/v1/portal/clock-out", {
                method: "POST",
            }),
        submitLeave: (data: { leave_type: string; start_date: string; end_date: string; notes?: string }) =>
            request<import("./hr").LeaveRequest>("/api/v1/portal/leave-requests", {
                method: "POST",
                body: JSON.stringify({ ...data, employee_id: "00000000-0000-0000-0000-000000000000" }),
            }),
    },
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
    StockValuation,
    StockValuationByCategory,
    Quote,
    QuoteLine,
    SalesOrder,
    SalesOrderLine,
    PurchaseOrder,
    PurchaseOrderLine,
    RecurringInvoice,
    RecurringLineItem,
} from "./erp";
export type { BankTransaction, InvoiceSuggestion, ReconciliationSuggestion } from "./banking";
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
export type { Employee, Payroll, PayrollCalculation, WorkSchedule, AttendanceRecord, LeaveRequest, Expense } from "./hr";
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
    CertificateStatus,
    LogoStatus,
} from "./tenant";
export type { IntegrationStatus, GmailMessage, DriveFile, OutlookMessage, OneDriveFile, EmailConnectInput, EmailConnectStatus } from "./integrations";
export type { DeliveryNote, DeliveryNoteLine, DeliveryNoteCreate } from "./albaranes";
export type { AIEmployee, ActivityEntry } from "./ai_employees";
export type { RecruitmentPosition, Candidate } from "./recruitment";
export type { ScannerToken, ScannedProduct, StockMovementResult } from "./scanner";
export type { TelegramConnectResponse, TelegramStatus } from "./messaging";
export type { HRDocument, HRDocumentGeneratePayload } from "./hr_documents";
export type { GenerativeInterface } from "./generative_ui";
export type { AlertEntry } from "./alerts";
export type { UnifiedCalendarEvent } from "./calendar_unified";
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
} from "./users";
export type { RegapStatus, RegapStatusValue, RegapAuthMethod } from "./regap";
export type { AutonomyMode, PolicyEntry, PolicyList } from "./autonomy";
export type { OnboardingState, OnboardingStepKey, Simulate303Result, Simulate303Row } from "./onboarding";
export type { PersistentNotification, NotificationListResponse } from "./notifications";
export type { VerifactuMode, VerifactuConfig } from "./verifactuConfig";
export type { ModeloAsistido, PresentacionInfo } from "./presentacion";
export type { PosLine, PosSession, PosLineAdd, PosCheckoutRequest } from "./pos";
