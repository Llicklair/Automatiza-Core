/**
 * QA.FRO — contract tests de los módulos lib/api/*.ts.
 *
 * Cada módulo de la capa API delega en `request()` del client base. Estos
 * tests blindan que el path, método y body que se envían al backend
 * coinciden con lo que el backend espera. Mock surgical de `request`
 * para no tocar fetch real.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// Mock global de `request` antes de importar cualquier módulo de API.
const requestMock = vi.fn();
vi.mock("../client", () => ({
    request: (...args: unknown[]) => requestMock(...args),
    // BASE y getToken también se importan; provee stubs.
    BASE: "http://localhost:8080",
    getToken: () => "fake-token",
}));

// IMPORTANT: imports después del mock.
import { auth } from "../auth";
import { autonomy } from "../autonomy";
import { onboarding } from "../onboarding";
import { regap } from "../regap";
import { notificationsApi } from "../notifications";
import { verifactuConfig } from "../verifactuConfig";
import { tasks, approvals } from "../tasks";
import { system } from "../system";
import { erp } from "../erp";

beforeEach(() => {
    requestMock.mockReset();
    requestMock.mockResolvedValue({});
});

afterEach(() => {
    requestMock.mockClear();
});

function lastCall() {
    return requestMock.mock.calls[requestMock.mock.calls.length - 1];
}

function lastUrl() {
    return lastCall()[0] as string;
}

function lastInit() {
    return (lastCall()[1] as RequestInit | undefined) ?? {};
}

function lastBody() {
    const body = lastInit().body;
    return body ? JSON.parse(body as string) : null;
}

// ────────────────────────────────────────────────────────────────────────
// auth
// ────────────────────────────────────────────────────────────────────────

describe("api.auth", () => {
    it("login envía email y password a /auth/login", async () => {
        await auth.login("a@b.com", "secret");
        expect(lastUrl()).toBe("/api/v1/auth/login");
        expect(lastInit().method).toBe("POST");
        expect(lastBody()).toEqual({ email: "a@b.com", password: "secret" });
    });

    it("register envía datos completos", async () => {
        await auth.register({
            email: "a@b.com",
            password: "s",
            full_name: "Ana",
            tenant: { name: "Acme", nif: "B12345678" },
        });
        expect(lastUrl()).toBe("/api/v1/auth/register");
        expect(lastInit().method).toBe("POST");
        const body = lastBody();
        expect(body.email).toBe("a@b.com");
        expect(body.tenant.nif).toBe("B12345678");
    });

    it("forgotPassword envía email", async () => {
        await auth.forgotPassword("a@b.com");
        expect(lastUrl()).toBe("/api/v1/auth/forgot-password");
        expect(lastBody()).toEqual({ email: "a@b.com" });
    });

    it("resetPassword envía token y new_password", async () => {
        await auth.resetPassword("tk", "newpass");
        expect(lastUrl()).toBe("/api/v1/auth/reset-password");
        expect(lastBody()).toEqual({ token: "tk", new_password: "newpass" });
    });

    it("me usa GET implícito", async () => {
        await auth.me();
        expect(lastUrl()).toBe("/api/v1/auth/me");
        // request sin segundo argumento → GET default
        expect(lastInit().method).toBeUndefined();
    });
});

// ────────────────────────────────────────────────────────────────────────
// autonomy
// ────────────────────────────────────────────────────────────────────────

describe("api.autonomy", () => {
    it("list usa GET /autonomy", async () => {
        await autonomy.list();
        expect(lastUrl()).toBe("/api/v1/autonomy");
        expect(lastInit().method).toBeUndefined();
    });

    it("set hace PUT al dominio con mode", async () => {
        await autonomy.set("banking_write", "AUTO");
        expect(lastUrl()).toBe("/api/v1/autonomy/banking_write");
        expect(lastInit().method).toBe("PUT");
        expect(lastBody()).toEqual({ mode: "AUTO" });
    });

    it("set url-encodea el domain", async () => {
        await autonomy.set("a/b" as any, "AUTO");
        expect(lastUrl()).toBe("/api/v1/autonomy/a%2Fb");
    });

    it("reset hace DELETE al dominio", async () => {
        await autonomy.reset("crm");
        expect(lastUrl()).toBe("/api/v1/autonomy/crm");
        expect(lastInit().method).toBe("DELETE");
    });
});

// ────────────────────────────────────────────────────────────────────────
// onboarding (wizard + simulación 303)
// ────────────────────────────────────────────────────────────────────────

describe("api.onboarding", () => {
    it("get pide /onboarding/wizard", async () => {
        await onboarding.get();
        expect(lastUrl()).toBe("/api/v1/onboarding/wizard");
    });

    it("setStep hace PATCH con step y value", async () => {
        await onboarding.setStep("company", true);
        expect(lastUrl()).toBe("/api/v1/onboarding/wizard");
        expect(lastInit().method).toBe("PATCH");
        expect(lastBody()).toEqual({ step: "company", value: true });
    });

    it("skip hace POST a /skip", async () => {
        await onboarding.skip();
        expect(lastUrl()).toBe("/api/v1/onboarding/wizard/skip");
        expect(lastInit().method).toBe("POST");
    });

    it("reset hace POST a /reset", async () => {
        await onboarding.reset();
        expect(lastUrl()).toBe("/api/v1/onboarding/wizard/reset");
        expect(lastInit().method).toBe("POST");
    });

    it("simulate303 inyecta quarter y year en query", async () => {
        await onboarding.simulate303(2, 2025);
        expect(lastUrl()).toBe("/api/v1/onboarding/wizard/simulate/303?quarter=2&year=2025");
    });

    it("simulate303 usa defaults Q1 2026", async () => {
        await onboarding.simulate303();
        expect(lastUrl()).toBe("/api/v1/onboarding/wizard/simulate/303?quarter=1&year=2026");
    });
});

// ────────────────────────────────────────────────────────────────────────
// regap
// ────────────────────────────────────────────────────────────────────────

describe("api.regap", () => {
    it("get usa /onboarding/regap", async () => {
        await regap.get();
        expect(lastUrl()).toBe("/api/v1/onboarding/regap");
    });

    it("start envía auth_method", async () => {
        await regap.start("cert_fnmt");
        expect(lastUrl()).toBe("/api/v1/onboarding/regap/start");
        expect(lastInit().method).toBe("POST");
        expect(lastBody()).toEqual({ auth_method: "cert_fnmt" });
    });

    it("grant hace POST sin body", async () => {
        await regap.grant();
        expect(lastUrl()).toBe("/api/v1/onboarding/regap/grant");
        expect(lastInit().method).toBe("POST");
    });

    it("verify envía nif_cliente", async () => {
        await regap.verify("B12345678");
        expect(lastUrl()).toBe("/api/v1/onboarding/regap/verify");
        expect(lastBody()).toEqual({ nif_cliente: "B12345678" });
    });

    it("reset hace POST a /reset", async () => {
        await regap.reset();
        expect(lastUrl()).toBe("/api/v1/onboarding/regap/reset");
        expect(lastInit().method).toBe("POST");
    });
});

// ────────────────────────────────────────────────────────────────────────
// notifications
// ────────────────────────────────────────────────────────────────────────

describe("api.notifications", () => {
    it("list pasa flags only_unread y limit en query", async () => {
        await notificationsApi.list(true, 25);
        expect(lastUrl()).toBe("/api/v1/notifications?only_unread=true&limit=25");
    });

    it("list usa defaults false,50", async () => {
        await notificationsApi.list();
        expect(lastUrl()).toBe("/api/v1/notifications?only_unread=false&limit=50");
    });

    it("markRead hace PATCH /{id}/read", async () => {
        await notificationsApi.markRead("abc-123");
        expect(lastUrl()).toBe("/api/v1/notifications/abc-123/read");
        expect(lastInit().method).toBe("PATCH");
    });

    it("markAllRead hace POST", async () => {
        await notificationsApi.markAllRead();
        expect(lastUrl()).toBe("/api/v1/notifications/mark-all-read");
        expect(lastInit().method).toBe("POST");
    });
});

// ────────────────────────────────────────────────────────────────────────
// verifactuConfig
// ────────────────────────────────────────────────────────────────────────

describe("api.verifactuConfig", () => {
    it("get usa /verifactu/config", async () => {
        await verifactuConfig.get();
        expect(lastUrl()).toBe("/api/v1/verifactu/config");
    });

    it("set hace PUT con mode", async () => {
        await verifactuConfig.set("voluntary");
        expect(lastUrl()).toBe("/api/v1/verifactu/config");
        expect(lastInit().method).toBe("PUT");
        expect(lastBody()).toEqual({ mode: "voluntary" });
    });

    it("set acepta no_remission", async () => {
        await verifactuConfig.set("no_remission");
        expect(lastBody()).toEqual({ mode: "no_remission" });
    });
});

// ────────────────────────────────────────────────────────────────────────
// tasks
// ────────────────────────────────────────────────────────────────────────

describe("api.tasks", () => {
    it("list sin params usa GET /tasks", async () => {
        await tasks.list();
        expect(lastUrl()).toBe("/api/v1/tasks");
    });

    it("list con status y limit pasa query string", async () => {
        await tasks.list({ status: "executing", limit: 10 });
        expect(lastUrl()).toBe("/api/v1/tasks?status=executing&limit=10");
    });

    it("create envía domain y user_intent", async () => {
        await tasks.create("chat", "hola");
        expect(lastUrl()).toBe("/api/v1/tasks");
        expect(lastInit().method).toBe("POST");
        expect(lastBody()).toEqual({ domain: "chat", user_intent: "hola" });
    });

    it("create incluye additional_metadata cuando se pasa", async () => {
        await tasks.create("chat", "x", { source: "web" });
        const body = lastBody();
        expect(body.additional_metadata).toEqual({ source: "web" });
    });

    it("create omite additional_metadata si no se pasa", async () => {
        await tasks.create("chat", "x");
        const body = lastBody();
        expect("additional_metadata" in body).toBe(false);
    });

    it("create incluye parent_task_id cuando se pasa", async () => {
        await tasks.create("chat", "x", undefined, "parent-1");
        expect(lastBody()).toMatchObject({ parent_task_id: "parent-1" });
    });

    it("get pide /tasks/{id}", async () => {
        await tasks.get("t-1");
        expect(lastUrl()).toBe("/api/v1/tasks/t-1");
    });

    it("cancel hace DELETE", async () => {
        await tasks.cancel("t-1");
        expect(lastUrl()).toBe("/api/v1/tasks/t-1");
        expect(lastInit().method).toBe("DELETE");
    });

    it("audit pide /tasks/{id}/audit", async () => {
        await tasks.audit("t-1");
        expect(lastUrl()).toBe("/api/v1/tasks/t-1/audit");
    });

    it("cleanup hace DELETE /tasks/cleanup", async () => {
        await tasks.cleanup();
        expect(lastUrl()).toBe("/api/v1/tasks/cleanup");
        expect(lastInit().method).toBe("DELETE");
    });
});

// ────────────────────────────────────────────────────────────────────────
// approvals
// ────────────────────────────────────────────────────────────────────────

describe("api.approvals", () => {
    it("list pide /approvals", async () => {
        await approvals.list();
        expect(lastUrl()).toBe("/api/v1/approvals");
    });

    it("decide hace POST con approved y rejection_reason", async () => {
        await approvals.decide("a-1", false, "Datos incompletos");
        expect(lastUrl()).toBe("/api/v1/approvals/a-1/decide");
        expect(lastInit().method).toBe("POST");
        expect(lastBody()).toEqual({
            approved: false,
            rejection_reason: "Datos incompletos",
        });
    });

    it("decide approved=true sin razón", async () => {
        await approvals.decide("a-1", true);
        const body = lastBody();
        expect(body.approved).toBe(true);
        expect(body.rejection_reason).toBeUndefined();
    });

    it("cleanup hace DELETE", async () => {
        await approvals.cleanup();
        expect(lastUrl()).toBe("/api/v1/approvals/cleanup");
        expect(lastInit().method).toBe("DELETE");
    });
});

// ────────────────────────────────────────────────────────────────────────
// system (backups + health no testeado por usar fetch directo)
// ────────────────────────────────────────────────────────────────────────

describe("api.system", () => {
    it("listBackups pide /system/backups", async () => {
        await system.listBackups();
        expect(lastUrl()).toBe("/api/v1/system/backups");
    });

    it("runBackup hace POST", async () => {
        await system.runBackup();
        expect(lastUrl()).toBe("/api/v1/system/backups");
        expect(lastInit().method).toBe("POST");
    });

    it("restoreBackup url-encodea el filename", async () => {
        await system.restoreBackup("backup 2026-05-15.dump");
        expect(lastUrl()).toBe(
            "/api/v1/system/backups/backup%202026-05-15.dump/restore",
        );
        expect(lastInit().method).toBe("POST");
    });

    it("deleteBackup hace DELETE con filename encoded", async () => {
        await system.deleteBackup("file with spaces.dump");
        expect(lastUrl()).toBe(
            "/api/v1/system/backups/file%20with%20spaces.dump",
        );
        expect(lastInit().method).toBe("DELETE");
    });
});

// ────────────────────────────────────────────────────────────────────────
// erp.clients
// ────────────────────────────────────────────────────────────────────────

describe("api.erp.clients", () => {
    it("list pide /clients", async () => {
        await erp.clients.list();
        expect(lastUrl()).toBe("/api/v1/clients");
    });

    it("create envía body con datos", async () => {
        await erp.clients.create({ name: "Acme", nif: "B12345678" } as any);
        expect(lastUrl()).toBe("/api/v1/clients");
        expect(lastInit().method).toBe("POST");
        expect(lastBody().name).toBe("Acme");
    });

    it("update hace PATCH al cliente", async () => {
        await erp.clients.update("c-1", { name: "Acme 2" } as any);
        expect(lastUrl()).toBe("/api/v1/clients/c-1");
        expect(lastInit().method).toBe("PATCH");
        expect(lastBody()).toEqual({ name: "Acme 2" });
    });

    it("delete hace DELETE", async () => {
        await erp.clients.delete("c-1");
        expect(lastUrl()).toBe("/api/v1/clients/c-1");
        expect(lastInit().method).toBe("DELETE");
    });
});

// ────────────────────────────────────────────────────────────────────────
// erp.products
// ────────────────────────────────────────────────────────────────────────

describe("api.erp.products", () => {
    it("list pide /products", async () => {
        await erp.products.list();
        expect(lastUrl()).toBe("/api/v1/products");
    });

    it("create envía datos", async () => {
        await erp.products.create({ name: "Producto X", price: 10 } as any);
        expect(lastUrl()).toBe("/api/v1/products");
        expect(lastInit().method).toBe("POST");
    });

    it("update hace PATCH", async () => {
        await erp.products.update("p-1", { price: 15 } as any);
        expect(lastUrl()).toBe("/api/v1/products/p-1");
        expect(lastInit().method).toBe("PATCH");
    });

    it("delete hace DELETE", async () => {
        await erp.products.delete("p-1");
        expect(lastUrl()).toBe("/api/v1/products/p-1");
        expect(lastInit().method).toBe("DELETE");
    });
});

// ────────────────────────────────────────────────────────────────────────
// erp.invoices
// ────────────────────────────────────────────────────────────────────────

describe("api.erp.invoices", () => {
    it("list pide /invoices", async () => {
        await erp.invoices.list();
        expect(lastUrl()).toBe("/api/v1/invoices");
    });

    it("get pide /invoices/{id}", async () => {
        await erp.invoices.get("i-1");
        expect(lastUrl()).toBe("/api/v1/invoices/i-1");
    });

    it("updateStatus hace PATCH al endpoint /status", async () => {
        await erp.invoices.updateStatus("i-1", "paid");
        expect(lastUrl()).toBe("/api/v1/invoices/i-1/status");
        expect(lastInit().method).toBe("PATCH");
        expect(lastBody()).toEqual({ status: "paid" });
    });

    it("delete hace DELETE", async () => {
        await erp.invoices.delete("i-1");
        expect(lastUrl()).toBe("/api/v1/invoices/i-1");
        expect(lastInit().method).toBe("DELETE");
    });

    it("sendVerifactu hace POST a /verifactu-send", async () => {
        await erp.invoices.sendVerifactu("i-1");
        expect(lastUrl()).toBe("/api/v1/invoices/i-1/verifactu-send");
        expect(lastInit().method).toBe("POST");
    });
});

// ────────────────────────────────────────────────────────────────────────
// Robustez transversal
// ────────────────────────────────────────────────────────────────────────

describe("contrato común", () => {
    it("todas las llamadas devuelven la promesa del mock sin transformarla", async () => {
        const payload = { foo: "bar" };
        requestMock.mockResolvedValueOnce(payload);
        const res = await auth.me();
        expect(res).toEqual(payload);
    });

    it("propaga el error del mock al caller", async () => {
        requestMock.mockRejectedValueOnce(new Error("backend down"));
        await expect(auth.me()).rejects.toThrow("backend down");
    });
});
