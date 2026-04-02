import { request } from "./client";

export interface ScannerToken {
    token: string;
    expires_at: string;
    scope: string;
}

export interface ScannedProduct {
    id: string;
    sku: string;
    name: string;
    description: string | null;
    price: number | null;
    stock_quantity: number;
    stock_min_alert: number | null;
    low_stock: boolean;
}

export interface StockMovementResult {
    product_id: string;
    sku: string;
    name: string;
    movement_type: string;
    quantity: number;
    stock_before: number;
    stock_after: number;
    low_stock: boolean;
}

export const scanner = {
    generateQR: (deviceName = "Scanner móvil") =>
        request<ScannerToken>("/scanner/generate-qr", {
            method: "POST",
            body: JSON.stringify({ device_name: deviceName }),
        }),
};
