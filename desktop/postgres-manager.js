const { execSync, spawn, execFile } = require("child_process");
const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");
const net = require("net");

// PostgreSQL portable se descarga en primera ejecución
const APPDATA_DIR = path.join(
  process.env.APPDATA || path.join(require("os").homedir(), "AppData", "Roaming"),
  "AutomatizaPyme"
);

const DEBUG_LOG = path.join(APPDATA_DIR, "app_debug.log");

function logDebug(msg) {
  const timestamp = new Date().toISOString();
  try {
    if (!fs.existsSync(APPDATA_DIR)) fs.mkdirSync(APPDATA_DIR, { recursive: true });
    fs.appendFileSync(DEBUG_LOG, `[${timestamp}] ${msg}\n`);
  } catch {}
  console.log(msg);
}
const PG_DIR = path.join(APPDATA_DIR, "pgsql");
const PG_BIN = path.join(PG_DIR, "bin");
const PG_DATA = path.join(APPDATA_DIR, "pgdata");
const PG_LOG = path.join(APPDATA_DIR, "postgres.log");
const PG_PORT = "5433"; // Evitar conflicto con PG del sistema

const DB_USER = "pyme_user";
const DB_NAME = "pyme_db";
const DB_PASS = "pyme_pass";

let pgProcess = null;

/**
 * Verifica si PostgreSQL portable ya está descargado.
 */
function isPostgresInstalled() {
  return (
    fs.existsSync(path.join(PG_BIN, "pg_ctl.exe")) &&
    fs.existsSync(path.join(PG_DIR, "share", "postgres.bki"))
  );
}

/**
 * Descarga y extrae PostgreSQL portable (EDB zip).
 * @param {Function} onProgress - Callback (message, percent)
 */
async function downloadPostgres(onProgress) {
  if (isPostgresInstalled()) return;

  fs.mkdirSync(APPDATA_DIR, { recursive: true });

  onProgress("Descargando PostgreSQL 15...", 0);

  // URL del ZIP portable de EDB (PostgreSQL 15 para Windows x64)
  const zipUrl =
    "https://get.enterprisedb.com/postgresql/postgresql-15.10-1-windows-x64-binaries.zip";
  const zipPath = path.join(APPDATA_DIR, "pgsql.zip");

  await downloadFile(zipUrl, zipPath, (percent) => {
    onProgress(`Descargando PostgreSQL... ${percent}%`, percent * 0.7);
  });

  onProgress("Extrayendo PostgreSQL...", 70);

  // Extraer con Windows System32\tar.exe (bsdtar, soporta ZIP nativo)
  // No usar GNU tar (Git bash) ni PowerShell Expand-Archive (lento y congela)
  const winTar = path.join(process.env.SystemRoot || "C:\\Windows", "System32", "tar.exe");
  await new Promise((resolve, reject) => {
    const child = spawn(
      winTar,
      ["-xf", zipPath, "-C", APPDATA_DIR],
      { stdio: "pipe", windowsHide: true }
    );
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`tar exited with code ${code}`));
    });
    child.on("error", reject);
  });

  // Limpiar zip
  try {
    fs.unlinkSync(zipPath);
  } catch {}

  onProgress("PostgreSQL instalado", 100);
}

/**
 * Inicializa el directorio de datos (primera vez).
 */
async function initDatabase() {
  if (fs.existsSync(path.join(PG_DATA, "PG_VERSION"))) return;

  const initdb = path.join(PG_BIN, "initdb.exe");
  await new Promise((resolve, reject) => {
    const child = spawn(
      initdb,
      [`--pgdata=${PG_DATA}`, "--encoding=UTF8", `--username=${DB_USER}`, "--auth=trust"],
      { stdio: "pipe", windowsHide: true }
    );
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`initdb exited with code ${code}`));
    });
    child.on("error", reject);
  });

  // Configurar pg_hba.conf para permitir acceso sin pass localmente (trust)
  const hbaPath = path.join(PG_DATA, "pg_hba.conf");
  let hba = fs.readFileSync(hbaPath, "utf8");
  // Asegurarse de que localhost confíe en las conexiones (trust)
  hba = hba.replace(
    /host\s+all\s+all\s+127\.0\.0\.1\/32\s+md5/g,
    "host    all             all             127.0.0.1/32            trust"
  );
  fs.writeFileSync(hbaPath, hba);

  // Configurar postgresql.conf - puerto custom
  const confPath = path.join(PG_DATA, "postgresql.conf");
  let conf = fs.readFileSync(confPath, "utf8");
  conf = conf.replace(/#port = 5432/, `port = ${PG_PORT}`);
  conf += `\n# AutomatizaPyme config\nshared_buffers = 128MB\nmax_connections = 50\n`;
  fs.writeFileSync(confPath, conf);
}

/**
 * Arranca PostgreSQL.
 */
async function startPostgres() {
  logDebug("Iniciando startPostgres (Blind Start)...");

  // Limpiar postmaster.pid si existe (stale lock para prevenir fallos tontos)
  const pidPath = path.join(PG_DATA, "postmaster.pid");
  if (fs.existsSync(pidPath)) {
    try { fs.unlinkSync(pidPath); } catch {}
  }

  const pgCtl = path.join(PG_BIN, "pg_ctl.exe");
  logDebug(`Lanzando pg_ctl start (ciego) a puerto ${PG_PORT}`);

  await new Promise((resolve) => {
    const child = spawn(
      pgCtl,
      ["start", "-D", PG_DATA, "-l", PG_LOG],
      { stdio: "ignore", windowsHide: true }
    );
    child.on("close", (code) => {
      logDebug(`pg_ctl terminado con codigo ${code}`);
      resolve();
    });
    child.on("error", (err) => {
      logDebug(`Error lanzando pg_ctl: ${err.message}`);
      resolve();
    });
  });
}

