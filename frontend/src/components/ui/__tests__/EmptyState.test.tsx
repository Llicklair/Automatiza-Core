/**
 * Tests del componente reutilizable EmptyState (UI.EMP).
 */
import { afterEach, describe, it, expect, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FileText } from "lucide-react";
import { EmptyState } from "../EmptyState";

describe("EmptyState", () => {
    afterEach(() => cleanup());
    it("renderiza título y descripción", () => {
        render(
            <EmptyState
                icon={FileText}
                title="No hay facturas"
                description="Crea la primera."
            />,
        );
        expect(screen.getByText("No hay facturas")).toBeInTheDocument();
        expect(screen.getByText("Crea la primera.")).toBeInTheDocument();
    });

    it("incluye role=status y aria-live polite", () => {
        const { container } = render(
            <EmptyState icon={FileText} title="Vacío" />,
        );
        const status = container.querySelector('[role="status"]');
        expect(status).not.toBeNull();
        expect(status?.getAttribute("aria-live")).toBe("polite");
    });

    it("renderiza el label del CTA primario cuando se proporciona href", () => {
        // next/link está mockeado en vitest.setup.ts para devolver solo children,
        // por lo que comprobamos contenido textual, no role="link".
        render(
            <EmptyState
                icon={FileText}
                title="Sin clientes"
                action={{ label: "Crear cliente", href: "/clientes/nuevo" }}
            />,
        );
        expect(screen.getByText("Crear cliente")).toBeInTheDocument();
    });

    it("dispara onClick del CTA primario sin href", async () => {
        const handler = vi.fn();
        render(
            <EmptyState
                icon={FileText}
                title="Sin asientos"
                action={{ label: "Importar", onClick: handler }}
            />,
        );
        await userEvent.click(
            screen.getByRole("button", { name: /importar/i }),
        );
        expect(handler).toHaveBeenCalledTimes(1);
    });

    it("renderiza ambos labels cuando se proporcionan action y secondaryAction", () => {
        render(
            <EmptyState
                icon={FileText}
                title="Vacío"
                action={{ label: "Crear", href: "/x" }}
                secondaryAction={{ label: "Importar CSV", href: "/import" }}
            />,
        );
        expect(screen.getByText("Crear", { exact: false })).toBeInTheDocument();
        expect(screen.getByText("Importar CSV")).toBeInTheDocument();
    });

    it("ajusta el padding cuando size=sm", () => {
        const { container } = render(
            <EmptyState icon={FileText} title="Vacío" size="sm" />,
        );
        const root = container.querySelector('[role="status"]');
        expect(root?.className).toMatch(/py-8/);
    });
});
