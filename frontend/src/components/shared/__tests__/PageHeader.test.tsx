/**
 * Tests del componente canónico `shared/PageHeader`.
 * (Heredados de ui/PageHeader, retirado en la auditoría UIX #8.)
 */
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { PageHeader } from "../PageHeader";

describe("PageHeader", () => {
    afterEach(() => cleanup());

    it("renderiza título como h1", () => {
        render(<PageHeader title="Facturas" />);
        const h = screen.getByRole("heading", { level: 1 });
        expect(h.textContent).toBe("Facturas");
    });

    it("renderiza descripción cuando se pasa", () => {
        render(
            <PageHeader title="Facturas" description="Gestión de facturas emitidas." />,
        );
        expect(
            screen.getByText("Gestión de facturas emitidas."),
        ).toBeInTheDocument();
    });

    it("no renderiza descripción cuando se omite", () => {
        const { container } = render(<PageHeader title="X" />);
        const ps = container.querySelectorAll("p");
        expect(ps.length).toBe(0);
    });

    it("renderiza actions a la derecha cuando se pasan", () => {
        render(
            <PageHeader
                title="Facturas"
                actions={<button>Nueva</button>}
            />,
        );
        expect(screen.getByRole("button", { name: "Nueva" })).toBeInTheDocument();
    });
});
