// Flat config para ESLint v9+ (el formato .eslintrc.json dejó de soportarse).
// eslint-config-next v16 exporta directamente un flat config (Linter.Config[]),
// así que no hace falta @eslint/eslintrc ni FlatCompat.
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
    ...nextCoreWebVitals,
    {
        // Equivalente al antiguo .eslintignore: los tests no pasan el lint de
        // producción (Vitest + TypeScript ya validan sintaxis y tipos).
        ignores: [
            "**/*.test.ts",
            "**/*.test.tsx",
            "**/__tests__/**",
            "src/test/**",
        ],
    },
];

export default eslintConfig;
