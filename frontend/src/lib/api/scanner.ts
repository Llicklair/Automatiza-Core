/**
 * Scanner API.
 *
 * Two flows live here:
 *   1) Desktop generates a QR token via the standard JWT-authenticated client
 *      (`scanner.generateQR()`).
 *   2) Mobile-scanner page consumes that token from the URL and uses it as a
 *      Bearer auth (no JWT). Those calls go through `scannerFetch` and are
 *      exposed on the `mobileScanner` object — they take the QR token as
 *      explicit first argument.
 */
import { BASE, request } from "./client";

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

export interface ScannerWhoami {
    tenant_id: string;
    device: string;
}

export interface ScannerStockMutation {
    sku: string;
    stock_after: number;
    low_stock: boolean;
}

export interface ScannerDeliveryConfirm {
    albaran_number: string;
    status: string;
}

export const scanner = {
    generateQR: (deviceName = "Scanner móvil") =>
        request<ScannerToken>("/api/v1/scanner/generate-qr", {
            method: "POST",
            body: JSON.stringify({ device_name: deviceName }),
        }),
};

// ── Mobile-scanner flow (QR-token auth) ───────────────────────────────────────

async function scannerFetch<T>(path: string, token: string, opts: RequestInit = {}): Promise<T> {
    const res = await fetch(`${BASE}/api/v1/scanner${path}`, {
        ...opts,
        headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
            ...(opts.headers || {}),
        },
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || res.statusText);
    }
    return res.json();
}

export const mobileScanner = {
    whoami: (token: string) =>
        scannerFetch<ScannerWhoami>("/whoami", token),

    scanProduct: (token: string, sku: string) =>
        scannerFetch<ScannedProduct>("/scan-product", token, {
            method: "POST",
            body: JSON.stringify({ sku }),
        }),

    stockEntry: (token: string, sku: string, quantity: number) =>
        scannerFetch<ScannerStockMutation>("/stock-entry", token, {
            method: "POST",
            body: JSON.stringify({ sku, quantity }),
        }),

    stockExit: (token: string, sku: string, quantity: number) =>
        scannerFetch<ScannerStockMutation>("/stock-exit", token, {
            method: "POST",
            body: JSON.stringify({ sku, quantity }),
        }),

    confirmDelivery: (token: string, albaran_number: string) =>
        scannerFetch<ScannerDeliveryConfirm>("/confirm-delivery", token, {
            method: "POST",
            body: JSON.stringify({ albaran_number }),
        }),
};
