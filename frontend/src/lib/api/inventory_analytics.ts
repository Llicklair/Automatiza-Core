/** Analítica de inventario (valoración, stock muerto, más vendidos). */
import { request } from "./client";

export interface InvValuation {
    value_cost: number;
    value_retail: number;
    potential_margin: number;
    units: number;
    product_count: number;
}

export interface DeadStockItem {
    product_id: string;
    name: string;
    sku: string | null;
    stock: number;
    last_sale: string | null;
    days_since_sale: number | null;
    value_cost: number;
}

export interface TopMover {
    product_id: string;
    name: string;
    sku: string | null;
    sold: number;
}

export type BajaReason = "rotura" | "merma" | "robo" | "caducado";

export interface BajaByReason {
    reason: BajaReason;
    units: number;
    value_eur: number;
}

export interface BajaTopProduct {
    product_id: string;
    name: string;
    units: number;
    value_eur: number;
}

export interface InvBajas {
    period_days: number;
    total_units: number;
    total_value_eur: number;
    by_reason: BajaByReason[];
    top_products: BajaTopProduct[];
}

export interface InvBelowMin {
    count: number;
    value_eur: number;
}

export interface InventoryAnalytics {
    valuation: InvValuation;
    dead_days: number;
    top_days: number;
    dead_count: number;
    dead_value_cost: number;
    dead_stock: DeadStockItem[];
    top_movers: TopMover[];
    merma_days: number;
    bajas: InvBajas;
    box_bajas_units: number;
    below_min: InvBelowMin;
}

export const inventoryAnalytics = {
    overview: (deadDays = 90, topDays = 30) =>
        request<InventoryAnalytics>(
            `/api/v1/inventory/analytics?dead_days=${deadDays}&top_days=${topDays}`,
        ),
};
