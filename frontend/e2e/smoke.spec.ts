import { test, expect } from "@playwright/test";

/**
 * Smoke tests E2E — sin dependencia de backend.
 *
 * Verifican que el dev server arranca, las páginas estáticas renderizan
 * y la navegación a rutas auth funciona. Sirven como red de seguridad
 * mínima en CI antes de añadir flows con backend (signup → factura → 303).
 */

test("home redirige a login cuando no hay sesión", async ({ page }) => {
    await page.goto("/");
    // Sin token, el middleware/guard debe llevar al login.
    await expect(page).toHaveURL(/\/(login|registro)/);
});

test("login muestra formulario con email y password", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByLabel(/email|correo/i)).toBeVisible();
    await expect(page.getByLabel(/password|contraseña/i)).toBeVisible();
});

test("login → registro link navega", async ({ page }) => {
    await page.goto("/login");
    const registroLink = page.getByRole("link", { name: /reg[ií]strate|crear cuenta|registro/i });
    if (await registroLink.count()) {
        await registroLink.first().click();
        await expect(page).toHaveURL(/\/registro/);
    } else {
        // Si no hay link directo, comprobar que /registro existe per se.
        await page.goto("/registro");
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    }
});
