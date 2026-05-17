import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E config (QA.E2E).
 *
 * Por defecto arranca el dev server de Next con `npm run dev` y espera al
 * puerto 3000. En CI nunca reusa servidor existente; en local sí, para
 * iterar rápido sin reiniciar Next cada vez.
 *
 * Para tests que tocan el backend FastAPI (login, factura, Verifactu) el
 * backend debe estar corriendo aparte en :8000 (ver `frontend/e2e/README.md`).
 */
export default defineConfig({
    testDir: "./e2e",
    testMatch: /.*\.spec\.ts/,
    outputDir: "./e2e/.results",

    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,

    reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",

    use: {
        baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
        trace: "on-first-retry",
        screenshot: "only-on-failure",
        video: "retain-on-failure",
    },

    projects: [
        {
            name: "chromium",
            use: { ...devices["Desktop Chrome"] },
        },
    ],

    webServer: {
        command: "npm run dev",
        url: "http://localhost:3000",
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
        stdout: "ignore",
        stderr: "pipe",
    },
});
