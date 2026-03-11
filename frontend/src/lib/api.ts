/**
 * Cliente de la API — encapsula fetch con token JWT.
 * Uso: import { api } from "@/lib/api"
 */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8080";

function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
}

async function request<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(options.headers as Record<string, string>),
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
        // Token expirado — intentar refresh
        const refreshed = await tryRefresh();
        if (refreshed) {
            headers["Authorization"] = `Bearer ${getToken()}`;
            const retry = await fetch(`${BASE}${path}`, { ...options, headers });
            if (!retry.ok) throw new Error(await retry.text());
            return retry.json();
        }
        // Refresh falló → logout
        localStorage.clear();
        window.location.href = "/login";
        throw new Error("Sesión expirada");
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Error desconocido");
    }

    if (res.status === 204) return undefined as T;
    return res.json();
}

async function tryRefresh(): Promise<boolean> {
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return false;
    try {
        const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        return true;
    } catch {
        return false;
    }
}

export const api = {
    auth: {
        login: (email: string, password: string) =>
            request<{ access_token: string; refresh_token: string; token_type: string }>(
                "/api/v1/auth/login",
                { method: "POST", body: JSON.stringify({ email, password }) }
            ),
        register: (data: {
            email: string;
            password: string;
            full_name?: string;
            tenant: { name: string; nif: string };
        }) =>
            request("/api/v1/auth/register", {
                method: "POST",
                body: JSON.stringify(data),
            }),
    },

    tasks: {
        list: (params?: { status?: string; skip?: number; limit?: number }) => {
            const q = new URLSearchParams(params as Record<string, string>).toString();
            return request<Task[]>(`/api/v1/tasks${q ? "?" + q : ""}`);
        },
        create: (domain: string, user_intent: string) =>
            request<Task>("/api/v1/tasks", {
                method: "POST",
                body: JSON.stringify({ domain, user_intent }),
            }),
        get: (id: string) => request<Task>(`/api/v1/tasks/${id}`),
        cancel: (id: string) =>
            request(`/api/v1/tasks/${id}`, { method: "DELETE" }),
        audit: (id: string) => request<AuditEntry[]>(`/api/v1/tasks/${id}/audit`),
        cleanup: () => request<{ deleted: number }>("/api/v1/tasks/cleanup", { method: "DELETE" }),
    },

    approvals: {
        list: () => request<Approval[]>("/api/v1/approvals"),
        decide: (id: string, approved: boolean, rejection_reason?: string) =>
            request<Approval>(`/api/v1/approvals/${id}/decide`, {
                method: "POST",
                body: JSON.stringify({ approved, rejection_reason }),
            }),
        cleanup: () => request<{ deleted: number }>("/api/v1/approvals/cleanup", { method: "DELETE" }),
    },

    documents: {
        list: (params?: { category?: string; skip?: number; limit?: number }) => {
            const q = new URLSearchParams(params as Record<string, string>).toString();
            return request<Document[]>(`/api/v1/documents${q ? "?" + q : ""}`);
        },
        upload: async (file: File, category?: string): Promise<Document> => {
            const token = getToken();
            const form = new FormData();
            form.append("file", file);
            if (category) form.append("category", category);

            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch(`${BASE}/api/v1/documents/upload`, {
                method: "POST",
                headers,
                body: form,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail ?? "Error al subir archivo");
            }
            return res.json();
        },
        importDB: async (files: File[]): Promise<{ document_id: string; file_name: string; rows_detected: number; columns: string[]; category: string; task_id: string | null; message: string }[]> => {
            const token = getToken();
            const form = new FormData();
            for (const f of files) form.append("files", f);

            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch(`${BASE}/api/v1/documents/import-db`, {
                method: "POST",
                headers,
                body: form,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail ?? "Error al importar base de datos");
            }
            return res.json();
        },
        scan: async (files: File[]): Promise<{ document: Document; auto_category: string; message: string }[]> => {
            const token = getToken();
            const form = new FormData();
            for (const f of files) form.append("files", f);

            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch(`${BASE}/api/v1/documents/scan`, {
                method: "POST",
                headers,
                body: form,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail ?? "Error al escanear archivos");
            }
            return res.json();
        },
        uploadBulk: async (file: File, category?: string): Promise<Document[]> => {
            const token = getToken();
            const form = new FormData();
            form.append("file", file);
            if (category) form.append("category", category);

            const headers: Record<string, string> = {};
            if (token) headers["Authorization"] = `Bearer ${token}`;
            const res = await fetch(`${BASE}/api/v1/documents/bulk`, {
                method: "POST",
                headers,
                body: form,
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: res.statusText }));
                throw new Error(err.detail ?? "Error al subir archivo ZIP");
            }
            return res.json();
        },
    },

    erp: {
        clients: {
            list: (params?: { skip?: number; limit?: number; client_type?: string }) => {
                const q = new URLSearchParams(params as Record<string, string>).toString();
                return request<Client[]>(`/api/v1/clients${q ? "?" + q : ""}`);
            },
            create: (data: Partial<Client>) =>
                request<Client>("/api/v1/clients", {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            update: (id: string, data: Partial<Client>) =>
                request<Client>(`/api/v1/clients/${id}`, {
                    method: "PATCH",
                    body: JSON.stringify(data),
                }),
            delete: (id: string) =>
                request<void>(`/api/v1/clients/${id}`, { method: "DELETE" }),
            invoices: (id: string, params?: { skip?: number; limit?: number }) => {
                const q = new URLSearchParams(params as Record<string, string>).toString();
                return request<Invoice[]>(`/api/v1/clients/${id}/invoices${q ? "?" + q : ""}`);
            },
            createInvoice: (clientId: string, data: Partial<Invoice>) =>
                request<Invoice>(`/api/v1/clients/${clientId}/invoices`, {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
        },
        products: {
            list: (params?: { skip?: number; limit?: number }) => {
                const q = new URLSearchParams(params as Record<string, string>).toString();
                return request<Product[]>(`/api/v1/products${q ? "?" + q : ""}`);
            },
            create: (data: Partial<Product>) =>
                request<Product>("/api/v1/products", {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            update: (id: string, data: Partial<Product>) =>
                request<Product>(`/api/v1/products/${id}`, {
                    method: "PATCH",
                    body: JSON.stringify(data),
                }),
            delete: (id: string) =>
                request<void>(`/api/v1/products/${id}`, { method: "DELETE" }),
        },
        invoices: {
            list: (params?: { skip?: number; limit?: number }) => {
                const q = new URLSearchParams(params as Record<string, string>).toString();
                return request<Invoice[]>(`/api/v1/invoices${q ? "?" + q : ""}`);
            },
            get: (id: string) => request<Invoice>(`/api/v1/invoices/${id}`),
            create: (clientId: string, data: Partial<Invoice>) =>
                request<Invoice>(`/api/v1/clients/${clientId}/invoices`, {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            updateStatus: (id: string, status: string) =>
                request<Invoice>(`/api/v1/invoices/${id}/status`, {
                    method: "PATCH",
                    body: JSON.stringify({ status }),
                }),
            delete: (id: string) =>
                request<void>(`/api/v1/invoices/${id}`, { method: "DELETE" }),
        },
        quotes: {
            list: (params?: { skip?: number; limit?: number }) => {
                const q = new URLSearchParams(params as Record<string, string>).toString();
                return request<Quote[]>(`/api/v1/quotes${q ? "?" + q : ""}`);
            },
            create: (data: Partial<Quote>) =>
                request<Quote>("/api/v1/quotes", {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            update: (id: string, data: Partial<Quote>) =>
                request<Quote>(`/api/v1/quotes/${id}`, {
                    method: "PATCH",
                    body: JSON.stringify(data),
                }),
            convertToInvoice: (id: string) =>
                request<{ invoice_id: string; invoice_number: string; amount_total: number; message: string }>(
                    `/api/v1/quotes/${id}/convert-to-invoice`,
                    { method: "POST" }
                ),
            delete: (id: string) => request<void>(`/api/v1/quotes/${id}`, { method: "DELETE" }),
        },
        orders: {
            list: () => request<SalesOrder[]>("/api/v1/orders"),
            create: (data: Partial<SalesOrder> & { lines?: SalesOrderLine[] }) =>
                request<SalesOrder>("/api/v1/orders", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: Partial<SalesOrder>) =>
                request<SalesOrder>(`/api/v1/orders/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
            delete: (id: string) => request<void>(`/api/v1/orders/${id}`, { method: "DELETE" }),
        },
        purchaseOrders: {
            list: () => request<PurchaseOrder[]>("/api/v1/purchase-orders"),
            create: (data: Partial<PurchaseOrder> & { lines?: PurchaseOrderLine[] }) =>
                request<PurchaseOrder>("/api/v1/purchase-orders", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: Partial<PurchaseOrder>) =>
                request<PurchaseOrder>(`/api/v1/purchase-orders/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
            delete: (id: string) => request<void>(`/api/v1/purchase-orders/${id}`, { method: "DELETE" }),
        },
        recurring: {
            list: () => request<RecurringInvoice[]>("/api/v1/recurring-invoices"),
            create: (data: Partial<RecurringInvoice> & { lines?: RecurringLineItem[] }) =>
                request<RecurringInvoice>("/api/v1/recurring-invoices", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: Partial<RecurringInvoice> & { lines?: RecurringLineItem[] }) =>
                request<RecurringInvoice>(`/api/v1/recurring-invoices/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
            delete: (id: string) => request<void>(`/api/v1/recurring-invoices/${id}`, { method: "DELETE" }),
            run: (id: string) => request<Invoice>(`/api/v1/recurring-invoices/${id}/run`, { method: "POST" }),
        },
        stock: {
            movements: (productId: string) => request<StockMovement[]>(`/api/v1/products/${productId}/stock-movements`),
            addMovement: (productId: string, data: Partial<StockMovement>) =>
                request<StockMovement>(`/api/v1/products/${productId}/stock-movements`, {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
        },
    },


    banking: {
        summary: () => request<{ ingresos: number; gastos: number; neto: number; margen: number; is_demo: boolean }>("/api/v1/banking/summary"),
        analytics: () => request<{ cashflow: { month: string, ingresos: number, gastos: number }[], insights: { id: string, type: 'success' | 'warning' | 'info' | 'error', title: string, message: string, action_text: string, action_url: string }[] }>("/api/v1/banking/analytics"),
        transactions: {
            list: () => request<BankTransaction[]>("/api/v1/banking/transactions"),
            sync: () => request<{ message: string; status: string }>("/api/v1/banking/transactions/sync", { method: "POST" }),
            reconcile: (id: string, invoice_id: string) => request<{ message: string; status: string }>(`/api/v1/banking/transactions/${id}/reconcile`, {
                method: "POST",
                body: JSON.stringify({ invoice_id })
            })
        }
    },

    crm: {
        opportunities: {
            list: () => request<Opportunity[]>("/api/v1/crm/opportunities"),
            create: (data: Partial<Opportunity>) =>
                request<Opportunity>("/api/v1/crm/opportunities", {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            update: (id: string, data: Partial<Opportunity>) =>
                request<Opportunity>(`/api/v1/crm/opportunities/${id}`, {
                    method: "PATCH",
                    body: JSON.stringify(data),
                }),
            delete: (id: string) =>
                request<void>(`/api/v1/crm/opportunities/${id}`, { method: "DELETE" }),
        },
        activities: {
            list: (params?: { client_id?: string; opportunity_id?: string }) => {
                const q = new URLSearchParams(params as Record<string, string>).toString();
                return request<Activity[]>(`/api/v1/crm/activities${q ? "?" + q : ""}`);
            },
            create: (data: Partial<Activity>) =>
                request<Activity>("/api/v1/crm/activities", {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            delete: (id: string) => request<void>(`/api/v1/crm/activities/${id}`, { method: "DELETE" }),
        },
        events: {
            list: () => request<EventItem[]>("/api/v1/crm/events"),
            create: (data: Partial<EventItem>) =>
                request<EventItem>("/api/v1/crm/events", {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            update: (id: string, data: Partial<EventItem>) =>
                request<EventItem>(`/api/v1/crm/events/${id}`, {
                    method: "PATCH",
                    body: JSON.stringify(data),
                }),
            delete: (id: string) =>
                request<void>(`/api/v1/crm/events/${id}`, { method: "DELETE" }),
        },
        reservations: {
            list: () => request<Reservation[]>("/api/v1/crm/reservations"),
            create: (data: Partial<Reservation>) =>
                request<Reservation>("/api/v1/crm/reservations", {
                    method: "POST",
                    body: JSON.stringify(data),
                }),
            update: (id: string, data: Partial<Reservation>) =>
                request<Reservation>(`/api/v1/crm/reservations/${id}`, {
                    method: "PATCH",
                    body: JSON.stringify(data),
                }),
            delete: (id: string) =>
                request<void>(`/api/v1/crm/reservations/${id}`, { method: "DELETE" }),
        }
    },

    hr: {
        employees: {
            list: () => request<Employee[]>("/api/v1/hr/employees"),
            create: (data: Partial<Employee>) => request<Employee>("/api/v1/hr/employees", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: Partial<Employee>) => request<Employee>(`/api/v1/hr/employees/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
            delete: (id: string) => request(`/api/v1/hr/employees/${id}`, { method: "DELETE" }),
        },
        payrolls: {
            list: () => request<Payroll[]>("/api/v1/hr/payrolls"),
            generate: (data: Partial<Payroll>) => request<Payroll>("/api/v1/hr/payrolls", { method: "POST", body: JSON.stringify(data) }),
            approve: (id: string) => request<Payroll>(`/api/v1/hr/payrolls/${id}/approve`, { method: "POST" }),
            downloadPdf: async (id: string, filename: string) => {
                const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
                const res = await fetch(`${BASE}/api/v1/hr/payrolls/${id}/pdf`, {
                    headers: { Authorization: `Bearer ${token}` },
                });
                if (!res.ok) throw new Error("Error descargando PDF");
                const blob = await res.blob();
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url; a.download = filename; a.click();
                URL.revokeObjectURL(url);
            },
        }
    },


    projects: {
        list: () => request<Project[]>("/api/v1/projects"),
        create: (data: Partial<Project>) => request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
        update: (id: string, data: Partial<Project>) => request<Project>(`/api/v1/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request<void>(`/api/v1/projects/${id}`, { method: "DELETE" }),
        tasks: {
            list: (params?: { project_id?: string }) => {
                const q = params?.project_id ? `?project_id=${params.project_id}` : "";
                return request<ProjectTask[]>(`/api/v1/projects/tasks${q}`);
            },
            create: (data: Partial<ProjectTask>) => request<ProjectTask>("/api/v1/projects/tasks", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: Partial<ProjectTask>) => request<ProjectTask>(`/api/v1/projects/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
            delete: (id: string) => request<void>(`/api/v1/projects/tasks/${id}`, { method: "DELETE" }),
        }
    },

    accounting: {
        journal: {
            list: () => request<JournalEntry[]>("/api/v1/accounting/journal"),
            create: (data: Partial<JournalEntry>) => request<JournalEntry>("/api/v1/accounting/journal", { method: "POST", body: JSON.stringify(data) }),
        },
        assets: {
            list: () => request<FixedAsset[]>("/api/v1/accounting/assets"),
            create: (data: Partial<FixedAsset>) => request<FixedAsset>("/api/v1/accounting/assets", { method: "POST", body: JSON.stringify(data) }),
            update: (id: string, data: Partial<FixedAsset>) => request<FixedAsset>(`/api/v1/accounting/assets/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
            delete: (id: string) => request(`/api/v1/accounting/assets/${id}`, { method: "DELETE" }),
        },
    },

    reports: {
        snapshot: (month?: string) =>
            request<CompanySnapshot>(`/api/v1/reports/company-snapshot${month ? `?month=${month}` : ""}`),
        generate: (month?: string) =>
            request<ReportDoc>(`/api/v1/reports/company-snapshot/generate${month ? `?month=${month}` : ""}`, { method: "POST" }),
        list: () => request<ReportDoc[]>("/api/v1/reports/"),
        download: (id: string) => `/api/v1/reports/${id}/download`,
    },

    advisory: {
        boe: (section: string = "fiscal", limit: number = 10) =>
            request<any[]>(`/api/v1/advisory/boe?section=${section}&limit=${limit}`),
        calendar: (days_ahead: number = 60) =>
            request<any[]>(`/api/v1/advisory/calendar?days_ahead=${days_ahead}`),
        guides: (section: string = "fiscal") =>
            request<any[]>(`/api/v1/advisory/guides?section=${section}`),
    },

    workflows: {
        list: () => request<Workflow[]>("/api/v1/workflows"),
        create: (data: Partial<Workflow>) => request<Workflow>("/api/v1/workflows", { method: "POST", body: JSON.stringify(data) }),
        parse: (text: string) => request<any>("/api/v1/workflows/parse-nl", { method: "POST", body: JSON.stringify({ text }) }),
        update: (id: string, data: Partial<Workflow>) => request<Workflow>(`/api/v1/workflows/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
        delete: (id: string) => request(`/api/v1/workflows/${id}`, { method: "DELETE" }),
        run: (id: string) => request<WorkflowExecution>(`/api/v1/workflows/${id}/run`, { method: "POST" }),
        executions: (id: string) => request<WorkflowExecution[]>(`/api/v1/workflows/${id}/executions`),
        resumeExecution: (workflowId: string, executionId: string) =>
            request<WorkflowExecution>(`/api/v1/workflows/${workflowId}/executions/${executionId}/resume`, { method: "POST" }),
    },

    tenant: {
        me: () => request<{ id: string; name: string; nif: string }>("/api/v1/tenant/me"),
        updateMe: (data: { name?: string; nif?: string }) =>
            request<{ id: string; name: string; nif: string }>("/api/v1/tenant/me", {
                method: "PATCH",
                body: JSON.stringify(data),
            }),
    },

    integrations: {
        list: () => request<IntegrationStatus[]>("/api/v1/integrations/"),
        connectHolded: (apiKey: string) =>
            request<{ status: string }>("/api/v1/integrations/holded/connect", {
                method: "POST", body: JSON.stringify({ api_key: apiKey }),
            }),
        disconnectHolded: () =>
            request("/api/v1/integrations/holded/disconnect", { method: "DELETE" }),
        connectPsd2: (secretId: string, secretKey: string) =>
            request<{ status: string }>("/api/v1/integrations/psd2/connect", {
                method: "POST", body: JSON.stringify({ secret_id: secretId, secret_key: secretKey }),
            }),
        disconnectPsd2: () =>
            request("/api/v1/integrations/psd2/disconnect", { method: "DELETE" }),
        oauthUrl: (provider: "google" | "microsoft") =>
            request<{ auth_url: string }>(`/api/v1/integrations/${provider}/auth-url`),
        disconnect: (type: string) =>
            request(`/api/v1/integrations/${type}/disconnect`, { method: "DELETE" }),
    },
};

// ── Tipos compartidos ─────────────────────────────────────────────────────────

export interface IntegrationStatus {
    integration_type: string;
    is_active: boolean;
    last_sync_at?: string;
}

export interface Workflow {
    id: string;
    tenant_id: string;
    name: string;
    description: string | null;
    is_active: boolean;
    trigger_type: string;
    trigger_config: any;
    action_type: string;
    action_config: any;
    ui_nodes?: any[];
    ui_edges?: any[];
    execution_mode: "reasoning" | "deterministic";
    compiled_steps?: Array<{ agent: string; action: string; params: { intent: string } }> | null;
    created_at: string;
}

export interface WorkflowExecution {
    id: string;
    workflow_id: string;
    tenant_id: string;
    status: string; // running | completed | success | failed | paused
    started_at: string;
    completed_at: string | null;
    trigger_payload: any;
    result_log: string | null;
    task_id: string | null;
    node_states: Record<string, { status: string; output?: any; started_at?: string; completed_at?: string }> | null;
    current_node_id: string | null;
    paused_at: string | null;
}

export interface Task {
    id: string;
    tenant_id: string;
    status: string;
    domain: string;
    user_intent: string;
    plan: any[];
    agent_results?: any[];
    current_step: number;
    requires_human_approval: boolean;
    error_message: string | null;
    created_at: string;
    started_at: string | null;
    completed_at: string | null;
}

export interface AuditEntry {
    id: number;
    task_id: string;
    agent_name: string;
    action_type: string;
    input_data: unknown;
    output_data: unknown;
    status: string;
    error_detail: string | null;
    executed_at: string;
}

export interface Approval {
    id: string;
    task_id: string;
    action_description: string;
    action_payload: unknown;
    risk_level: string;
    expires_at: string;
    status: string;
}

export interface Document {
    id: string;
    file_name: string;
    file_type: string | null;
    file_size: number;
    status: string;
    category: string | null;
    parsed_content: string | null;
    created_at: string;
    processed_at: string | null;
    task_id: string | null;
}

export interface BankTransaction {
    id: string;
    date: string;
    description: string;
    amount: number;
    balance: number | null;
    status: string; // unreconciled, reconciled, ignored
    invoice_id: string | null;
}

export interface Client {
    id: string;
    nif: string | null;
    name: string;
    email: string | null;
    address: string | null;
    city: string | null;
    postal_code: string | null;
    client_type: string;
    holded_id: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface Opportunity {
    id: string;
    tenant_id: string;
    client_id: string;
    title: string;
    expected_value: number;
    stage: 'new' | 'qualified' | 'proposal' | 'won' | 'lost';
    created_at: string;
    updated_at: string;
    client?: Client;
}

export interface Product {
    id: string;
    tenant_id: string;
    item_type: string;
    sku: string | null;
    name: string;
    description: string | null;
    price: number;
    tax_percentage: number;
    stock_quantity: number;
    stock_min_alert: number;
    created_at: string;
    updated_at: string | null;
}

export interface StockMovement {
    id: string;
    tenant_id: string;
    product_id: string;
    movement_type: string;
    quantity: number;
    stock_after: number;
    reference: string | null;
    notes: string | null;
    created_at: string;
}

export interface SalesOrderLine {
    id?: string;
    product_id?: string | null;
    description: string;
    quantity: number;
    unit_price: number;
    discount_percentage: number;
    tax_percentage: number;
    total?: number;
}

export interface SalesOrder {
    id: string;
    tenant_id: string;
    client_id: string;
    order_number: string | null;
    date: string;
    expected_delivery: string | null;
    status: string;
    amount_base: number;
    tax_amount: number;
    amount_total: number;
    notes: string | null;
    quote_id: string | null;
    created_at: string;
    updated_at: string;
    client?: Client;
    lines?: SalesOrderLine[];
}

export interface PurchaseOrderLine {
    id?: string;
    product_id?: string | null;
    description: string;
    quantity: number;
    unit_price: number;
    tax_percentage: number;
    total?: number;
}

export interface PurchaseOrder {
    id: string;
    tenant_id: string;
    supplier_id: string;
    order_number: string | null;
    date: string;
    expected_delivery: string | null;
    status: string;
    amount_base: number;
    tax_amount: number;
    amount_total: number;
    notes: string | null;
    created_at: string;
    updated_at: string;
    supplier?: Client;
    lines?: PurchaseOrderLine[];
}

export interface RecurringLineItem {
    description: string;
    quantity: number;
    unit_price: number;
    tax_percentage: number;
}

export interface RecurringInvoice {
    id: string;
    tenant_id: string;
    client_id: string;
    name: string;
    interval_type: string;
    next_run_date: string;
    last_run_date: string | null;
    is_active: boolean;
    lines_json: RecurringLineItem[];
    notes: string | null;
    terms: string | null;
    created_at: string;
    updated_at: string;
    client?: Client;
}

export interface InvoiceLine {
    id?: string;
    product_id?: string | null;
    description: string;
    quantity: number;
    unit_price: number;
    discount_percentage: number;
    tax_percentage: number;
    total?: number;
}

export interface Invoice {
    id: string;
    client_id: string;
    invoice_number: string | null;
    date: string;
    due_date: string | null;
    amount_base: number;
    tax_amount: number;
    amount_total: number;
    status: string;
    invoice_type: string;
    notes: string | null;
    terms: string | null;
    external_id: string | null;
    created_at: string;
    updated_at: string | null;
    client?: Client;
    lines?: InvoiceLine[];
}

export interface Employee {
    id: string;
    tenant_id: string;
    nif: string | null;
    name: string;
    department: string | null;
    role: string | null;
    base_salary: number | null;
    status: string;
    join_date: string | null;
    contract_end_date: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface Payroll {
    id: string;
    tenant_id: string;
    employee_id: string;
    period_start: string;
    period_end: string;
    issue_date: string;
    base_salary: number;
    deductions: number;
    net_salary: number;
    status: string;
    created_at: string;
    employee?: Employee;
}

export interface Project {
    id: string;
    tenant_id: string;
    client_id: string | null;
    name: string;
    description: string | null;
    budget: number;
    status: string;
    start_date: string | null;
    due_date: string | null;
    created_at: string;
}

export interface ProjectTask {
    id: string;
    tenant_id: string;
    project_id: string;
    assignee_id: string | null;
    title: string;
    description: string | null;
    status: 'todo' | 'in_progress' | 'done';
    start_date: string | null;
    due_date: string | null;
    created_at: string;
    project?: Project;
}

export interface JournalLine {
    id: string;
    tenant_id: string;
    entry_id: string;
    account_code: string;
    account_name: string | null;
    debit: number;
    credit: number;
}

export interface JournalEntry {
    id: string;
    tenant_id: string;
    date: string;
    description: string;
    reference_id: string | null;
    created_at: string;
    lines: JournalLine[];
}

export interface FixedAsset {
    id: string;
    tenant_id: string;
    name: string;
    category: string | null;
    description: string | null;
    purchase_date: string;
    purchase_value: number;
    useful_life_years: number;
    residual_value: number;
    depreciation_method: string;
    status: string;
    account_code: string | null;
    reference_invoice: string | null;
    notes: string | null;
    created_at: string;
}

export interface QuoteLine {
    id?: string;
    product_id?: string | null;
    description: string;
    quantity: number;
    unit_price: number;
    tax_percentage: number;
    total_line?: number;
}

export interface Quote {
    id: string;
    client_id: string;
    quote_number: string | null;
    date: string;
    valid_until: string | null;
    amount_base: number;
    tax_amount: number;
    amount_total: number;
    status: string; // draft | sent | accepted | rejected
    notes: string | null;
    terms: string | null;
    opportunity_id: string | null;
    created_at: string;
    client?: Client;
    lines?: QuoteLine[];
}

export interface Activity {
    id: string;
    tenant_id: string;
    client_id: string | null;
    opportunity_id: string | null;
    type: string; // call | email | note | meeting_log
    description: string;
    metadata_json: Record<string, any>;
    created_at: string;
}

export interface EventItem {
    id: string;
    tenant_id: string;
    title: string;
    description: string | null;
    start_time: string;
    end_time: string;
    type: string;
    location_or_link: string | null;
    client_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface Reservation {
    id: string;
    tenant_id: string;
    client_id: string;
    resource_id: string | null;
    start_time: string;
    end_time: string;
    status: string;
    notes: string | null;
    created_at: string;
    updated_at: string;
}

export interface CompanySnapshot {
    month: string;
    generated_at: string;
    facturas: {
        ingresos_total: number;
        gastos_total: number;
        margen_bruto: number;
        margen_pct: number;
        facturas_emitidas: number;
        facturas_recibidas: number;
        facturas_pendientes_cobro: number;
        importe_pendiente_cobro: number;
    };
    banca: {
        total_ingresos: number;
        total_gastos: number;
        saldo_neto: number;
        transacciones: number;
        reconciliadas: number;
    };
    rrhh: {
        empleados_activos: number;
        coste_nominas: number;
        nominas_pagadas: number;
        nominas_pendientes: number;
    };
    clientes: {
        total_clientes: number;
        nuevos_periodo: number;
        top_client_name: string | null;
        top_client_amount: number;
    };
    resumen_ejecutivo: string;
}

export interface ReportDoc {
    id: string;
    file_name: string;
    file_size: number;
    category: string | null;
    created_at: string;
}


