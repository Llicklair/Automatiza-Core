/**
 * Gestor de servicios nativos — reemplaza docker-manager.js.
 * Orquesta: PostgreSQL portable + Python/uvicorn + Next.js
 */
const path = require("path");
const http = require("http");
const { spawn, execSync } = require("child_process");
const fs = require("fs");
const os = require("os");

const APPDATA_DIR = path.join(process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming"), "AutomatizaPyme");
if (!fs.existsSync(APPDATA_DIR)) try { fs.mkdirSync(APPDATA_DIR, { recursive: true }); } catch {}

// Log en Escritorio para diagnóstico infalible
const BOOT_LOG = path.join(os.homedir(), "Desktop", "AutomatizaPyme_BOOT_LOG.txt");

function logBoot(msg) {
  const ts = new Date().toISOString();
  try { fs.appendFileSync(BOOT_LOG, `[${ts}] [service-manager] ${msg}\n`); } catch {}
  console.log(msg);
}

logBoot("Modulo service-manager cargado.");

const {
  isPostgresInstalled,
  downloadPostgres,
  initDatabase,
  startPostgres,
  stopPostgres,
  waitForPostgres,
  createDatabase,
  getDatabaseURL,
  PG_PORT,
} = require("./postgres-manager");

const {
  isPythonInstalled,
  areDepsInstalled,
  downloadPython,
  installDeps,
  startBackend,
  stopBackend,
  runMigrations,
} = require("./python-manager");

const { getLanIP } = require("./network-utils");

let PROJECT_ROOT;
try {
  const { app } = require("electron");
  PROJECT_ROOT =
    app && app.isPackaged
      ? path.join(process.resourcesPath, "project")
      : path.resolve(__dirname, "..");
} catch {
  PROJECT_ROOT = path.resolve(__dirname, "..");
}
const FRONTEND_DIR = path.join(PROJECT_ROOT, "frontend");

/**
 * Lee el .env del proyecto y devuelve un objeto clave-valor.
 * Busca en: raíz del proyecto → APPDATA (portable) → vacío.
 * Ignora líneas comentadas (#) y soporta valores con espacios.
 */
function loadDotEnv() {
  const candidates = [
    path.join(PROJECT_ROOT, ".env"),
    path.join(APPDATA_DIR, ".env"),
  ];
  for (const envPath of candidates) {
    if (fs.existsSync(envPath)) {
      logBoot(`Cargando .env desde: ${envPath}`);
      const vars = {};
      const lines = fs.readFileSync(envPath, "utf8").split("\n");
      for (const raw of lines) {
        const line = raw.trim();
        if (!line || line.startsWith("#")) continue;
        const eqIdx = line.indexOf("=");
        if (eqIdx < 1) continue;
        const key = line.slice(0, eqIdx).trim();
        let val = line.slice(eqIdx + 1).trim();
        // Quitar comentarios inline (solo si hay espacio antes del #)
        const commentIdx = val.indexOf(" #");
        if (commentIdx > -1) val = val.slice(0, commentIdx).trim();
        // Quitar comillas envolventes
        if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
          val = val.slice(1, -1);
        }
        vars[key] = val;
      }
      return vars;
    }
  }
  logBoot("No se encontró .env, usando solo variables del sistema.");
  return {};
}

const dotEnv = loadDotEnv();

/** Busca una variable: .env del proyecto > variable del sistema > fallback */
function envVar(key, fallback = "") {
  return dotEnv[key] || process.env[key] || fallback;
}

let frontendProcess = null;

/**
 * Mata procesos huérfanos que puedan haber quedado de una ejecución anterior.
 * Busca por puerto (8080=backend, 3000=frontend) y mata el árbol completo.
 */
function killOrphanProcesses() {
  const portsToClean = [8080, 3000];
  for (const port of portsToClean) {
    try {
      const output = execSync(
        `netstat -ano | findstr "LISTENING" | findstr ":${port}"`,
        { stdio: "pipe", timeout: 5000 }
      ).toString();
      const lines = output.trim().split("\n");
      for (const line of lines) {
        const parts = line.trim().split(/\s+/);
        const pid = parseInt(parts[parts.length - 1], 10);
        if (pid && pid > 4) {
          logBoot(`Matando proceso huérfano en puerto ${port} (PID ${pid})...`);
          try {
            execSync(`taskkill /PID ${pid} /T /F`, { stdio: "ignore", timeout: 5000 });
          } catch {}
        }
      }
    } catch {
      // No hay nada escuchando en ese puerto — OK
    }
  }
}

