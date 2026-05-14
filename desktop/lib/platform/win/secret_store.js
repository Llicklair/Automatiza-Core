/**
 * SecretStore — almacenamiento cifrado de credenciales (DIS.IFACE).
 *
 * Contrato:
 *   async get(key: string): Promise<string | null>
 *   async set(key: string, value: string): Promise<boolean>
 *   async remove(key: string): Promise<boolean>
 *   async isAvailable(): Promise<boolean>
 *
 * Windows (esta implementación): usa `safeStorage` de Electron (DPAPI) +
 * persistencia en `%APPDATA%/AutomatizaPyme/secure/<key>.dat`. Whitelist de
 * keys ya enforced en `main.js` (SEC.JWT) y `service-manager.js` (SEC.KEY) —
 * este módulo solo expone el contrato sin acoplar a casos de uso concretos.
 *
 * TODO_macos: Keychain Services API (security framework) via `@napi-rs/keyring`
 * o IPC a `security add-generic-password`. Misma firma de método.
 *
 * TODO_linux: libsecret via `@napi-rs/keyring` (GNOME Keyring / KWallet). Misma firma.
 */

const fs = require("fs");
const path = require("path");

function _securePath(appDir, key) {
  return path.join(appDir, "secure", `${key}.dat`);
}

async function isAvailable() {
  try {
    const { safeStorage } = require("electron");
    return safeStorage.isEncryptionAvailable();
  } catch {
    return false;
  }
}

async function get(key, opts = {}) {
  try {
    const { safeStorage, app } = require("electron");
    if (!safeStorage.isEncryptionAvailable()) return null;
    const appDir = opts.appDir || app.getPath("userData");
    const filePath = _securePath(appDir, key);
    if (!fs.existsSync(filePath)) return null;
    const buffer = fs.readFileSync(filePath);
    return safeStorage.decryptString(buffer);
  } catch {
    return null;
  }
}

async function set(key, value, opts = {}) {
  try {
    const { safeStorage, app } = require("electron");
    if (!safeStorage.isEncryptionAvailable()) return false;
    const appDir = opts.appDir || app.getPath("userData");
    const filePath = _securePath(appDir, key);
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    const encrypted = safeStorage.encryptString(String(value));
    fs.writeFileSync(filePath, encrypted);
    return true;
  } catch {
    return false;
  }
}

async function remove(key, opts = {}) {
  try {
    const { app } = require("electron");
    const appDir = opts.appDir || app.getPath("userData");
    const filePath = _securePath(appDir, key);
    if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
    return true;
  } catch {
    return false;
  }
}

module.exports = { get, set, remove, isAvailable };