/**
 * Para PostgreSQL.
 */
function stopPostgres() {
  const pgCtl = path.join(PG_BIN, "pg_ctl.exe");
  try {
    execSync(`"${pgCtl}" stop -D "${PG_DATA}" -m fast -w -t 15`, {
      stdio: "pipe",
      timeout: 30000,
    });
  } catch {
    // Ya parado
  }
}

/**
 * Verifica si PostgreSQL está corriendo.
 */
/**
 * Verifica si PostgreSQL está aceptando conexiones mediante sockets TCP.
 */
function isPostgresRunning() {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let isFinished = false;

    socket.setTimeout(2000);

    socket.on("connect", () => {
      if (!isFinished) {
        isFinished = true;
        socket.destroy();
        resolve(true);
      }
    });

    socket.on("timeout", () => {
      if (!isFinished) {
        isFinished = true;
        socket.destroy();
        resolve(false);
      }
    });

    socket.on("error", () => {
      if (!isFinished) {
        isFinished = true;
        socket.destroy();
        resolve(false);
      }
    });

    socket.connect(parseInt(PG_PORT), "127.0.0.1");
  });
}

/**
 * Espera a que PostgreSQL acepte conexiones.
 */
async function waitForPostgres(timeoutMs = 60000) {
  logDebug("Esperando a que PostgreSQL responda...");
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    if (await isPostgresRunning()) {
      logDebug("PostgreSQL respondió!");
      return;
    }
    await new Promise(r => setTimeout(r, 2000));
  }

  logDebug("Timeout esperando a PostgreSQL");
  let lastError = "";
  try {
    if (fs.existsSync(PG_LOG)) {
      lastError = "\nÚltimos logs:\n" + fs.readFileSync(PG_LOG, "utf8").split("\n").slice(-5).join("\n");
    }
  } catch {}
  throw new Error(`PostgreSQL no arrancó en ${timeoutMs / 1000}s.${lastError}`);
}

/**
 * Crea la base de datos si no existe.
 */
function createDatabase() {
  const psql = path.join(PG_BIN, "psql.exe");
  try {
    // Verificar si la BD existe
    const result = execSync(
      `"${psql}" -p ${PG_PORT} -U ${DB_USER} -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" postgres`,
      { stdio: "pipe", timeout: 10000 }
    ).toString().trim();

    if (!result.includes("1")) {
      execSync(
        `"${psql}" -p ${PG_PORT} -U ${DB_USER} -c "CREATE DATABASE ${DB_NAME}" postgres`,
        { stdio: "pipe", timeout: 10000 }
      );
    }

    // Habilitar pgvector SOLO si el binario de la extensión está instalado.
    // El Postgres portable de la app no incluye pgvector y la búsqueda semántica
    // usa coseno en Python como fallback, así que la extensión es opcional.
    // Comprobamos pg_available_extensions primero para NO ensuciar el log de
    // Postgres con "la extensión «vector» no está disponible" en cada arranque.
    try {
      const vectorAvailable = execSync(
        `"${psql}" -p ${PG_PORT} -U ${DB_USER} -d ${DB_NAME} -tAc "SELECT 1 FROM pg_available_extensions WHERE name = 'vector'"`,
        { stdio: "pipe", timeout: 10000 }
      )
        .toString()
        .trim();
      if (vectorAvailable === "1") {
        execSync(
          `"${psql}" -p ${PG_PORT} -U ${DB_USER} -d ${DB_NAME} -c "CREATE EXTENSION IF NOT EXISTS vector"`,
          { stdio: "pipe", timeout: 10000 }
        );
      }
    } catch {
      // pgvector no disponible — continuar sin él
    }
  } catch (err) {
    // BD puede que ya exista
  }
}

/**
 * Devuelve la DATABASE_URL para el backend.
 */
function getDatabaseURL() {
  return `postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:${PG_PORT}/${DB_NAME}`;
}

/**
 * Descarga un archivo con progreso.
 */
function downloadFile(url, dest, onProgress) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);
    const protocol = url.startsWith("https") ? https : http;

    const request = (reqUrl) => {
      protocol.get(reqUrl, (res) => {
        // Seguir redirects
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          request(res.headers.location);
          return;
        }

        const total = parseInt(res.headers["content-length"], 10) || 0;
        let downloaded = 0;

        res.on("data", (chunk) => {
          downloaded += chunk.length;
          if (total > 0) {
            onProgress(Math.round((downloaded / total) * 100));
          }
        });

        res.pipe(file);
        file.on("finish", () => {
          file.close(resolve);
        });
      }).on("error", (err) => {
        fs.unlinkSync(dest);
        reject(err);
      });
    };

    request(url);
  });
}

module.exports = {
  isPostgresInstalled,
  downloadPostgres,
  initDatabase,
  startPostgres,
  stopPostgres,
  isPostgresRunning,
  waitForPostgres,
  createDatabase,
  getDatabaseURL,
  PG_PORT,
  APPDATA_DIR,
};
