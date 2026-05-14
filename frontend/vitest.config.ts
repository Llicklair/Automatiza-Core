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
            // Empezamos en 20% para no romper CI mientras se rampea, y
            // subir cada quarter según `docs/ci_quality_gates.md`.
            thresholds: {
                lines: 20,
                functions: 20,
                branches: 20,
                statements: 20,
            },
        },
    },
});
