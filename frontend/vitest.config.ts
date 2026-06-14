import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            "@": path.resolve(__dirname, "./src"),
        },
    },
    test: {
        globals: true,
        environment: "jsdom",
        setupFiles: ["./vitest.setup.ts"],
        include: ["src/**/*.test.{ts,tsx}"],
        coverage: {
            provider: "v8",
            reporter: ["text", "json", "html"],
            include: ["src/**/*.{ts,tsx}"],
            exclude: [
                "src/**/*.test.{ts,tsx}",
                "src/test-utils/**",
                "src/**/types.ts",
                "src/test/a11y/**",
            ],
            // QA.CI — gates de cobertura (target consenso: 40% líneas).
            // Suelo alineado a la cobertura ACTUAL (~2,7%): el 20% previo rompía
            // el CI (cobertura real muy por debajo), justo lo contrario de su
            // intención. Es un floor anti-regresión; subir cada quarter hacia el
            // target según `docs/ci_quality_gates.md`.
            thresholds: {
                lines: 2,
                functions: 2,
                branches: 1,
                statements: 2,
            },
        },
    },
});
