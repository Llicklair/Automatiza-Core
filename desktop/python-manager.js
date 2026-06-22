const { execSync, spawn, spawnSync } = require("child_process");
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
let IS_PACKAGED = false; // módulo-scope: usado también en startBackend()
try {
  const { app } = require("electron");
  IS_PACKAGED = !!(app && app.isPackaged);
  PROJECT_ROOT = IS_PACKAGED
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

const DEPS_HASH_FILE = path.join(APPDATA_DIR, "deps_requirements.hash");

/**
 * Verifica si las dependencias del backend están instaladas Y están actualizadas
 * respecto al requirements.txt actual (compara hash del archivo).
 */
function areDepsInstalled() {
  if (!fs.existsSync(path.join(SITE_PACKAGES, "fastapi"))) return false;
  // Si no existe el archivo de hash, forzar reinstalación
  if (!fs.existsSync(DEPS_HASH_FILE)) return false;
  try {
    const requirementsPath = path.join(BACKEND_DIR, "requirements.txt");
    if (!fs.existsSync(requirementsPath)) return true; // sin requirements, no reinstalar
    const crypto = require("crypto");
    const currentHash = crypto.createHash("md5").update(fs.readFileSync(requirementsPath)).digest("hex");
    const savedHash = fs.readFileSync(DEPS_HASH_FILE, "utf8").trim();
    return currentHash === savedHash;
  } catch {
    return false;
  }
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
 * @param {Function} onProgress - (message, percent)
 */
async function installDeps(onProgress) {
  if (areDepsInstalled()) return;

  onProgress("Instalando dependencias del backend (puede tardar varios minutos)...", 0);
  logPython("Iniciando instalación de dependencias...");

  const pipExe = path.join(PYTHON_DIR, "Scripts", "pip.exe");
  const requirementsPath = path.join(BACKEND_DIR, "requirements.txt");

  if (!fs.existsSync(requirementsPath)) {
    throw new Error(`No se encontró requirements.txt en: ${requirementsPath}.`);
  }

  // Si pip no existe (instalación previa incompleta), reinstalarlo
  if (!fs.existsSync(pipExe)) {
    logPython("pip.exe no encontrado — reinstalando pip...");
    onProgress("Reparando instalación de Python (pip)...", 5);
    const getPipPath = path.join(PYTHON_DIR, "get-pip.py");
    await downloadFile("https://bootstrap.pypa.io/get-pip.py", getPipPath, () => {});
    execSync(`"${PYTHON_EXE}" "${getPipPath}"`, {
      cwd: PYTHON_DIR,
      stdio: "pipe",
      timeout: 120000,
      env: { ...process.env, PYTHONPATH: SITE_PACKAGES },
    });
    try { fs.unlinkSync(getPipPath); } catch {}
    if (!fs.existsSync(pipExe)) {
      throw new Error(`No se pudo instalar pip. Revisa AutomatizaPyme_BACKEND_LOG.txt en tu Escritorio.`);
    }
    logPython("pip reinstalado correctamente.");
  }

  logPython(`Instalando desde: ${requirementsPath}`);

  await new Promise((resolve, reject) => {
    const pip = spawn(
      pipExe,
      ["install", "--target", SITE_PACKAGES, "-r", requirementsPath, "--no-warn-script-location"],
      {
        cwd: BACKEND_DIR,
        env: { ...process.env, PYTHONPATH: SITE_PACKAGES },
        stdio: "pipe",
      }
    );

    let pkgCount = 0;
    let installing = false;
    let heartbeatSec = 0;

    // Heartbeat cada 5s durante la fase silenciosa de copia de archivos
    const heartbeat = setInterval(() => {
      if (!installing) return;
      heartbeatSec += 5;
      const mins = Math.floor(heartbeatSec / 60);
      const secs = heartbeatSec % 60;
      const elapsed = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
      onProgress(`Copiando archivos... (${elapsed} — esto puede tardar varios minutos)`, 92);
    }, 5000);

    pip.stdout.on("data", (data) => {
      const text = data.toString();
      logPython(`[pip] ${text.trim()}`);

      if (text.includes("Installing collected packages")) {
        installing = true;
        heartbeatSec = 0;
        onProgress("Copiando archivos al sistema (fase lenta, por favor espera)...", 91);
        return;
      }
      if (!installing) {
        const match = text.match(/Collecting ([^\s]+)/);
        if (match) {
          pkgCount++;
          const pct = Math.min(5 + Math.round((pkgCount / 80) * 85), 90);
          onProgress(`Descargando ${match[1]}...`, pct);
        }
      }
    });
    pip.stderr.on("data", (data) => logPython(`[pip stderr] ${data.toString().trim()}`));

    pip.on("error", (err) => { clearInterval(heartbeat); reject(new Error(`No se pudo lanzar pip: ${err.message}`)); });
    pip.on("close", (code) => {
      clearInterval(heartbeat);
      if (code === 0) resolve();
      else reject(new Error(`pip salió con código ${code}. Revisa AutomatizaPyme_BACKEND_LOG.txt en tu Escritorio.`));
    });
  });

  // Guardar hash de requirements.txt para detectar cambios futuros
  try {
    const crypto = require("crypto");
    const hash = crypto.createHash("md5").update(fs.readFileSync(requirementsPath)).digest("hex");
    fs.writeFileSync(DEPS_HASH_FILE, hash);
  } catch {}

  logPython("Dependencias instaladas correctamente.");
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
    PYTHONIOENCODING: "utf-8",
    PYTHONUTF8: "1",
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
  // _BACKEND_HOST permite toggle solo-local vs LAN vía IPC (Electron).
  const backendHost = extraEnv._BACKEND_HOST || "0.0.0.0";
  delete env._BACKEND_HOST;

  const launcherCode = [
    "import sys, os",
    "sys.path.insert(0, os.getcwd())",
    "import uvicorn",
    `uvicorn.run('app.main:app', host='${backendHost}', port=8080, log_level='info')`,
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
 * Pide al backend un apagado grácil (drena scheduler + tasks en vuelo) antes
 * del force-kill. Bloqueante con timeout corto: el lifespan de uvicorn nunca
 * corre porque luego hacemos `taskkill /F`, así que este POST es la única vía
 * para dejar el scheduler limpio. Best-effort: cualquier error se ignora.
 *
 * Se ejecuta en un subproceso Node (electron-as-node) para poder bloquear de
 * forma síncrona dentro de stopBackend(), que se invoca desde los handlers de
 * cierre (before-quit, SIGTERM…) donde no se puede await.
 */
function requestGracefulShutdown() {
  const script =
    "const http=require('http');" +
    "const req=http.request({host:'127.0.0.1',port:8080,path:'/lifecycle/shutdown',method:'POST',timeout:3000}," +
    "r=>{r.resume();r.on('end',()=>process.exit(0));});" +
    "req.on('error',()=>process.exit(0));" +
    "req.on('timeout',()=>{req.destroy();process.exit(0);});" +
    "req.end();";
  try {
    // spawnSync con args (sin shell) evita el quoting de cmd.exe sobre el
    // script (que contiene '=>' y otros caracteres especiales).
    spawnSync(process.execPath, ["-e", script], {
      timeout: 4000,
      stdio: "ignore",
      env: { ...process.env, ELECTRON_RUN_AS_NODE: "1" },
    });
  } catch {
    // Timeout o backend ya caído: seguimos al force-kill.
  }
}

/**
 * Para el backend.
 */
function stopBackend() {
  if (!backendProcess) return;
  requestGracefulShutdown();
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
    # Los IDs de revisión descriptivos superan los 32 chars por defecto de
    # alembic_version.version_num (p.ej. 0032_employee_memory_and_rag_scope = 34).
    # Sin esto, el upgrade paso a paso falla con StringDataRightTruncation.
    with engine.connect() as conn:
        try:
            conn.execute(text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE varchar(128)"
            ))
            conn.commit()
        except Exception as e:
            print(f"[MIGRATE] No se pudo ensanchar version_num: {e}")
    c = Config("alembic.ini")
    try:
        command.upgrade(c, "head")
        print("[MIGRATE] Migraciones aplicadas.")
    except Exception as e:
        # Auto-recuperación ante drift (p.ej. BD inicializada con create_all +
        # stamp a un head antiguo: algunas tablas ya existen). create_all crea
        # solo las tablas que faltan; luego re-sincronizamos alembic a head.
        print(f"[MIGRATE] upgrade falló ({e}); reconciliando con create_all...")
        from app.db.models import models  # noqa: F401 — registra los modelos
        from app.db.base import Base
        Base.metadata.create_all(engine)
        command.stamp(c, "head")
        print("[MIGRATE] BD reconciliada y stamped a head.")

# SEC.RLS — rol de aplicación no-superusuario (pyme_app) + policies RLS.
# Idempotente y a nivel TOP (fuera del if/else) para cubrir TAMBIÉN la rama
# "fresh" (create_all + stamp), que NO ejecuta los upgrade() de las migraciones
# y por tanto se saltaría la 0016/0060. Corre como admin: en migraciones
# DATABASE_URL apunta al rol pyme_user (superusuario).
from app.db.security_bootstrap import ensure_security_objects
with engine.begin() as _sec_conn:
    ensure_security_objects(_sec_conn)
print("[MIGRATE] SEC.RLS: rol pyme_app y policies aseguradas.")
`;
  try {
    fs.writeFileSync(migrationScript, scriptContent);
    // stdout heredado para ver el progreso en vivo; stderr a 'pipe' para PODER
    // capturar el traceback de Python si falla. Antes (stdio "inherit") el error
    // se perdía: era la causa de que un `alembic upgrade` abortado quedara
    // invisible y la BD se atascara sin avisar (ver lessons.md 2026-05-20).
    execSync(`"${PYTHON_EXE}" "${migrationScript}"`, {
      cwd: BACKEND_DIR,
      env,
      stdio: ["inherit", "inherit", "pipe"],
      timeout: 120000,
    });
    logPython("Migraciones aplicadas correctamente.");
    return { ok: true, error: null };
  } catch (err) {
    const stderr = err.stderr ? err.stderr.toString() : "";
    const detail = (stderr.trim() || err.message || "Error desconocido").slice(-3000);
    logPython(`Error en migraciones: ${detail}`);
    console.error(`Error en migraciones: ${detail}`);
    return { ok: false, error: detail };
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
