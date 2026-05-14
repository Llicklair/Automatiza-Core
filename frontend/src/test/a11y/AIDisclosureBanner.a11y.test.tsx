/**
 * QA.AXE — auditoría WCAG 2.1 AA del banner Art. 50 AI Act.
 *
 * El banner es el primer punto de contacto con el usuario en cualquier
 * dominio que invoque un agente LLM, por lo que su accesibilidad es
 * crítica para cumplir simultáneamente el RD 1112/2018 (UNE-EN 301 549)
 * y el Reglamento UE 2024/1689.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { AIDisclosureBanner } from "@/components/ai/AIDisclosureBanner";
import { axe } from "./setup";

describe("AIDisclosureBanner — a11y", () => {
    beforeEach(() => {
        window.localStorage.clear();
        cleanup();
    });

    it("no presenta violaciones WCAG 2.1 AA en su estado inicial", async () => {
        const { container } = render(<AIDisclosureBanner />);
        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });

    it("mantiene la conformidad con nota extra y dominio asignado", async () => {
        const { container } = render(
            <AIDisclosureBanner domain="hr" extraNote="Agente RRHH activo" />,
        );
        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });
});
