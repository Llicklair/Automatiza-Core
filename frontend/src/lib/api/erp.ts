import { request, downloadBlob, requestUpload } from "./client";

export interface ScannedInvoiceLine {
    description: string;
    quantity: number;
    unit_price: number;
    tax_percentage: number;
    total: number;
}

export interface ScannedInvoice {
    emisor: {
        nif: string;
        name: string;
        address: string | null;
        city: string | null;
        postal_code: string | null;
    };
    invoice_number: string;
    issue_date: string;
    due_date: string | null;
    lines: ScannedInvoiceLine[];
    amount_base: number;
    tax_amount: number;
    amount_total: number;
    currency: string;
    payment_method: string | null;
    iban: string | null;
    confidence: number;
    warnings: string[];
}

export interface Client {
    id: string;
    nif: string | null;
    name: string;
    email: string | null;
    phone: string | null;
    address: string | null;
    city: string | null;
    postal_code: string | null;
    client_type: string;
    created_at: string;
    updated_at: string | null;
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
    verifactu_status: string | null;
    verifactu_sent_at: string | null;
    created_at: string;
    updated_at: string | null;
    client?: Client;
    lines?: InvoiceLine[];
}

export interface Product {
    id: string;
    tenant_id: string;
    item_type: string;
    sku: string | null;
    barcode: string | null;
    name: string;
    description: string | null;
    category: string | null;
    location: string | null;
    unit: string;
    price: number;
    cost_price: number | null;
    tax_percentage: number;
    stock_quantity: number;
    stock_min_alert: number;
    is_active: boolean;
    created_at: string;
    updated_at: string | null;
}

export interface StockMovement {
    id: string;
    tenant_id: string;
    product_id: string;
    user_id: string | null;
    movement_type: string;
    quantity: number;
    stock_after: number;
    unit_cost: number | null;
    reference: string | null;
    notes: string | null;
    created_at: string;
}

export interface StockValuationByCategory {
    category: string | null;
    units: number;
    value: number;
    product_count: number;
}

export interface StockValuation {
    total_value: number;
    total_units: number;
    product_count: number;
    missing_cost_price_count: number;
    by_category: StockValuationByCategory[];
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

export const erp = {
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
        list: (params?: {
            skip?: number;
            limit?: number;
            q?: string;
            category?: string;
            is_active?: boolean;
            status?: "ok" | "low_stock" | "out_of_stock";
        }) => {
            const filtered: Record<string, string> = {};
            if (params) {
                for (const [k, v] of Object.entries(params)) {
                    if (v !== undefined && v !== null && v !== "") {
                        filtered[k] = String(v);
                    }
                }
            }
            const qs = new URLSearchParams(filtered).toString();
            return request<Product[]>(`/api/v1/products${qs ? "?" + qs : ""}`);
        },
        byBarcode: (code: string) =>
            request<Product>(`/api/v1/products/by-barcode/${encodeURIComponent(code)}`),
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
        scan: (file: File) => {
            const fd = new FormData();
            fd.append("file", file);
            return requestUpload<ScannedInvoice>("/api/v1/invoices/scan", fd);
        },
        /** Aprendizaje OCR (F2.5): el usuario corrigió una extracción → guardar
         * overrides para que las próximas facturas del mismo NIF salgan
         * mejor sin coste extra de LLM. */
        learnScanCorrection: (params: {
            supplier_nif: string;
            original: ScannedInvoice;
            corrected: ScannedInvoice;
        }) =>
            request<{ saved: boolean; overrides: Record<string, unknown> }>(
                "/api/v1/invoices/scan/learn",
                { method: "POST", body: JSON.stringify(params) },
            ),
        downloadPdf: (id: string, invoiceNumber: string | null) =>
            downloadBlob(`/api/v1/invoices/${id}/pdf`, `Factura_${invoiceNumber || id.slice(0, 8)}.pdf`),
        downloadFacturae: (id: string, invoiceNumber: string | null) =>
            downloadBlob(`/api/v1/invoices/${id}/facturae`, `facturae_${(invoiceNumber || id.slice(0, 8)).replace(/\//g, "-")}.xsig`),
        sendVerifactu: (id: string) =>
            request<{ message: string; invoice_id: string; status: string }>(`/api/v1/invoices/${id}/verifactu-send`, { method: "POST" }),
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
        valuation: () => request<StockValuation>("/api/v1/stock/valuation"),
        movements: (productId: string) => request<StockMovement[]>(`/api/v1/products/${productId}/stock-movements`),
        addMovement: (productId: string, data: Partial<StockMovement>) =>
            request<StockMovement>(`/api/v1/products/${productId}/stock-movements`, {
                method: "POST",
                body: JSON.stringify(data),
            }),
    },
};
