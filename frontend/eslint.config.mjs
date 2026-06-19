// Flat config para ESLint v9+ (el formato .eslintrc.json dejó de soportarse).
// eslint-config-next v16 exporta directamente un flat config (Linter.Config[]),
// así que no hace falta @eslint/eslintrc ni FlatCompat.
import nextCoreWebVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
    ...nextCoreWebVitals,
    {
        // React Compiler (eslint-plugin-react-hooks v7) marca como ERROR varios
        // patrones que el compilador prefiere pero que NO son bugs en código que
        // ya funciona: setState síncrono en effects (el idioma de carga de datos
        // que la propia doc de React recomienda), llamadas "impuras" en render,
        // componentes/refs en render, etc. Adoptarlos de golpe rompe el CI con
        // +120 avisos en código correcto, y las "soluciones" son hacks que
        // ensucian sin arreglar nada. Los dejamos en `off`: 120+ warnings
        // permanentes ahogarían la señal del lint (con --max-warnings no verías
        // un aviso nuevo de verdad). Reactivar (warn/error) el día que se adopte
        // el React Compiler. exhaustive-deps SÍ sigue activo (regla útil).
        rules: {
            "react-hooks/set-state-in-effect": "off",
            "react-hooks/immutability": "off",
            "react-hooks/purity": "off",
            "react-hooks/static-components": "off",
            "react-hooks/refs": "off",
            "react-hooks/incompatible-library": "off",
        },
    },
    {
        // Invariante de arquitectura (ARCHITECTURE.md §9): los componentes nunca
        // hacen `fetch()` directo — toda llamada HTTP pasa por `lib/api/*` (cuya
        // base única es `client.ts`: maneja JWT, refresh 401 y errores). La
        // auditoría confirmó 0 violaciones; este gate lo blinda. Arranca en `warn`
        // (cultura de rampa del repo); subir a `error` cuando esté asentado.
        files: ["src/**/*.{ts,tsx}"],
        rules: {
            "no-restricted-syntax": [
                "warn",
                {
                    selector: "CallExpression[callee.name='fetch']",
                    message:
                        "No uses fetch() directo: usa lib/api/* (client.ts). Ver ARCHITECTURE.md §9.",
                },
                {
                    selector: "CallExpression[callee.property.name='fetch']",
                    message:
                        "No uses window/globalThis.fetch directo: usa lib/api/* (client.ts). Ver ARCHITECTURE.md §9.",
                },
            ],
        },
    },
    {
        // La capa lib/api SÍ puede usar fetch crudo: es la frontera HTTP real
        // (client.ts, SSE de taskStream, client_portal/scanner con JWT propio).
        // error-reporter.ts vive en src/lib/ (no en lib/api) pero es otra frontera
        // legítima: reporta errores y no puede pasar por el api-client sin
        // circularidad. Aquí viven las excepciones justificadas.
        files: ["src/lib/api/**", "src/lib/error-reporter.ts"],
        rules: { "no-restricted-syntax": "off" },
    },
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
