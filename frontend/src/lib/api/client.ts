/**
 * Base HTTP client — shared by all domain modules.
 * Handles JWT auth, token refresh, and blob downloads.
 */
import { ApiError } from "./errors";
import { resolveApiBase } from "./base";
import {
    clearAllSecureTokens,
    getCachedToken,
    hydrateSecureStore,
    removeSecureToken,
    setSecureToken,
} from "../secureStore";

// Resolución en runtime (ver lib/api/base.ts): URL absoluta a :8080 en acceso
// directo (Electron/LAN), o base vacía (mismo origen) tras un proxy/túnel para
// acceso remoto. Nunca se hornea una URL en build que pueda quedar obsoleta.
export const BASE = resolveApiBase();

function parseDetail(raw: unknown): string {
    if (typeof raw === "string") return raw;
    if (Array.isArray(raw))
        return raw.map((e: { msg?: string }) => e.msg ?? JSON.stringify(e)).join("; ");
    return JSON.stringify(raw);
}

/**
 * SEC.JWT — `getToken()` se mantiene sincrónico leyendo del cache
 * in-memory de `secureStore`. La hidratación inicial corre al boot
 * (`hydrateSecureStore()` en el layout root).
 */
export function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return getCachedToken("access_token");
}

/** Persiste un par de tokens nuevos (access + refresh) tras login o refresh. */
export async function setTokens(accessToken: string, refreshToken: string): Promise<void> {
    await Promise.all([
        setSecureToken("access_token", accessToken),
        setSecureToken("refresh_token", refreshToken),
    ]);
    if (typeof document !== "undefined") {
        document.cookie = "auth_flag=1; path=/; SameSite=Lax";
    }
}

/** Borra todos los tokens — usado en logout y fallos de refresh. */
export async function clearTokens(): Promise<void> {
    await clearAllSecureTokens();
    if (typeof document !== "undefined") {
        document.cookie = "auth_flag=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    }
}

// Refresh single-flight: una página de datos (p.ej. el dashboard) dispara varias
// peticiones a la vez; si el access token expiró, todas reciben 401 al unísono.
// Sin deduplicar lanzarían N POST /refresh concurrentes (derroche y carreras).
// Compartimos una única promesa de refresh en vuelo; la siguiente expiración
// crea una nueva.
let _refreshInFlight: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
    if (_refreshInFlight) return _refreshInFlight;
    _refreshInFlight = (async () => {
        const refresh = getCachedToken("refresh_token");
        if (!refresh) return false;
        try {
            const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ refresh_token: refresh }),
            });
            if (!res.ok) return false;
            const data = await res.json();
            await setTokens(data.access_token, data.refresh_token);
            return true;
        } catch {
            return false;
        }
    })();
    try {
        return await _refreshInFlight;
    } finally {
        _refreshInFlight = null;
    }
}

/**
 * `fetch` que convierte fallos de red (TypeError "Failed to fetch", DNS,
 * CORS, offline) en un `ApiError` con status 0 y `errorType: "network_error"`.
 * Así toda la app puede manejar errores con `instanceof ApiError` sin que se
 * escape un `TypeError` crudo al boundary global.
 */
async function safeFetch(input: string, init?: RequestInit): Promise<Response> {
    try {
        return await fetch(input, init);
    } catch {
        throw new ApiError(
            0,
            "No se pudo conectar con el servidor. Comprueba tu conexión a internet.",
            undefined,
            "network_error",
        );
    }
}