/**
 * Genera o recupera SECRET_KEY y TENANT_ENCRYPTION_KEY persistentes.
 * Se almacenan en APPDATA para que sobrevivan reinicios.
 */
function getOrCreateSecrets() {
  const secretsPath = path.join(APPDATA_DIR, "secrets.json");
  if (fs.existsSync(secretsPath)) {
    try {
      return JSON.parse(fs.readFileSync(secretsPath, "utf8"));
    } catch {}
  }
  // Generar claves nuevas
  const crypto = require("crypto");
  const secrets = {
    SECRET_KEY: crypto.randomBytes(32).toString("hex"),
    TENANT_ENCRYPTION_KEY: crypto.randomBytes(32).toString("base64url"),
  };
  try { fs.writeFileSync(secretsPath, JSON.stringify(secrets)); } catch {}
  return secrets;
}

/**
 * Genera las variables de entorno para el backend.
 * Lee del .env del proyecto (prioridad) > variables del sistema > defaults.
 */
function getBackendEnv(lanIP) {
  const corsOrigins = `http://localhost:3000,http://${lanIP}:3000`;
  const secrets = getOrCreateSecrets();

  return {
    DATABASE_URL: getDatabaseURL(),
    FRONTEND_URL: corsOrigins,
    ENVIRONMENT: "production",
    DEBUG: "true",
    SECRET_KEY: secrets.SECRET_KEY,
    TENANT_ENCRYPTION_KEY: secrets.TENANT_ENCRYPTION_KEY,
    // LLM
    DEFAULT_LLM_PROVIDER:  envVar("DEFAULT_LLM_PROVIDER", "gemini"),
    GEMINI_API_KEY:        envVar("GEMINI_API_KEY"),
    GEMINI_MODEL:          envVar("GEMINI_MODEL", "gemini-2.5-flash"),
    OPENROUTER_API_KEY:    envVar("OPENROUTER_API_KEY"),
    OPENROUTER_MODEL:      envVar("OPENROUTER_MODEL"),
    GROQ_API_KEY:          envVar("GROQ_API_KEY"),
    GROQ_MODEL:            envVar("GROQ_MODEL"),
    OPENAI_API_KEY:        envVar("OPENAI_API_KEY"),
    OPENAI_MODEL:          envVar("OPENAI_MODEL"),
    ANTHROPIC_API_KEY:     envVar("ANTHROPIC_API_KEY"),
    ANTHROPIC_MODEL:       envVar("ANTHROPIC_MODEL"),
    // OAuth
    GOOGLE_CLIENT_ID:      envVar("GOOGLE_CLIENT_ID"),
    GOOGLE_CLIENT_SECRET:  envVar("GOOGLE_CLIENT_SECRET"),
    GOOGLE_REDIRECT_URI:   envVar("GOOGLE_REDIRECT_URI"),
    MICROSOFT_CLIENT_ID:   envVar("MICROSOFT_CLIENT_ID"),
    MICROSOFT_CLIENT_SECRET: envVar("MICROSOFT_CLIENT_SECRET"),
    MICROSOFT_REDIRECT_URI:  envVar("MICROSOFT_REDIRECT_URI"),
    // SMTP
    SMTP_HOST:     envVar("SMTP_HOST"),
    SMTP_PORT:     envVar("SMTP_PORT", "587"),
    SMTP_USER:     envVar("SMTP_USER"),
    SMTP_PASSWORD: envVar("SMTP_PASSWORD"),
    SMTP_TLS:      envVar("SMTP_TLS", "true"),
    // Embeddings
    EMBEDDINGS_PROVIDER:    envVar("EMBEDDINGS_PROVIDER", "local"),
    EMBEDDINGS_LOCAL_MODEL: envVar("EMBEDDINGS_LOCAL_MODEL", "BAAI/bge-m3"),
  };
}

/**
 * Arranca Next.js (frontend).
 * Si .next no existe o la API URL cambió, hacer build primero (síncrono).
 * Usa npx next para evitar problemas de PATH con el binario next.
 */
