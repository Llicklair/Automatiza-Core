import { request, fetchText } from "./client";

export interface DeliveryNoteLine {
    id: string;
    product_id: string | null;
    description: string;
    quantity: number;
    unit_price: number;
    tax_percentage: number;
    total: number;
}

export interface DeliveryNote {
    id: string;
    tenant_id: string;
    client_id: string | null;
    albaran_number: string;
    date: string;
    status: "draft" | "confirmed" | "recibido" | "en_proceso" | "listo" | "delivered" | "anulado";
    /** T7: facturas enlazadas (vacío = sin facturar). */
    invoice_ids?: string[];
    client_name?: string | null;
    client_nif?: string | null;
    client_phone?: string | null;
    client_email?: string | null;
    notes: string | null;
    amount_base: number;
    tax_amount: number;
    amount_total: number;
    created_at: string | null;
    lines: DeliveryNoteLine[];
}

export interface DeliveryNoteCreate {
    client_id?: string;
    client_name?: string;
    date?: string;
    notes?: string;
    lines: { product_id?: string; description: string; quantity: number; unit_price: number; tax_percentage: number }[];
}

/** T8: edición. Campo ausente = no tocar; "" en notes/client_name = limpiar. */
export interface DeliveryNoteUpdate {
    client_id?: string;
    client_name?: string;
    date?: string;
    notes?: string;
    lines?: { product_id?: string; description: string; quantity: number; unit_price: number; tax_percentage: number }[];
}

export const albaranes = {
    list: () => request<DeliveryNote[]>("/api/v1/albaranes"),
    get: (id: string) => request<DeliveryNote>(`/api/v1/albaranes/${id}`),
    create: (data: DeliveryNoteCreate) => request<DeliveryNote>("/api/v1/albaranes", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: DeliveryNoteUpdate) => request<DeliveryNote>(`/api/v1/albaranes/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    updateStatus: (id: string, status: string) => request<DeliveryNote>(`/api/v1/albaranes/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) }),
    /** HTML del ticket-resguardo 80 mm (vertical tintorería). */
    ticketHtml: (id: string): Promise<string> => fetchText(`/api/v1/albaranes/${id}/ticket`),
    /** T7: factura agrupada — N albaranes del mismo cliente → 1 factura borrador. */
    facturar: (albaran_ids: string[]) =>
        request<{ id: string; invoice_number: string | null }>("/api/v1/albaranes/facturar", {
            method: "POST",
            body: JSON.stringify({ albaran_ids }),
        }),
    delete: (id: string) => request(`/api/v1/albaranes/${id}`, { method: "DELETE" }),
    pdfUrl: (id: string) => `/api/v1/albaranes/${id}/pdf`,
};
