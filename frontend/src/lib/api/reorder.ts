/**
 * Reposición automática: sugerencias de pedido y generación de pedidos de
 * compra borrador. Módulo independiente; usa el cliente compartido (client.ts).
 */
import { request } from "./client";

export interface ReorderSuggestion {
    product_id: string;
    name: string;
    sku: string | null;
    current_stock: number;
    reorder_point: number;
    suggested_qty: number;
    cost_price: number | null;
    tax_percentage: number;
    supplier_id: string | null;
    supplier_name: string | null;
}

export interface GeneratePosResult {
    created: {
        purchase_order_id: string;
        supplier_id: string;
        lines: number;
        amount_total: number;
    }[];
    skipped_no_supplier: string[];
}

export const reorder = {
    /** Productos en o por debajo de su punto de pedido, con cantidad sugerida. */
    suggestions: () => request<ReorderSuggestion[]>("/api/v1/inventory/reorder-suggestions"),

    /** Genera pedidos de compra borrador agrupados por proveedor. */
    generatePurchaseOrders: () =>
        request<GeneratePosResult>("/api/v1/inventory/reorder/generate-pos", { method: "POST" }),
};
