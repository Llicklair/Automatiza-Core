/**
 * U.6 WCAG / QA.AXE — setup compartido para tests de accesibilidad.
 *
 * Extiende `expect` con el matcher `toHaveNoViolations` de `vitest-axe`
 * y configura axe-core con las reglas de WCAG 2.1 AA. Importar este
 * archivo en cada test a11y antes de las aserciones.
 */
import { expect } from "vitest";
import * as matchers from "vitest-axe/matchers";
import { configureAxe } from "vitest-axe";

expect.extend(matchers);

declare module "vitest" {
    interface Assertion {
        toHaveNoViolations(): void;
    }
    interface AsymmetricMatchersContaining {
        toHaveNoViolations(): void;
    }
}

export const axe = configureAxe({
    rules: {
        "color-contrast": { enabled: true },
        "label": { enabled: true },
        "landmark-one-main": { enabled: false },
        "page-has-heading-one": { enabled: false },
        "region": { enabled: false },
    },
    runOnly: {
        type: "tag",
        values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"],
    },
});
