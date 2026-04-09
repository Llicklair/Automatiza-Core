import { http, HttpResponse } from "msw";

const BASE = "http://127.0.0.1:8080";

export const handlers = [
    // Auth
    http.post(`${BASE}/api/v1/auth/login`, async ({ request }) => {
        const body = (await request.json()) as Record<string, string>;
        if (body.email === "fail@test.com") {
            return HttpResponse.json(
                { detail: "Credenciales incorrectas" },
                { status: 401 },
            );
        }
        return HttpResponse.json({
            access_token: "test-access-token",
            refresh_token: "test-refresh-token",
        });
    }),

    http.post(`${BASE}/api/v1/auth/refresh`, () => {
        return HttpResponse.json({
            access_token: "refreshed-access-token",
            refresh_token: "refreshed-refresh-token",
        });
    }),

    // Tasks
    http.get(`${BASE}/api/v1/tasks`, () => {
        return HttpResponse.json([]);
    }),

    // Invoices
    http.get(`${BASE}/api/v1/invoices`, () => {
        return HttpResponse.json([]);
    }),

    // Health
    http.get(`${BASE}/api/v1/health`, () => {
        return HttpResponse.json({ status: "ok" });
    }),
];
