import { request } from "./client";

export const auth = {
    login: (email: string, password: string) =>
        request<{ access_token: string; refresh_token: string; token_type: string }>(
            "/api/v1/auth/login",
            { method: "POST", body: JSON.stringify({ email, password }) }
        ),
    register: (data: {
        email: string;
        password: string;
        full_name?: string;
        tenant: { name: string; nif: string };
    }) =>
        request("/api/v1/auth/register", {
            method: "POST",
            body: JSON.stringify(data),
        }),
    forgotPassword: (email: string) =>
        request("/api/v1/auth/forgot-password", {
            method: "POST",
            body: JSON.stringify({ email }),
        }),
    resetPassword: (token: string, new_password: string) =>
        request("/api/v1/auth/reset-password", {
            method: "POST",
            body: JSON.stringify({ token, new_password }),
        }),
    me: () => request<{ full_name: string; email: string }>("/api/v1/auth/me"),
};
