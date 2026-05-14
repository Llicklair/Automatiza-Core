/**
 * PathProvider — rutas canónicas del sistema operativo (DIS.IFACE).
 *
 * Contrato:
 *   appData(): string           // ej. C:\Users\X\AppData\Roaming\AutomatizaPyme
 *   logsDir(): string           // ej. <appData>/logs
 *   secureDir(): string         // ej. <appData>/secure
 *   certsDir(): string          // ej. <appData>/certs
 *   backupsDefault(): string    // ej. C:\Users\X\Documents\AutomatizaPyme-Backups
 *   postgresDataDir(): string   // ej. <appData>/PostgresData/17
 *
 * Windows (esta implementación): se ancla a `%APPDATA%` (Roaming). Esto
 * permite que un usuario que cambia de equipo lleve consigo su configuración
 * vía perfil itinerante en redes empresariales con Active Directory.
 *
 * TODO_macos: `~/Library/Application Support/AutomatizaPyme/` para appData,
 * `~/Library/Logs/AutomatizaPyme/` para logsDir.
 *
 * TODO_linux: respetar XDG Base Directory Specification:
 *   - `${XDG_DATA_HOME:-$HOME/.local/share}/AutomatizaPyme`
 *   - `${XDG_STATE_HOME:-$HOME/.local/state}/AutomatizaPyme/logs`
 */

const os = require("os");
const path = require("path");

function appData() {
  const base = process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming");
  return path.join(base, "AutomatizaPyme");
}

function logsDir() {
  return path.join(appData(), "logs");
}

function secureDir() {
  return path.join(appData(), "secure");
}

function certsDir() {
  return path.join(appData(), "certs");
}

function backupsDefault() {
  return path.join(os.homedir(), "Documents", "AutomatizaPyme-Backups");
}

function postgresDataDir() {
  return path.join(appData(), "PostgresData", "17");
}

module.exports = {
  appData,
  logsDir,
  secureDir,
  certsDir,
  backupsDefault,
  postgresDataDir,
};
