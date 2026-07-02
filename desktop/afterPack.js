/**
 * afterPack — compila el backend a bytecode y borra el fuente en la copia
 * EMPAQUETADA (nunca en el repo). Sube el coste de "editar una línea de
 * license.py para saltarse la licencia": ya no hay .py que editar, solo .pyc.
 *
 * No es inviolable (el .pyc es descompilable), pero elimina el bypass trivial.
 *
 * Se salta app/db/migrations/: Alembic lee las migraciones como *.py por RUTA
 * (no por import), y el arranque hace `alembic upgrade head` en BDs existentes;
 * borrar esos .py rompería las migraciones. Las migraciones son DDL, no IP.
 *
 * El bytecode 3.11 es estable entre micro-versiones, así que compilar con el
 * Python 3.11 del sistema produce .pyc que el intérprete embebido 3.11.9 importa.
 */
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const KEEP_PY_UNDER = path.join("db", "migrations"); // relativo a app/

function findPython311() {
  const candidates = ["python", "python3", "py"];
  for (const exe of candidates) {
    try {
      const args = exe === "py" ? ["-3.11", "--version"] : ["--version"];
      const out = execFileSync(exe, args, { encoding: "utf8" }).trim();
      if (/Python 3\.11\./.test(out)) return { exe, prefix: exe === "py" ? ["-3.11"] : [] };
    } catch (_) {
      /* siguiente candidato */
    }
  }
  return null;
}

function walk(dir, cb) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(full, cb);
    else cb(full);
  }
}

exports.default = async function afterPack(context) {
  const appDir = path.join(
    context.appOutDir,
    "resources",
    "project",
    "backend",
    "app"
  );
  if (!fs.existsSync(appDir)) {
    throw new Error(`[afterPack] No existe ${appDir}; ¿cambió el layout de extraResources?`);
  }
  // Salvaguarda: operar SOLO sobre la salida del build, nunca sobre el repo.
  if (!appDir.startsWith(context.appOutDir)) {
    throw new Error(`[afterPack] Ruta fuera del build: ${appDir}`);
  }

  const py = findPython311();
  if (!py) {
    // Fallar el build en vez de enviar el fuente en claro sin avisar.
    throw new Error(
      "[afterPack] No encontré Python 3.11 para compilar el backend a bytecode. " +
        "Instálalo o quita el hook afterPack si quieres enviar el fuente."
    );
  }

  console.log(`[afterPack] Compilando backend a bytecode con ${py.exe} ${py.prefix.join(" ")}`);
  execFileSync(py.exe, [...py.prefix, "-m", "compileall", "-b", "-q", appDir], {
    stdio: "inherit",
  });

  let deleted = 0;
  let keptMigrations = 0;
  let pyc = 0;
  walk(appDir, (file) => {
    if (file.endsWith(".pyc")) {
      pyc++;
      return;
    }
    if (!file.endsWith(".py")) return;
    const rel = path.relative(appDir, file);
    if (rel.includes(KEEP_PY_UNDER)) {
      keptMigrations++;
      return; // Alembic necesita estos .py
    }
    fs.unlinkSync(file);
    deleted++;
  });

  console.log(
    `[afterPack] Bytecode: ${pyc} .pyc · borrados ${deleted} .py de fuente · ` +
      `conservados ${keptMigrations} .py de migraciones (Alembic)`
  );
  if (deleted === 0) {
    throw new Error("[afterPack] No se borró ningún .py — el stripping no funcionó, abortando.");
  }
};
