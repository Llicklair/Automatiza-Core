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
    sku: string | null;
    barcode: string | null;
    name: string;
    description: string | null;
    price: number | null;
    stock_quantity: number;
    stock_min_alert: number | null;
    low_stock: boolean;
}

export interface StockMovementResult {
    product_id: string;
    sku: string | null;
    barcode: string | null;
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
    sku: string | null;
    barcode?: string | null;
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
//
// EXCEPCIÓN A "todo via client.ts": el mobile-scanner se autentica con un
// QR-token efímero pasado por URL, NO con el JWT de la sesión desktop.
// `client.ts.request()` adjuntaría el JWT del usuario y rompería esta API,
// que precisamente NO debe enviar credenciales de la sesión principal.
// Igual que `taskStream.ts`, esta usa un canal de auth alternativo y queda
// fuera del enrutado por `client.ts`.

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

    // `code` admite SKU o código de barras; el backend prueba barcode primero.
    // El body mantiene la clave `sku` por retrocompatibilidad con la API.
    scanProduct: (token: string, code: string) =>
        scannerFetch<ScannedProduct>("/scan-product", token, {
            method: "POST",
            body: JSON.stringify({ sku: code }),
        }),

    stockEntry: (token: string, code: string, quantity: number) =>
        scannerFetch<ScannerStockMutation>("/stock-entry", token, {
            method: "POST",
            body: JSON.stringify({ sku: code, quantity }),
        }),

    stockExit: (token: string, code: string, quantity: number) =>
        scannerFetch<ScannerStockMutation>("/stock-exit", token, {
            method: "POST",
            body: JSON.stringify({ sku: code, quantity }),
        }),

    confirmDelivery: (token: string, albaran_number: string) =>
        scannerFetch<ScannerDeliveryConfirm>("/confirm-delivery", token, {
            method: "POST",
            body: JSON.stringify({ albaran_number }),
        }),
};
