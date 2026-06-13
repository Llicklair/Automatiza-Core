/**
 * sanitize-env.js — genera `.env.dist` saneado para empaquetar (predist).
 *
 * El instalador NO debe distribuir el `.env` real del desarrollador: filtraría
 * secretos a cada cliente. Este script copia `../.env` a `desktop/.env.dist`
 * eliminando las claves que NO deben viajar:
 *
 *   - Secretos generados por-instalación (vienen de Electron safeStorage):
 *     SECRET_KEY, TENANT_ENCRYPTION_KEY.
 *   - Infra per-install (la genera el desktop): POSTGRES_*, DATABASE_URL.
 *   - Observabilidad/tracing del desarrollador: LANGFUSE_*, LLM_TRACE_*.
 *
 * NOTA Google: GOOGLE_CLIENT_SECRET SÍ se conserva. Google exige el secret en el
 * intercambio aunque uses PKCE (incluso con un cliente Desktop, donde el secret
 * NO es confidencial por diseño), y el token de Gmail debe quedarse local — por
 * eso Google NO pasa por el proxy. El flujo usa PKCE (S256) como protección extra
 * (ver app/integrations/google_oauth.py). Los *_CLIENT_SECRET de redes sociales
 * en cambio SÍ se eliminan: viven en el proxy de Render (ver DENY_EXACT abajo).
 */
const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "..", ".env");
const OUT = path.join(__dirname, ".env.dist");

// Claves exactas a eliminar + prefijos (cualquier clave que empiece por ellos).
const DENY_EXACT = new Set([
  "SECRET_KEY",
  "TENANT_ENCRYPTION_KEY",
  "DATABASE_URL",
  "POSTGRES_USER",
  "POSTGRES_PASSWORD",
  "POSTGRES_DB",
  // Secrets OAuth de redes sociales → ahora viven en el proxy (Render), no en
  // el binario. Los CLIENT_ID se quedan (públicos, para construir la URL de login).
  "FACEBOOK_CLIENT_SECRET",
  "INSTAGRAM_CLIENT_SECRET",
  "TWITTER_CLIENT_SECRET",
  "LINKEDIN_CLIENT_SECRET",
  // Key de Unsplash → vive en el proxy de Render (/images/search), no en el binario.
  "UNSPLASH_ACCESS_KEY",
]);
const DENY_PREFIX = ["LANGFUSE_", "LLM_TRACE_"];

function isDenied(key) {
  if (DENY_EXACT.has(key)) return true;
  return DENY_PREFIX.some((p) => key.startsWith(p));
}

function main() {
  const header =
    "# .env de distribución (generado por sanitize-env.js).\n" +
    "# Secretos por-instalación (SECRET_KEY/TENANT_ENCRYPTION_KEY) y la BD se\n" +
    "# resuelven en runtime; no se incluyen aquí. NO commitear este fichero.\n";

  if (!fs.existsSync(SRC)) {
    console.warn(`[sanitize-env] No existe ${SRC}; genero .env.dist vacío.`);
    fs.writeFileSync(OUT, header, "utf8");
    return;
  }

  const lines = fs.readFileSync(SRC, "utf8").split(/\r?\n/);
  const kept = [];
  let removed = 0;
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      kept.push(line);
      continue;
    }
    const eq = line.indexOf("=");
    const key = (eq >= 0 ? line.slice(0, eq) : line).trim();
    if (isDenied(key)) {
      removed += 1;
      continue;
    }
    kept.push(line);
  }

  fs.writeFileSync(OUT, header + kept.join("\n"), "utf8");
  console.log(`[sanitize-env] .env.dist generado — ${removed} claves sensibles eliminadas.`);
}

main();
