/**
 * QA.AXE — auditoría WCAG 2.1 AA del footer de trazabilidad LLM.
 *
 * El texto del footer es informativo y debe ser legible por lectores de
 * pantalla. El símbolo decorativo `↳` queda marcado con `aria-hidden`.
 */
import { describe, it, expect, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { AIGenerationFooter } from "@/components/ai/AIGenerationFooter";
import { axe } from "./setup";

describe("AIGenerationFooter — a11y", () => {
    afterEach(() => cleanup());

    it("no renderiza nada cuando no recibe metadata (sin a11y issues)", async () => {
        const { container } = render(<AIGenerationFooter />);
        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });

    it("cumple WCAG 2.1 AA con metadata completa", async () => {
        const { container } = render(
            <AIGenerationFooter
                provider="Anthropic"
                model="claude-haiku-4-5"
                tokensIn={1234}
                tokensOut={567}
            />,
        );
        const results = await axe(container);
        expect(results).toHaveNoViolations();
    });
});
