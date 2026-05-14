import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock fetch globally before importing the module
const fetchMock = vi.fn();
vi.stubGlobal("fetch", fetchMock);

// The module computes BASE from window.location in jsdom → http://localhost:8080
// We need to know the actual BASE the module will use
let clientModule: typeof import("../client");
let request: typeof import("../client").request;
let getToken: typeof import("../client").getToken;
let secureStoreModule: typeof import("../../secureStore");
let BASE: string;

// SEC.JWT — en jsdom (sin Electron), secureStore cae a localStorage fallback.
// Los tests setean tokens vía `localStorage.setItem` y después llaman
// `hydrateSecureStore()` para que el cache in-memory se sincronice.
async function setupTokens(access: string | null, refresh: string | null) {
    if (access) localStorage.setItem("access_token", access);
    if (refresh) localStorage.setItem("refresh_token", refresh);
    await secureStoreModule.hydrateSecureStore();
}

beforeEach(async () => {
    vi.resetModules();
    localStorage.clear();
    fetchMock.mockReset();
    secureStoreModule = await import("../../secureStore");
    clientModule = await import("../client");
    request = clientModule.request;
    getToken = clientModule.getToken;
    BASE = clientModule.BASE;
});

afterEach(() => {
    localStorage.clear();
});

describe("getToken", () => {
    it("returns null when no token is stored", () => {
        expect(getToken()).toBeNull();
    });

    it("returns the stored access token", async () => {
        await setupTokens("my-token", null);
        expect(getToken()).toBe("my-token");
    });
});

describe("request", () => {
    it("makes a fetch call with correct URL and Content-Type header", async () => {
        fetchMock.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ data: "test" }),
        });

        const result = await request("/api/v1/health");

        expect(fetchMock).toHaveBeenCalledTimes(1);
        const [url, options] = fetchMock.mock.calls[0];
        expect(url).toBe(`${BASE}/api/v1/health`);
        expect(options.headers["Content-Type"]).toBe("application/json");
        expect(result).toEqual({ data: "test" });
    });

    it("includes Authorization header when token exists", async () => {
        await setupTokens("bearer-token", null);

        fetchMock.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ ok: true }),
        });

        await request("/api/v1/tasks");

        const [, options] = fetchMock.mock.calls[0];
        expect(options.headers["Authorization"]).toBe("Bearer bearer-token");
    });

    it("does NOT include Authorization header without token", async () => {
        fetchMock.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () => Promise.resolve({}),
        });

        await request("/api/v1/health");

        const [, options] = fetchMock.mock.calls[0];
        expect(options.headers["Authorization"]).toBeUndefined();
    });

    it("returns undefined for 204 No Content responses", async () => {
        fetchMock.mockResolvedValueOnce({
            ok: true,
            status: 204,
            json: () => Promise.resolve(null),
        });

        const result = await request("/api/v1/something");
        expect(result).toBeUndefined();
    });

    it("throws with detail message on non-ok responses", async () => {
        fetchMock.mockResolvedValueOnce({
            ok: false,
            status: 422,
            statusText: "Unprocessable Entity",
            json: () => Promise.resolve({ detail: "Validation error" }),
        });

        await expect(request("/api/v1/bad")).rejects.toThrow("Validation error");
    });

    it("on 401, attempts token refresh then retries", async () => {
        await setupTokens("expired-token", "valid-refresh");

        // First call: 401
        fetchMock.mockResolvedValueOnce({
            ok: false,
            status: 401,
            json: () => Promise.resolve({ detail: "Unauthorized" }),
        });
        // Refresh call: success
        fetchMock.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () =>
                Promise.resolve({
                    access_token: "new-access",
                    refresh_token: "new-refresh",
                }),
        });
        // Retry call: success
        fetchMock.mockResolvedValueOnce({
            ok: true,
            status: 200,
            json: () => Promise.resolve({ retried: true }),
        });

        const result = await request("/api/v1/tasks");

        expect(result).toEqual({ retried: true });
        expect(fetchMock).toHaveBeenCalledTimes(3);
        expect(localStorage.getItem("access_token")).toBe("new-access");
    });

    it("on 401, if refresh fails, clears storage and redirects to /login", async () => {
        await setupTokens("expired", "bad-refresh");

        // Original call: 401
        fetchMock.mockResolvedValueOnce({
            ok: false,
            status: 401,
            json: () => Promise.resolve({ detail: "Unauthorized" }),
        });
        // Refresh call: fails
        fetchMock.mockResolvedValueOnce({
            ok: false,
            status: 401,
            json: () => Promise.resolve({ detail: "Invalid refresh" }),
        });

        // Mock window.location
        const originalLocation = window.location;
        Object.defineProperty(window, "location", {
            writable: true,
            value: { ...originalLocation, href: "" },
        });

        await expect(request("/api/v1/tasks")).rejects.toThrow(
            "Sesión expirada",
        );

        expect(localStorage.getItem("access_token")).toBeNull();
        expect(window.location.href).toBe("/login");

        // Restore
        Object.defineProperty(window, "location", {
            writable: true,
            value: originalLocation,
        });
    });

    it("on 401 with no refresh_token, redirects to /login immediately", async () => {
        await setupTokens("expired", null);
        // No refresh_token set

        fetchMock.mockResolvedValueOnce({
            ok: false,
            status: 401,
            json: () => Promise.resolve({ detail: "Unauthorized" }),
        });

        const originalLocation = window.location;
        Object.defineProperty(window, "location", {
            writable: true,
            value: { ...originalLocation, href: "" },
        });

        await expect(request("/api/v1/tasks")).rejects.toThrow(
            "Sesión expirada",
        );
        expect(window.location.href).toBe("/login");

        Object.defineProperty(window, "location", {
            writable: true,
            value: originalLocation,
        });
    });
});
