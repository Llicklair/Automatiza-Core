/**
 * Gestión de lotes de producto (caducidad / FEFO).
 *
 * Módulo independiente para no tocar el ya extenso erp.ts. Usa el cliente HTTP
 * compartido (JWT, refresh, errores) de client.ts.
 */
import { request } from "./client";

export interface ProductLot {
    id: string;
    product_id: string;
    lot_number: string;
    expiry_date: string | null;
    quantity: number;
    cost_price: number | null;
    received_at: string | null;
}

export interface ExpiringLot extends ProductLot {
    product_name: string;
    /** "warning" = caduca pronto · "error" = ya caducado. */
    severity: "warning" | "error";
    /** Días hasta caducar (negativo si ya caducó). */
    days_left: number;
}

export interface LotCreateInput {
    lot_number: string;
    quantity: number;
    expiry_date?: string | null;
    cost_price?: number | null;
}

export interface LotUpdateInput {
    lot_number?: string;
    expiry_date?: string | null;
    cost_price?: number | null;
}

export interface LotCreateResult {
    stock_after: number;
    lots: ProductLot[];
}

export const lots = {
    /** Lotes con stock de un producto, en orden FEFO (caduca antes → primero). */
    listForProduct: (productId: string) =>
        request<ProductLot[]>(`/api/v1/products/${productId}/lots`),

    /** Alta de lote (recepción): crea el lote, suma stock y registra movimiento. */
    create: (productId: string, data: LotCreateInput) =>
        request<LotCreateResult>(`/api/v1/products/${productId}/lots`, {
            method: "POST",
            body: JSON.stringify(data),
        }),

    /** Edita metadatos del lote (número, caducidad, coste). No cambia la cantidad. */
    update: (productId: string, lotId: string, data: LotUpdateInput) =>
        request<ProductLot>(`/api/v1/products/${productId}/lots/${lotId}`, {
            method: "PATCH",
            body: JSON.stringify(data),
        }),

    /** Lotes de todo el negocio que caducan dentro de `days` días (o ya caducados). */
    expiring: (days = 7) =>
        request<ExpiringLot[]>(`/api/v1/inventory/expiring-lots?days=${days}`),
};
