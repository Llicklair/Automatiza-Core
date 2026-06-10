/**
 * Tests del wrapper único de página `shared/PageContainer` (auditoría UIX #11).
 */
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { PageContainer } from "../PageContainer";

describe("PageContainer", () => {
    afterEach(() => cleanup());

    it("aplica padding y ancho por defecto (1400px)", () => {
        const { container } = render(<PageContainer>hola</PageContainer>);
        const div = container.firstElementChild!;
        expect(div.className).toContain("p-6");
        expect(div.className).toContain("max-w-[1400px]");
        expect(div.className).toContain("mx-auto");
    });

    it("respeta el width indicado", () => {
        const { container } = render(
            <PageContainer width="3xl">hola</PageContainer>,
        );
        expect(container.firstElementChild!.className).toContain("max-w-3xl");
        expect(container.firstElementChild!.className).not.toContain("max-w-[1400px]");
    });

    it("width=full no limita el ancho", () => {
        const { container } = render(
            <PageContainer width="full">hola</PageContainer>,
        );
        expect(container.firstElementChild!.className).not.toContain("max-w");
    });

    it("acepta className extra sin perder las bases", () => {
        const { container } = render(
            <PageContainer className="relative space-y-8">hola</PageContainer>,
        );
        const cls = container.firstElementChild!.className;
        expect(cls).toContain("relative");
        expect(cls).toContain("space-y-8");
        expect(cls).not.toContain("space-y-6"); // tailwind-merge resuelve el conflicto
        expect(cls).toContain("p-6");
    });
});
