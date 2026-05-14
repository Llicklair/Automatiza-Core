/**
 * QA.AXE — auditoría WCAG 2.1 AA de la página de login.
 *
 * El login es el primer punto de contacto con cualquier usuario, incluidos
 * empleados de gestoría con lector de pantalla. Comprobaciones críticas:
 * inputs etiquetados, errores anunciados, decorativos ocultos a SR.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render } from "@/test-utils/render";
import LoginPage from "@/app/(auth)/login/page";
import { axe } from "./setup";

vi.mock("@/lib/api", () => ({
    api: {
        auth: {
            login: vi.fn(),
        },
    },
}));

beforeEach(() => {
    localStorage.clear();
});

describe("LoginPage — a11y", () => {
    it("no presenta violaciones WCAG 2.1 AA en su estado inicial", async () => {
        const { container } = render(<LoginPage />);
        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });
});
