/**
 * Gestor de Java JRE portable — descarga auto en primera ejecución.
 * Patrón idéntico a postgres-manager.js y python-manager.js.
 * Usa Eclipse Adoptium (Temurin) JRE 21 LTS mínimo para Windows x64.
 */
const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const http = require("http");
const https = require("https");

const APPDATA_DIR = path.join(
  process.env.APPDATA || path.join(require("os").homedir(), "AppData", "Roaming"),
  "AutomatizaPyme"
);

const DEBUG_LOG = path.join(APPDATA_DIR, "app_debug.log");

function logDebug(msg) {
  const timestamp = new Date().toISOString();
  try {
    if (!fs.existsSync(APPDATA_DIR)) fs.mkdirSync(APPDATA_DIR, { recursive: true });
    fs.appendFileSync(DEBUG_LOG, `[${timestamp}] [jre-manager] ${msg}\n`);
  } catch {}
  console.log(msg);
}

const JRE_DIR = path.join(APPDATA_DIR, "jre");
const JAVA_EXE = path.join(JRE_DIR, "bin", "java.exe");

/**
 * Verifica si Java JRE portable ya está descargado.
 */
function isJREInstalled() {
  return fs.existsSync(JAVA_EXE);
}

/**
 * Devuelve la ruta al ejecutable java.exe.
 * Prioridad: JRE portable > Java del sistema > null.
 */
function getJavaPath() {
  if (fs.existsSync(JAVA_EXE)) return JAVA_EXE;

  // Probar Java del sistema
  try {
    const { execSync } = require("child_process");
    const output = execSync("java -version 2>&1", { stdio: "pipe", timeout: 5000 }).toString();
    if (output.includes("version")) return "java";
  } catch {}

  return null;
}

/**
 * Descarga y extrae Eclipse Adoptium JRE 21 LTS portable.
 * @param {Function} onProgress - Callback (message, percent)
 */
async function downloadJRE(onProgress) {
  if (isJREInstalled()) return;

  fs.mkdirSync(APPDATA_DIR, { recursive: true });

  onProgress("Descargando Java JRE 21...", 0);

  // Eclipse Adoptium Temurin JRE 21 LTS — Windows x64
  const zipUrl =
    "https://api.adoptium.net/v3/binary/latest/21/ga/windows/x64/jre/hotspot/normal/eclipse?project=jdk";
  const zipPath = path.join(APPDATA_DIR, "jre.zip");

  await downloadFile(zipUrl, zipPath, (percent) => {
    onProgress(`Descargando Java JRE... ${percent}%`, percent * 0.7);
  });

  onProgress("Extrayendo Java JRE...", 70);

  // Extraer con Windows System32\tar.exe (bsdtar, soporta ZIP nativo)
  const winTar = path.join(process.env.SystemRoot || "C:\\Windows", "System32", "tar.exe");
  const tempExtract = path.join(APPDATA_DIR, "jre_temp");
  fs.mkdirSync(tempExtract, { recursive: true });

  await new Promise((resolve, reject) => {
    const child = spawn(
      winTar,
      ["-xf", zipPath, "-C", tempExtract],
      { stdio: "pipe", windowsHide: true }
    );
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`tar exited with code ${code}`));
    });
    child.on("error", reject);
  });

  // Adoptium extrae en subcarpeta tipo "jdk-21.0.x+y-jre" — mover al destino limpio
  const extracted = fs.readdirSync(tempExtract);
  const jreFolder = extracted.find((f) => f.startsWith("jdk-") && f.includes("-jre"));

  if (jreFolder) {
    const src = path.join(tempExtract, jreFolder);
    // Mover contenido a JRE_DIR
    if (fs.existsSync(JRE_DIR)) fs.rmSync(JRE_DIR, { recursive: true, force: true });
    fs.renameSync(src, JRE_DIR);
  } else {
    // Fallback: si la estructura es diferente, mover todo
    if (fs.existsSync(JRE_DIR)) fs.rmSync(JRE_DIR, { recursive: true, force: true });
    fs.renameSync(tempExtract, JRE_DIR);
  }

  // Limpiar
  try { fs.unlinkSync(zipPath); } catch {}
  try { fs.rmSync(tempExtract, { recursive: true, force: true }); } catch {}

  onProgress("Java JRE instalado", 100);
  logDebug(`JRE instalado en ${JRE_DIR}`);
}

/**
 * Descarga un archivo con progreso y soporte de redirects.
 */
function downloadFile(url, dest, onProgress) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest);

    const request = (reqUrl) => {
      const protocol = reqUrl.startsWith("https") ? https : http;
      protocol.get(reqUrl, (res) => {
        // Seguir redirects
        if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
          res.resume();
          request(res.headers.location);
          return;
        }

        if (res.statusCode !== 200) {
          res.resume();
          reject(new Error(`HTTP ${res.statusCode} descargando JRE`));
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
        try { fs.unlinkSync(dest); } catch {}
        reject(err);
      });
    };

    request(url);
  });
}

module.exports = {
  isJREInstalled,
  getJavaPath,
  downloadJRE,
  JRE_DIR,
  JAVA_EXE,
};
