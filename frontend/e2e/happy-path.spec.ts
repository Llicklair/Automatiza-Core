import { test, expect } from "@playwright/test";

/**
 * Happy path E2E (QA.E2E): signup → factura → Verifactu QR → simulación 303.
 *
 * **Requiere backend FastAPI corriendo en :8000** y Postgres local en :5433
 * (ver `frontend/e2e/README.md` para arranque). Los tests siguientes están
 * `skip` hasta que se decida la estrategia de seed y storage state.
 *
 * TODO (sesión dedicada, ~1-2d):
 * 1. `auth.setup.ts` con signup + login real y guardado de storage state.
 * 2. Seed determinista de tenant + cliente vía API o fixture pytest.
 * 3. Test: crear factura → verificar QR Verifactu → comprobar /verify/{huella}.
 * 4. Test: simulación modelo 303 con datos del trimestre.
 * 5. Test: presentación contra mock AEAT (cuando PRES.303 esté integrado).
 */

test.skip("signup completo crea tenant y permite login", async ({ page }) => {
    // TODO: usar email único por test (`${randomUUID()}@e2e.test`).
    await page.goto("/registro");
    // Rellenar formulario completo y submit.
    // Verificar redirect a /bienvenida o /.
});

test.skip("crear factura genera QR Verifactu", async ({ page }) => {
    // Pre-requisito: storage state cargado por auth.setup.ts.
    await page.goto("/ventas/facturas/nueva");
    // Rellenar form + crear → comprobar que aparece QR + huella visible.
});

test.skip("simulación modelo 303 muestra resultado", async ({ page }) => {
    await page.goto("/bienvenida/simulacion-303");
    await expect(page.getByText(/Datos ejemplo|Simulación/)).toBeVisible();
});
