/**
 * Base HTTP client — shared by all domain modules.
 * Handles JWT auth, token refresh, and blob downloads.
 */

export const BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8080`
    : "http://127.0.0.1:8080");

export function getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
}

async function tryRefresh(): Promise<boolean> {
    const refresh = localStorage.getItem("refresh_token");
    if (!refresh) return false;
    try {
        const res = await fetch(`${BASE}/api/v1/auth/refresh`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return false;
        const data = await res.json();
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        document.cookie = "auth_flag=1; path=/; SameSite=Lax";
        return true;
    } catch {
        return false;
    }
}

export async function request<T>(
    path: string,
    options: RequestInit = {}
): Promise<T> {
    const token = getToken();
    const headers: Record<string, string> = {
        "Content-Type": "application/json",
        ...(options.headers as Record<string, string>),
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${BASE}${path}`, { ...options, headers });

    if (res.status === 401) {
        // Token expirado — intentar refresh
        const refreshed = await tryRefresh();
        if (refreshed) {
            headers["Authorization"] = `Bearer ${getToken()}`;
            const retry = await fetch(`${BASE}${path}`, { ...options, headers });
            if (!retry.ok) throw new Error(await retry.text());
            return retry.json();
        }
        // Refresh falló → logout
        localStorage.clear();
        document.cookie = "auth_flag=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        window.location.href = "/login";
        throw new Error("Sesión expirada");
    }

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? "Error desconocido");
    }

    if (res.status === 204) return undefined as T;
    return res.json();
}

export async function downloadBlob(path: string, filename: string): Promise<void> {
    let token = getToken();
    let res = await fetch(`${BASE}${path}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });

    // Si 401, intentar refresh y reintentar
    if (res.status === 401) {
        const refreshed = await tryRefresh();
        if (refreshed) {
            token = getToken();
            res = await fetch(`${BASE}${path}`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
        }
    }

    if (!res.ok) {
        let detail = "Error al descargar el archivo";
        try {
            const err = await res.json();
            detail = err.detail || detail;
        } catch { /* no json body */ }
        throw new Error(detail);
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
