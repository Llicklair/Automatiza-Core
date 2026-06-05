module.exports = {
    plugins: {
        // Tailwind v4: el plugin PostCSS se movió a un paquete aparte.
        // `@tailwindcss/postcss` ya incluye el autoprefixing (Lightning CSS),
        // por eso no se declara autoprefixer por separado.
        "@tailwindcss/postcss": {},
    },
}
