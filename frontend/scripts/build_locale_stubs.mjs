/**
 * I18N.UI — genera stubs para locales pendientes de traducción (CA/EU/GL).
 *
 * Lee `src/messages/es.json` y produce archivos espejo con un prefijo
 * `[XX] ` en cada string. Esto permite:
 *   - Compilar la app en cualquier locale soportado sin null refs.
 *   - Detectar visualmente strings sin traducir en QA manual.
 *   - Entregar a la agencia de traducción (I18N.TR) un JSON ya estructurado.
 *
 * Ejecutar tras añadir keys nuevas en es.json:
 *   node frontend/scripts/build_locale_stubs.mjs
 *
 * Ya generadas las traducciones reales por agencia, este script NO debe
 * sobrescribir — usar el flag `--force` (cuidado: borra trabajo manual).
 */
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");
const SRC = resolve(ROOT, "src/messages/es.json");

const TARGETS = [
    { code: "ca", prefix: "[CA] " },
    { code: "eu", prefix: "[EU] " },
    { code: "gl", prefix: "[GL] " },
];

const force = process.argv.includes("--force");

function transform(node, prefix) {
    if (typeof node === "string") return prefix + node;
    if (Array.isArray(node)) return node.map((n) => transform(n, prefix));
    if (node && typeof node === "object") {
        const out = {};
        for (const [k, v] of Object.entries(node)) out[k] = transform(v, prefix);
        return out;
    }
    return node; // numbers, booleans
}

const source = JSON.parse(readFileSync(SRC, "utf8"));

for (const target of TARGETS) {
    const outPath = resolve(ROOT, `src/messages/${target.code}.json`);
    if (existsSync(outPath) && !force) {
        console.log(`Skip ${target.code}.json (ya existe, usa --force para sobrescribir)`);
        continue;
    }
    const data = transform(source, target.prefix);
    writeFileSync(outPath, JSON.stringify(data, null, 2) + "\n", "utf8");
    console.log(`Generado ${target.code}.json (${countLeaves(data)} keys)`);
}

function countLeaves(node) {
    if (typeof node === "string") return 1;
    if (Array.isArray(node)) return node.reduce((a, n) => a + countLeaves(n), 0);
    if (node && typeof node === "object") {
        return Object.values(node).reduce((a, v) => a + countLeaves(v), 0);
    }
    return 0;
}
