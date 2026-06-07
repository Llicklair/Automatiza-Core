/**
 * Almacenes / tiendas y stock por almacén (multi-almacén).
 * Módulo independiente; usa el cliente HTTP compartido (client.ts).
 */
import { request } from "./client";

export interface Warehouse {
    id: string;
    name: string;
    code: string | null;
    address: string | null;
    is_default: boolean;
    is_active: boolean;
}

export interface WarehouseStock {
    warehouse_id: string;
    warehouse_name: string;
    is_default: boolean;
    quantity: number;
}

export interface WarehouseInput {
    name: string;
    code?: string | null;
    address?: string | null;
    is_default?: boolean;
    is_active?: boolean;
}

export interface TransferInput {
    product_id: string;
    from_warehouse_id: string;
    to_warehouse_id: string;
    quantity: number;
}

export const warehouses = {
    list: () => request<Warehouse[]>("/api/v1/warehouses"),

    create: (data: WarehouseInput) =>
        request<Warehouse>("/api/v1/warehouses", {
            method: "POST",
            body: JSON.stringify(data),
        }),

    update: (id: string, data: Partial<WarehouseInput>) =>
        request<Warehouse>(`/api/v1/warehouses/${id}`, {
            method: "PATCH",
            body: JSON.stringify(data),
        }),

    /** Desglose de stock de un producto por almacén (el por defecto se deriva). */
    stockByProduct: (productId: string) =>
        request<WarehouseStock[]>(`/api/v1/products/${productId}/stock-by-warehouse`),

    /** Transfiere stock (y lotes FEFO) entre dos almacenes. */
    transfer: (data: TransferInput) =>
        request<{ quantity: number; moved_lots: { lot_number: string; quantity: number }[] }>(
            "/api/v1/inventory/transfer",
            { method: "POST", body: JSON.stringify(data) },
        ),
};
