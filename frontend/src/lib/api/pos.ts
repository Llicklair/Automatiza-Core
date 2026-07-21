/**
 * TPV (Punto de Venta) API.
 */
import { request, fetchText } from "./client";

export interface PosLine {
    id: string;
    session_id: string;
    product_id: string | null;
    description: string;
    quantity: number;
    unit_price: number;
    tax_percentage: number;
    total: number;
    created_at: string;
}

export interface PosSession {
    id: string;
    tenant_id: string;
    user_id: string;
    status: "open" | "closed" | "cancelled";
    payment_method: "cash" | "card" | null;
    amount_subtotal: number;
    tax_amount: number;
    amount_total: number;
    notes: string | null;
    opened_at: string;
    closed_at: string | null;
    lines: PosLine[];
}

export interface PosLineAdd {
    product_id?: string | null;
    description?: string;
    quantity?: number;
    unit_price?: number;
    tax_percentage?: number;
}

export interface PosCheckoutRequest {
    payment_method: "cash" | "card";
    notes?: string | null;
}

export interface VerifactuQr {
    huella: string;
    verify_url: string;
}

/** Factura simplificada (F2) emitida a partir de una sesión de TPV cerrada. */
export interface SimplifiedInvoice {
    id: string;
    invoice_number: string | null;
    invoice_type: string;
    status: string;
    amount_total: number;
    is_simplified: boolean;
    /** QR Verifactu ({huella, verify_url}) o null si el tenant no tiene Verifactu activo. */
    verifactu: VerifactuQr | null;
}

export const pos = {
    current: () => request<PosSession | null>("/api/v1/pos/sessions/current"),

    open: () =>
        request<PosSession>("/api/v1/pos/sessions", { method: "POST" }),

    list: (params?: { status?: string; only_mine?: boolean; limit?: number }) => {
        const filtered: Record<string, string> = {};
        if (params) {
            for (const [k, v] of Object.entries(params)) {
                if (v !== undefined && v !== null && v !== "") {
                    filtered[k] = String(v);
                }
            }
        }
        const qs = new URLSearchParams(filtered).toString();
        return request<PosSession[]>(`/api/v1/pos/sessions${qs ? "?" + qs : ""}`);
    },

    get: (sessionId: string) =>
        request<PosSession>(`/api/v1/pos/sessions/${sessionId}`),

    addLine: (sessionId: string, data: PosLineAdd) =>
        request<PosSession>(`/api/v1/pos/sessions/${sessionId}/lines`, {
            method: "POST",
            body: JSON.stringify(data),
        }),

    updateLine: (sessionId: string, lineId: string, quantity: number) =>
        request<PosSession>(
            `/api/v1/pos/sessions/${sessionId}/lines/${lineId}`,
            { method: "PATCH", body: JSON.stringify({ quantity }) },
        ),

    removeLine: (sessionId: string, lineId: string) =>
        request<PosSession>(
            `/api/v1/pos/sessions/${sessionId}/lines/${lineId}`,
            { method: "DELETE" },
        ),

    checkout: (sessionId: string, data: PosCheckoutRequest) =>
        request<PosSession>(`/api/v1/pos/sessions/${sessionId}/checkout`, {
            method: "POST",
            body: JSON.stringify(data),
        }),

    cancel: (sessionId: string) =>
        request<PosSession>(`/api/v1/pos/sessions/${sessionId}/cancel`, {
            method: "POST",
        }),

    emitirFactura: (sessionId: string) =>
        request<SimplifiedInvoice>(`/api/v1/pos/sessions/${sessionId}/factura`, {
            method: "POST",
        }),

    /** HTML del ticket (80 mm) listo para imprimir en térmica de TPV o impresora normal. */
    ticketHtml: (invoiceId: string): Promise<string> =>
        fetchText(`/api/v1/invoices/${invoiceId}/ticket`),
};
