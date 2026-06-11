/**
 * I18N.CHECK — guardia de paridad de claves entre es.json y en.json.
 *
 * Falla (exit 1) si alguno de los dos tiene claves que el otro no tiene:
 * cada clave nueva en es.json debe llegar con su par inglés en el mismo
 * commit (migración i18n real, #1 fase 2). ca/eu/gl quedan exentos: son
 * stubs regenerables con build_locale_stubs.mjs.
 *
 *   npm run i18n:check
 */
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "..");

function flatten(node, prefix = "", out = new Set()) {
    if (typeof node === "string") {
        out.add(prefix);
    } else if (node && typeof node === "object" && !Array.isArray(node)) {
        for (const [k, v] of Object.entries(node)) {
            flatten(v, prefix ? `${prefix}.${k}` : k, out);
        }
    } else {
        out.add(prefix); // arrays/números: tratarlos como hoja
    }
    return out;
}

function load(code) {
    return JSON.parse(
        readFileSync(resolve(ROOT, `src/messages/${code}.json`), "utf8"),
    );
}

const esKeys = flatten(load("es"));
const enKeys = flatten(load("en"));

const missingInEn = [...esKeys].filter((k) => !enKeys.has(k));
const orphansInEn = [...enKeys].filter((k) => !esKeys.has(k));

if (missingInEn.length === 0 && orphansInEn.length === 0) {
    console.log(`i18n:check OK — ${esKeys.size} claves en paridad es/en`);
    process.exit(0);
}

if (missingInEn.length) {
    console.error(`\nFALTAN en en.json (${missingInEn.length}):`);
    for (const k of missingInEn) console.error(`  - ${k}`);
}
if (orphansInEn.length) {
    console.error(`\nHUÉRFANAS en en.json (${orphansInEn.length}):`);
    for (const k of orphansInEn) console.error(`  - ${k}`);
}
process.exit(1);
