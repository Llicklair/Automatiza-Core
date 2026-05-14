/**
 * SEC.JWT — Secure storage for JWT tokens.
 *
 * In Electron: tokens persist encrypted with safeStorage (DPAPI/Keychain/libsecret)
 * via IPC to the main process. Disk never sees them in plaintext.
 *
 * Fallback for dev/web (no Electron): localStorage — flagged with a console warning.
 *
 * API surface:
 *   - `hydrateSecureStore()` — async, call once at app boot to load cached tokens.
 *   - `getCachedToken(key)` — sync read from in-memory cache (used by `client.ts:getToken()`).
 *   - `setSecureToken(key, value)` — async write to cache + persistent store.
 *   - `removeSecureToken(key)` — async clear from cache + persistent store.
 *   - `clearAllSecureTokens()` — async, used on logout.
 */

type SecureKey = "access_token" | "refresh_token";

const SECURE_KEYS: readonly SecureKey[] = ["access_token", "refresh_token"];

interface ElectronSecureStoreAPI {
    get: (key: SecureKey) => Promise<string | null>;
    set: (key: SecureKey, value: string) => Promise<boolean>;
    remove: (key: SecureKey) => Promise<boolean>;
    isAvailable: () => Promise<boolean>;
}

function getElectronApi(): ElectronSecureStoreAPI | null {
    if (typeof window === "undefined") return null;
    const electronAPI = window.electronAPI;
    return (electronAPI?.secureStore as ElectronSecureStoreAPI | undefined) ?? null;
}

const _memoryCache: Partial<Record<SecureKey, string>> = {};
let _hydrated = false;
let _warnedFallback = false;

function warnFallbackOnce(): void {
    if (_warnedFallback) return;
    _warnedFallback = true;
    if (typeof console !== "undefined") {
        console.warn(
            "[secureStore] Electron safeStorage no disponible — usando localStorage como fallback. " +
                "Esto es esperado en dev/web. En la build empaquetada los tokens deben ir cifrados."
        );
    }
}

/**
 * Carga los tokens almacenados al boot del renderer.
 * Idempotente: llamar dos veces no re-cargar.
 */
export async function hydrateSecureStore(): Promise<void> {
    if (_hydrated) return;
    _hydrated = true;

    const api = getElectronApi();
    if (api) {
        for (const key of SECURE_KEYS) {
            const value = await api.get(key);
            if (value) _memoryCache[key] = value;
        }
        return;
    }

    // Fallback dev/web: localStorage
    warnFallbackOnce();
    if (typeof window === "undefined") return;
    for (const key of SECURE_KEYS) {
        const value = window.localStorage.getItem(key);
        if (value) _memoryCache[key] = value;
    }
}

/** Lee desde el cache sincrónico. Devuelve null si no hidratado o ausente. */
export function getCachedToken(key: SecureKey): string | null {
    return _memoryCache[key] ?? null;
}

/** Persiste y cachea un token. Async porque el IPC a Electron lo es. */
export async function setSecureToken(key: SecureKey, value: string): Promise<void> {
    _memoryCache[key] = value;

    const api = getElectronApi();
    if (api) {
        await api.set(key, value);
        return;
    }

    warnFallbackOnce();
    if (typeof window === "undefined") return;
    window.localStorage.setItem(key, value);
}

/** Elimina un token del cache y del store persistente. */
export async function removeSecureToken(key: SecureKey): Promise<void> {
    delete _memoryCache[key];

    const api = getElectronApi();
    if (api) {
        await api.remove(key);
        return;
    }

    warnFallbackOnce();
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(key);
}

/** Limpia todos los tokens — usado en logout. */
export async function clearAllSecureTokens(): Promise<void> {
    await Promise.all(SECURE_KEYS.map((k) => removeSecureToken(k)));
}