function startFrontend(lanIP) {
  const isWin = process.platform === "win32";
  const npmCmd = isWin ? "npm.cmd" : "npm";
  const apiUrl = `http://${lanIP}:8080`;
  const nextDir = path.join(FRONTEND_DIR, ".next");
  const urlMarker = path.join(FRONTEND_DIR, ".next", ".api_url");

  // Entorno común para build y start
  const frontendEnv = {
    ...process.env,
    NEXT_PUBLIC_API_URL: apiUrl,
    PORT: "3000",
  };

  const nodeModulesDir = path.join(FRONTEND_DIR, "node_modules");
  let depsInstalled = fs.existsSync(nodeModulesDir);

  if (!depsInstalled) {
    logBoot("Frontend: instalando dependencias (npm install)...");
    try {
      execSync(`${npmCmd} install`, {
        cwd: FRONTEND_DIR,
        stdio: "pipe",
        timeout: 600000, // 10 min
      });
      logBoot("Frontend: dependencias instaladas.");
    } catch (err) {
      logBoot(`[FRONTEND INSTALL ERROR] ${err.message}`);
      if (err.stderr) logBoot(`[FRONTEND INSTALL STDERR] ${err.stderr.toString().trim()}`);
    }
  }

  // Decidir si necesitamos rebuild
  let needsBuild = !fs.existsSync(nextDir);
  if (!needsBuild) {
    try {
      const savedUrl = fs.readFileSync(urlMarker, "utf8").trim();
      needsBuild = savedUrl !== apiUrl;
    } catch {
      needsBuild = true; // sin marcador → rebuild
    }
  }

  logBoot(`Frontend: needsBuild=${needsBuild}`);

  // ── FASE 1: Build síncrono si es necesario ───────────────────────────────
  if (needsBuild) {
    logBoot("Frontend: ejecutando 'npm run build'...");
    try {
      execSync(`${npmCmd} run build`, {
        cwd: FRONTEND_DIR,
        env: frontendEnv,
        stdio: "pipe",   // capturar stderr para no bloquear
        timeout: 600000,  // 10 min máximo
      });
      logBoot("Frontend: build completado.");
      // Guardar marcador de URL para no reconstruir la próxima vez
      try { fs.writeFileSync(urlMarker, apiUrl); } catch {}
    } catch (buildErr) {
      logBoot(`[FRONTEND BUILD ERROR] ${buildErr.message}`);
      if (buildErr.stderr) logBoot(`[FRONTEND BUILD STDERR] ${buildErr.stderr.toString().trim()}`);
      // No lanzamos error fatal: intentamos arrancar igualmente por si hay build previo
    }
  }

  // ── FASE 2: Arrancar el servidor Next.js ─────────────────────────────────
  logBoot("Frontend: arrancando servidor Next.js...");
  frontendProcess = spawn(
    npmCmd,
    ["start", "--", "-H", "0.0.0.0"],
    {
      cwd: FRONTEND_DIR,
      env: frontendEnv,
      stdio: "pipe",
    }
  );

  frontendProcess.stderr.on("data", (data) => {
    logBoot(`[FRONTEND STDERR] ${data.toString().trim()}`);
  });

  frontendProcess.stdout.on("data", (data) => {
    logBoot(`[FRONTEND STDOUT] ${data.toString().trim()}`);
  });

  frontendProcess.on("error", (err) => {
    logBoot(`[FRONTEND ERROR] ${err.message}`);
  });

  frontendProcess.on("close", (code) => {
    logBoot(`[FRONTEND CLOSE] código ${code}`);
  });

  return frontendProcess;
}

/**
 * Para el frontend.
 */
function stopFrontend() {
  if (!frontendProcess) return;
  try {
    if (process.platform === "win32") {
      execSync(`taskkill /PID ${frontendProcess.pid} /T /F`, { stdio: "ignore" });
    } else {
      frontendProcess.kill("SIGTERM");
    }
  } catch {}
  frontendProcess = null;
}

/**
 * Espera a que un puerto HTTP responda.
 */
