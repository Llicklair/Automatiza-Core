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

let frontendProcess = null;

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
  };
}

/**
 * Arranca Next.js (frontend).
 * Solo reconstruye si .next no existe o la API URL cambió.
 */
function startFrontend(lanIP) {
  const isWin = process.platform === "win32";
  const apiUrl = `http://${lanIP}:8080`;
  const nextDir = path.join(FRONTEND_DIR, ".next");
  const urlMarker = path.join(FRONTEND_DIR, ".next", ".api_url");

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

  const cmd = needsBuild
    ? `npm.cmd run build && npm.cmd start -- -H 0.0.0.0`
    : `npm.cmd start -- -H 0.0.0.0`;

  logBoot(`Frontend: needsBuild=${needsBuild}, cmd=${needsBuild ? "build+start" : "start only"}`);

  frontendProcess = spawn(
    isWin ? "cmd.exe" : "sh",
    isWin ? ["/c", cmd] : ["-c", cmd.replace(/npm\.cmd/g, "npm")],
    {
      cwd: FRONTEND_DIR,
      env: {
        ...process.env,
        NEXT_PUBLIC_API_URL: apiUrl,
        PORT: "3000",
      },
      stdio: "pipe",
    }
  );

  frontendProcess.stderr.on("data", (data) => {
    logBoot(`[FRONTEND STDERR] ${data.toString().trim()}`);
  });

  frontendProcess.on("error", (err) => {
    logBoot(`[FRONTEND ERROR] ${err.message}`);
  });

  frontendProcess.on("close", (code) => {
    logBoot(`[FRONTEND CLOSE] código ${code}`);
  });

  // Guardar marcador de API URL tras build exitoso
  if (needsBuild) {
    frontendProcess.stdout.on("data", (data) => {
      const line = data.toString();
      if (line.includes("Ready") || line.includes("started server")) {
        try { fs.writeFileSync(urlMarker, apiUrl); } catch {}
      }
    });
  }

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

  // 3. Frontend
  logBoot("Iniciando frontend...");
  onProgress("Arrancando frontend...", 78);
  const fp = startFrontend(lanIP);

  fp.stdout.on("data", (data) => {
    const line = data.toString();
    logBoot(`[FRONTEND STDOUT] ${line.trim()}`);
    if (line.includes("Compiling")) onProgress("Compilando páginas...", 82);
    if (line.includes("Compiled")) onProgress("Compilación completada", 90);
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
 * Para todos los servicios.
 */
function stopAll() {
  stopFrontend();
  stopBackend();
  stopPostgres();
}

module.exports = {
  startAll,
  stopAll,
  startFrontend,
  stopFrontend,
  waitForHTTP,
  getBackendEnv,
};