export async function request<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    // Espera a que termine la hidratación de tokens antes de leer el access
    // token: evita que una petición disparada al montar una página corra con el
    // cache aún vacío (→ 401 → refresh sin token → rebote espurio a /login).
    // Es idempotente y comparte la promesa en vuelo, así que el coste es nulo.
    if (typeof window !== "undefined") await hydrateSecureStore();
    const token = getToken();
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(options.headers as Record<string, string>),
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await safeFetch(`${BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
        // Token expirado — intentar refresh
        const refreshed = await tryRefresh();
        if (refreshed) {
            headers["Authorization"] = `Bearer ${getToken()}`;
            const retry = await safeFetch(`${BASE}${path}`, { ...options, headers });
            if (retry.status === 401) {
                // El refresh "tuvo éxito" pero el nuevo token tampoco vale
                // (revocado, tenant deshabilitado): no dejar tokens muertos —
                // logout limpio, igual que en la rama de refresh fallido.
                await clearTokens();
                window.location.href = "/login";
                throw new ApiError(401, "Sesión expirada", undefined, "session_expired");
            }
            if (!retry.ok) {
                const err = await retry.json().catch(() => ({ detail: retry.statusText }));
                throw new ApiError(
                    retry.status,
                    parseDetail(err.detail ?? "Error desconocido"),
                    err.request_id,
                    err.type,
                );
            }
            return retry.json();
        }
        // Refresh falló → logout
        await clearTokens();
        window.location.href = "/login";
        throw new ApiError(401, "Sesión expirada", undefined, "session_expired");
    }

    if (res.status === 402) {
        window.dispatchEvent(new CustomEvent("license-required"));
        throw new ApiError(402, "Licencia requerida", undefined, "license_required");
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(
            res.status,
            parseDetail(err.detail ?? "Error desconocido"),
            err.request_id,
            err.type,
        );
    }

    if (res.status === 204) return undefined as T;
    return res.json();
}

export async function requestUpload<T>(path: string, formData: FormData): Promise<T> {
    let token = getToken();
    let res = await safeFetch(`${BASE}${path}`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
    });

    if (res.status === 401) {
        const refreshed = await tryRefresh();
        if (refreshed) {
            token = getToken();
            res = await safeFetch(`${BASE}${path}`, {
                method: "POST",
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                body: formData,
            });
        } else {
            await clearTokens();
            window.location.href = "/login";
            throw new ApiError(401, "Sesión expirada", undefined, "session_expired");
        }
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new ApiError(
            res.status,
            parseDetail(err.detail ?? "Error desconocido"),
            err.request_id,
            err.type,
        );
    }

    if (res.status === 204) return undefined as T;
    return res.json();
}

export async function fetchBlob(path: string, init?: RequestInit): Promise<Blob> {
    let token = getToken();
    const auth = (): Record<string, string> => token ? { Authorization: `Bearer ${token}` } : {};
    const headers = () => ({ ...(init?.headers as Record<string, string>), ...auth() });
    let res = await safeFetch(`${BASE}${path}`, { ...init, headers: headers() });
    if (res.status === 401) {
        const refreshed = await tryRefresh();
        if (refreshed) {
            token = getToken();
            res = await safeFetch(`${BASE}${path}`, { ...init, headers: headers() });
        }
    }
    if (!res.ok) {
        let detail = "Error al obtener el archivo";
        let errorType: string | undefined;
        let requestId: string | undefined;
        try { const err = await res.json(); detail = err.detail || detail; errorType = err.type; requestId = err.request_id; } catch { /* no json body */ }
        throw new ApiError(res.status, parseDetail(detail), requestId, errorType);
    }
    return res.blob();
}

export async function fetchText(path: string, init?: RequestInit): Promise<string> {
    let token = getToken();
    const auth = (): Record<string, string> => token ? { Authorization: `Bearer ${token}` } : {};
    const headers = () => ({ ...(init?.headers as Record<string, string>), ...auth() });
    let res = await safeFetch(`${BASE}${path}`, { ...init, headers: headers() });
    if (res.status === 401) {
        const refreshed = await tryRefresh();
        if (refreshed) {
            token = getToken();
            res = await safeFetch(`${BASE}${path}`, { ...init, headers: headers() });
        }
    }
    if (!res.ok) {
        let detail = "Error al obtener el contenido";
        let errorType: string | undefined;
        let requestId: string | undefined;
        try { const err = await res.json(); detail = err.detail || detail; errorType = err.type; requestId = err.request_id; } catch { /* no json body */ }
        throw new ApiError(res.status, parseDetail(detail), requestId, errorType);
    }
    return res.text();
}

export async function downloadBlob(path: string, filename: string): Promise<void> {
    let token = getToken();
    let res = await safeFetch(`${BASE}${path}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    // Si 401, intentar refresh y reintentar
    if (res.status === 401) {
        const refreshed = await tryRefresh();
        if (refreshed) {
            token = getToken();
            res = await safeFetch(`${BASE}${path}`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
        }
    }

    if (!res.ok) {
        let detail = "Error al descargar el archivo";
        let errorType: string | undefined;
        let requestId: string | undefined;
        try {
            const err = await res.json();
            detail = err.detail || detail;
            errorType = err.type;
            requestId = err.request_id;
        } catch { /* no json body */ }
        throw new ApiError(res.status, parseDetail(detail), requestId, errorType);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}