function waitForHTTP(port, timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      // Usar 127.0.0.1 explícitamente: en Windows, "localhost" resuelve a ::1 (IPv6)
      // pero uvicorn con 0.0.0.0 solo escucha IPv4.
      const req = http.get(`http://127.0.0.1:${port}`, (res) => {
        resolve();
        res.resume();
      });
      req.on("error", () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Puerto ${port} no respondió en ${timeoutMs / 1000}s`));
        } else {
          setTimeout(check, 2000);
        }
      });
      req.setTimeout(3000, () => {
        req.destroy();
        setTimeout(check, 2000);
      });
    };
    check();
  });
}

/**
 * Flujo completo de arranque.
 * @param {Function} onProgress - (message, percent) callback
 */
async function startAll(onProgress) {
  logBoot("Iniciando startAll...");
  try {
    // Limpiar procesos huérfanos de ejecuciones anteriores
    logBoot("Limpiando procesos huérfanos...");
    killOrphanProcesses();

    const lanIP = getLanIP();
    logBoot(`IP detectada: ${lanIP}`);

    const backendEnv = getBackendEnv(lanIP);
    logBoot("Variables de entorno backend preparadas.");

    // 1. PostgreSQL
    logBoot("Comprobando instalacin de PostgreSQL...");
    if (!isPostgresInstalled()) {
      logBoot("PostgreSQL no instalado. Descargando...");
      await downloadPostgres((msg, pct) => onProgress(msg, pct * 0.2));
    }
    
    logBoot("Inicializando base de datos...");
    onProgress("Inicializando base de datos...", 20);
    await initDatabase();

    logBoot("Arrancando PostgreSQL...");
    onProgress("Arrancando PostgreSQL...", 25);
    await startPostgres();
    
    logBoot("Esperando respuesta de PostgreSQL...");
    await waitForPostgres();
    logBoot("PostgreSQL operativo.");
    onProgress("PostgreSQL operativo", 30);

    createDatabase();
    logBoot("Base de datos de la aplicación verificada.");
    onProgress("Base de datos lista", 35);

  // 2. Python + Backend
  if (!isPythonInstalled()) {
    await downloadPython((msg, pct) => onProgress(msg, 35 + pct * 0.15));
  }
  if (!areDepsInstalled()) {
    await installDeps((msg, pct) => onProgress(msg, 50 + pct * 0.1));
  }

  onProgress("Aplicando migraciones...", 60);
  runMigrations(backendEnv);

  logBoot("Arrancando backend...");
  onProgress("Arrancando backend...", 65);
  startBackend(backendEnv);
  await waitForHTTP(8080, 300000); // 5 min
  logBoot("Backend operativo en puerto 8080.");
  onProgress("Backend operativo", 75);

  // 3. Frontend (el build síncrono ocurre dentro de startFrontend si es necesario)
  logBoot("Iniciando frontend...");
  onProgress("Construyendo frontend...", 78);
  const fp = startFrontend(lanIP);

  fp.stdout.on("data", (data) => {
    const line = data.toString();
    if (line.includes("Ready")) onProgress("Frontend listo", 95);
  });

    await waitForHTTP(3000, 600000); // 10 min por si npm build es lento
    logBoot("Frontend operativo en puerto 3000.");
    onProgress("¡Todo listo!", 100);

    return { lanIP, frontendProcess: fp };
  } catch (err) {
    logBoot(`ERROR FATAL en startAll: ${err.message}\n${err.stack}`);
    throw err;
  }
}

/**
 * Para todos los servicios. Cada paso es independiente para que un fallo
 * no impida parar los demás. Al final, mata cualquier proceso huérfano por puerto.
 */
function stopAll() {
  logBoot("stopAll: parando frontend...");
  try { stopFrontend(); } catch (e) { logBoot(`stopAll: error parando frontend: ${e.message}`); }

  logBoot("stopAll: parando backend...");
  try { stopBackend(); } catch (e) { logBoot(`stopAll: error parando backend: ${e.message}`); }

  logBoot("stopAll: parando PostgreSQL...");
  try { stopPostgres(); } catch (e) { logBoot(`stopAll: error parando PostgreSQL: ${e.message}`); }

  // Fallback nuclear: matar cualquier proceso que siga en los puertos de la app
  logBoot("stopAll: limpieza final de procesos huérfanos...");
  try { killOrphanProcesses(); } catch (e) { logBoot(`stopAll: error en limpieza: ${e.message}`); }

  logBoot("stopAll: completado.");
}

module.exports = {
  startAll,
  stopAll,
  startFrontend,
  stopFrontend,
  waitForHTTP,
  getBackendEnv,
  killOrphanProcesses,
};
