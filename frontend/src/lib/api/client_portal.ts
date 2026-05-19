import { request } from "./client";

// ── EXCEPCIÓN a "todo via client.ts" ─────────────────────────────────────────
// El portal de clientes usa un JWT propio almacenado en `sessionStorage`
// bajo `PORTAL_TOKEN_KEY`, distinto del JWT del usuario empresa (que vive
// en `secureStore`). `client.ts.request()` adjuntaría el JWT empresa y
// rompería este flujo de auth alternativo (similar a `taskStream` y al
// QR-auth de `scanner.ts`). Por eso `portalRequest`, `authenticate` y
// `downloadInvoicePdf` se quedan con `fetch` directo.

export interface PortalTokenStatus {
    has_token: boolean;
    expires_at: string | null;
    created_at: string | null;
    last_used_at: string | null;
}

export interface PortalClientData {
    client: {
        id: string;
        name: string;
        email: string | null;
        nif: string | null;
        address: string | null;
        city: string | null;
    };
    invoices: {
        id: string;
        invoice_number: string | null;
        date: string | null;
        due_date: string | null;
        amount_total: number;
        status: string;
    }[];
    quotes: {
        id: string;
        quote_number: string | null;
        date: string | null;
        amount_total: number;
        status: string;
    }[];
}

// Admin API (uses normal JWT)
export const clientPortalAdmin = {
    getTokenStatus: (clientId: string) =>
        request<PortalTokenStatus>(`/api/v1/client-portal/admin/tokens/${clientId}`),
    generateToken: (clientId: string, daysValid = 90) =>
        request<{ raw_token: string; portal_url: string | null; expires_at: string; message: string }>(
            `/api/v1/client-portal/admin/tokens/${clientId}?days_valid=${daysValid}`,
            { method: "POST" }
        ),
    revokeToken: (clientId: string) =>
        request<void>(`/api/v1/client-portal/admin/tokens/${clientId}`, { method: "DELETE" }),
};

// Client-facing API (uses portal JWT stored in sessionStorage)
const PORTAL_TOKEN_KEY = "client_portal_token";

function getPortalJwt() {
    return typeof window !== "undefined" ? sessionStorage.getItem(PORTAL_TOKEN_KEY) : null;
}

async function portalRequest<T>(path: string, init?: RequestInit): Promise<T> {
    const jwt = getPortalJwt();
    const res = await fetch(path, {
        ...init,
        headers: {
            "Content-Type": "application/json",
            ...(jwt ? { Authorization: `Bearer ${jwt}` } : {}),
            ...init?.headers,
        },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Error");
    }
    if (res.status === 204) return undefined as T;
    return res.json();
}

export const clientPortal = {
    authenticate: async (rawToken: string): Promise<boolean> => {
        const res = await fetch("/api/v1/client-portal/auth", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: rawToken }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        if (data.access_token) {
            sessionStorage.setItem(PORTAL_TOKEN_KEY, data.access_token);
            return true;
        }
        return false;
    },
    me: () => portalRequest<PortalClientData>("/api/v1/client-portal/me"),
    downloadInvoicePdf: async (invoiceId: string, invoiceNumber: string | null) => {
        const jwt = getPortalJwt();
        const res = await fetch(`/api/v1/client-portal/invoices/${invoiceId}/pdf`, {
            headers: jwt ? { Authorization: `Bearer ${jwt}` } : {},
        });
        if (!res.ok) throw new Error("Error descargando PDF");
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `Factura_${invoiceNumber || invoiceId.slice(0, 8)}.pdf`;
        a.click();
        URL.revokeObjectURL(url);
    },
    logout: () => sessionStorage.removeItem(PORTAL_TOKEN_KEY),
    isAuthenticated: () => !!getPortalJwt(),
};
