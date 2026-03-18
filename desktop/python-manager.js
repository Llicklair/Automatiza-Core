const { execSync, spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const https = require("https");
const os = require("os");

const { APPDATA_DIR } = require("./postgres-manager");

// Log en Escritorio para diagnóstico de Python/Backend
const PYTHON_LOG_FILE = path.join(os.homedir(), "Desktop", "AutomatizaPyme_BACKEND_LOG.txt");
function logPython(msg) {
  const ts = new Date().toISOString();
  try { fs.appendFileSync(PYTHON_LOG_FILE, `[${ts}] ${msg}\n`); } catch {}
  console.log(`[PYTHON-MGR] ${msg}`);
}

const PYTHON_DIR = path.join(APPDATA_DIR, "python");
const PYTHON_EXE = path.join(PYTHON_DIR, "python.exe");
const SITE_PACKAGES = path.join(PYTHON_DIR, "Lib", "site-packages");
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
const BACKEND_DIR = path.join(PROJECT_ROOT, "backend");

let backendProcess = null;

/**
 * Verifica si Python embebido está instalado.
 */
function isPythonInstalled() {
  return fs.existsSync(PYTHON_EXE);
}

/**
 * Verifica si las dependencias del backend están instaladas.
 */
function areDepsInstalled() {
  return fs.existsSync(path.join(SITE_PACKAGES, "fastapi"));
}

/**
 * Descarga Python embebido (embed zip de python.org).
 * @param {Function} onProgress
 */
async function downloadPython(onProgress) {
  if (isPythonInstalled()) return;

  fs.mkdirSync(PYTHON_DIR, { recursive: true });

  onProgress("Descargando Python 3.11...", 0);

  const zipUrl =
    "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip";
  const zipPath = path.join(APPDATA_DIR, "python.zip");

  await downloadFile(zipUrl, zipPath, (percent) => {
    onProgress(`Descargando Python... ${percent}%`, percent * 0.5);
  });

  onProgress("Extrayendo Python...", 50);

  execSync(
    `powershell -NoProfile -Command "Expand-Archive -Path '${zipPath}' -DestinationPath '${PYTHON_DIR}' -Force"`,
    { stdio: "pipe", timeout: 120000 }
  );

  // Habilitar pip: modificar python311._pth para habilitar import site
  const pthFiles = fs.readdirSync(PYTHON_DIR).filter((f) => f.endsWith("._pth"));
  for (const pth of pthFiles) {
    const pthPath = path.join(PYTHON_DIR, pth);
    let content = fs.readFileSync(pthPath, "utf8");
    content = content.replace("#import site", "import site");
    // Añadir site-packages al path
    if (!content.includes("Lib\\site-packages")) {
      content += "\nLib\\site-packages\n";
    }
    fs.writeFileSync(pthPath, content);
  }

  // Descargar e instalar pip
  onProgress("Instalando pip...", 60);
  const getPipPath = path.join(PYTHON_DIR, "get-pip.py");
  await downloadFile(
    "https://bootstrap.pypa.io/get-pip.py",
    getPipPath,
    () => {}
  );

  execSync(`"${PYTHON_EXE}" "${getPipPath}"`, {
    cwd: PYTHON_DIR,
    stdio: "pipe",
    timeout: 120000,
    env: { ...process.env, PYTHONPATH: SITE_PACKAGES },
  });

  // Limpiar
  try {
    fs.unlinkSync(zipPath);
    fs.unlinkSync(getPipPath);
  } catch {}

  onProgress("Python instalado", 70);
}

/**
 * Instala las dependencias del backend.
 * @param {Function} onProgress
 */
async function installDeps(onProgress) {
  if (areDepsInstalled()) return;

  onProgress("Instalando dependencias del backend...", 0);
  logPython("Iniciando instalación de dependencias...");

  const pipExe = path.join(PYTHON_DIR, "Scripts", "pip.exe");
  const requirementsPath = path.join(BACKEND_DIR, "requirements.txt");

  if (!fs.existsSync(requirementsPath)) {
    const errMsg = `No se encontró requirements.txt en: ${requirementsPath}. La instalación no puede continuar.`;
    logPython(errMsg);
    throw new Error(errMsg);
  }

  logPython(`Instalando desde requirements.txt: ${requirementsPath}`);
  logPython(`pip: ${pipExe}`);
  logPython(`site-packages: ${SITE_PACKAGES}`);

  try {
    execSync(
      `"${pipExe}" install --target "${SITE_PACKAGES}" -r "${requirementsPath}" --no-warn-script-location`,
      {
        cwd: BACKEND_DIR,
        stdio: "pipe",
        timeout: 600000,
        env: { ...process.env, PYTHONPATH: SITE_PACKAGES },
      }
    );
    logPython("Dependencias instaladas correctamente.");
  } catch (err) {
    const output = (err.stdout || "").toString() + "\n" + (err.stderr || "").toString();
    logPython(`ERROR instalando dependencias:\n${output}`);
    throw new Error(`Fallo al instalar dependencias del backend:\n${output.slice(0, 500)}`);
  }

  onProgress("Dependencias instaladas", 100);
}

/**
 * Arranca el backend (uvicorn).
 * @param {object} env - Variables de entorno adicionales (DATABASE_URL, etc.)
 * @returns {ChildProcess}
 */
function startBackend(extraEnv = {}) {
  const env = {
    ...process.env,
    PYTHONPATH: `${BACKEND_DIR};${SITE_PACKAGES}`,
    ...extraEnv,
  };

  // Eliminar ELECTRON_RUN_AS_NODE para que no afecte a subprocesos
  delete env.ELECTRON_RUN_AS_NODE;

  logPython(`Arrancando uvicorn...`);
  logPython(`PYTHON_EXE: ${PYTHON_EXE}`);
  logPython(`BACKEND_DIR: ${BACKEND_DIR}`);
  logPython(`DATABASE_URL: ${extraEnv.DATABASE_URL || "(no definida)"}`);

  // Embedded Python ignora PYTHONPATH (lo controla el fichero ._pth).
  // Inyectamos el backend dir en sys.path via -c para que encuentre 'app'.
  const launcherCode = [
    "import sys, os",
    "sys.path.insert(0, os.getcwd())",
    "import uvicorn",
    "uvicorn.run('app.main:app', host='0.0.0.0', port=8080, log_level='info')",
  ].join("; ");

  backendProcess = spawn(
    PYTHON_EXE,
    ["-c", launcherCode],
    {
      cwd: BACKEND_DIR,
      env,
      stdio: "pipe",
    }
  );

  backendProcess.stdout.on("data", (data) => {
    const text = data.toString();
    logPython(`[STDOUT] ${text.trim()}`);
    process.stdout.write(`[BACKEND STDOUT] ${text}`);
  });

  backendProcess.stderr.on("data", (data) => {
    const text = data.toString();
    logPython(`[STDERR] ${text.trim()}`);
    process.stderr.write(`[BACKEND STDERR] ${text}`);
  });

  backendProcess.on("error", (err) => {
    logPython(`[PROCESS ERROR] ${err.message}`);
  });

  backendProcess.on("close", (code) => {
    logPython(`[PROCESS CLOSE] Backend salió con código ${code}`);
  });

  return backendProcess;
}

/**
 * Para el backend.
 */
function stopBackend() {
  if (!backendProcess) return;
  try {
    if (process.platform === "win32") {
      execSync(`taskkill /PID ${backendProcess.pid} /T /F`, { stdio: "ignore" });
    } else {
      backendProcess.kill("SIGTERM");
    }
  } catch {
    // Ya muerto
  }
  backendProcess = null;
}

/**
 * Ejecuta migraciones Alembic.
 */
function runMigrations(extraEnv = {}) {
  const env = {
    ...process.env,
    PYTHONPATH: `${BACKEND_DIR};${SITE_PACKAGES}`,
    ...extraEnv,
  };
  delete env.ELECTRON_RUN_AS_NODE;

  // Embedded Python ignora PYTHONPATH — inyectar sys.path via -c.
  // Estrategia: si la BD está vacía (fresh install), crear tablas desde modelos
  // y stampar alembic a head. Si ya tiene tablas, usar alembic upgrade normal.
  const migrationScript = path.join(BACKEND_DIR, "_desktop_migrate.py");
  const scriptContent = `
import sys, os
sys.path.insert(0, os.getcwd())
db_url = os.environ["DATABASE_URL"]
sync_url = db_url.replace("+asyncpg", "")

from sqlalchemy import create_engine, inspect, text
engine = create_engine(sync_url)

inspector = inspect(engine)
tables = inspector.get_table_names()

if "alembic_version" not in tables:
    print("[MIGRATE] Fresh DB — creando tablas desde modelos...")
    from app.db.models import models  # importa todos los modelos
    from app.db.base import Base
    Base.metadata.create_all(engine)
    # Crear extension vector si disponible
    with engine.connect() as conn:
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        except Exception:
            pass
    from alembic.config import Config
    from alembic import command
    c = Config("alembic.ini")
    command.stamp(c, "head")
    print("[MIGRATE] Tablas creadas y alembic stamped a head.")
else:
    print("[MIGRATE] BD existente — ejecutando alembic upgrade head...")
    from alembic.config import Config
    from alembic import command
    c = Config("alembic.ini")
    command.upgrade(c, "head")
    print("[MIGRATE] Migraciones aplicadas.")
`;
  try {
    fs.writeFileSync(migrationScript, scriptContent);
    execSync(`"${PYTHON_EXE}" "${migrationScript}"`, {
      cwd: BACKEND_DIR,
      env,
      stdio: "inherit",
      timeout: 120000,
    });
    logPython("Migraciones aplicadas correctamente.");
    return true;
  } catch (err) {
    logPython(`Error en migraciones: ${err.message}`);
    console.error(`Error en migraciones: ${err.message}`);
    return false;
  } finally {
    try { fs.unlinkSync(migrationScript); } catch {}
  }
}

/**
 * Descarga un archivo con callback de progreso.
 */
function downloadFile(url, dest, onProgress) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);

    const request = (reqUrl) => {
      const mod = reqUrl.startsWith("https") ? https : require("http");
      mod.get(reqUrl, (res) => {
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          request(res.headers.location);
          return;
        }
        const total = parseInt(res.headers["content-length"], 10) || 0;
        let downloaded = 0;
        res.on("data", (chunk) => {
          downloaded += chunk.length;
          if (total > 0) onProgress(Math.round((downloaded / total) * 100));
        });
        res.pipe(file);
        file.on("finish", () => file.close(resolve));
      }).on("error", (err) => {
        try { fs.unlinkSync(dest); } catch {}
        reject(err);
      });
    };

    request(url);
  });
}

module.exports = {
  isPythonInstalled,
  areDepsInstalled,
  downloadPython,
  installDeps,
  startBackend,
  stopBackend,
  runMigrations,
  PYTHON_EXE,
  BACKEND_DIR,
};
