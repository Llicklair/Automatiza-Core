/**
 * Tests del componente UI.POL `PageHeader`.
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

    it("renderiza breadcrumb encima del título cuando se pasa", () => {
        const { container } = render(
            <PageHeader
                title="Detalle"
                breadcrumb={<nav data-testid="bc">Inicio &gt; Facturas</nav>}
            />,
        );
        const bc = screen.getByTestId("bc");
        const h1 = container.querySelector("h1");
        // breadcrumb debe aparecer ANTES del h1 en el DOM
        expect(bc.compareDocumentPosition(h1!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it("usa role banner (header semántico) ", () => {
        const { container } = render(<PageHeader title="X" />);
        // <header> sin <main> ancestro es banner por defecto; cuando va
        // anidado dentro de <main> no, pero el elemento `<header>` debe existir.
        expect(container.querySelector("header")).not.toBeNull();
    });
});
