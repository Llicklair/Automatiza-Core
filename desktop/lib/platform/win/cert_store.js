/**
 * CertStore — almacenamiento de certificados de AutomatizaPyme S.L. (DIS.IFACE).
 *
 * Contrato:
 *   async getRepresentationCert(): Promise<{cert: Buffer, password: string} | null>
 *   async setRepresentationCert(cert: Buffer, password: string): Promise<boolean>
 *   async hasRepresentationCert(): Promise<boolean>
 *
 * **Restricción crítica** (consenso Ronda 8 A.19): este store es SOLO para
 * el cert de representación de la propia AutomatizaPyme S.L. (Verifactu
 * sello, FACe, alta colaborador social AEAT). **NUNCA debe almacenar el
 * cert personal FNMT del cliente** — eso es anti-patrón legal (Ronda 25 T1).
 *
 * Windows (esta implementación): cifra el bundle PKCS#12 con `safeStorage`
 * (DPAPI) y lo persiste en `%APPDATA%/AutomatizaPyme/certs/representation.p12.dat`.
 * El password también va cifrado en `representation.pwd.dat`.
 *
 * TODO_macos: Keychain Access tiene API nativa para certs; alternativa
 * `security import` via shell con prompt al usuario. Mantener cifrado en disco.
 *
 * TODO_linux: gnome-keyring si disponible; fallback a archivo cifrado con
 * libsecret. Permisos de archivo 0600.
 */

const fs = require("fs");
const path = require("path");

const CERT_NAME = "representation.p12.dat";
const PWD_NAME = "representation.pwd.dat";

function _certDir() {
  const { app } = require("electron");
  return path.join(app.getPath("userData"), "certs");
}

async function hasRepresentationCert() {
  try {
    return fs.existsSync(path.join(_certDir(), CERT_NAME));
  } catch {
    return false;
  }
}

async function getRepresentationCert() {
  try {
    const { safeStorage } = require("electron");
    if (!safeStorage.isEncryptionAvailable()) return null;
    const dir = _certDir();
    const certPath = path.join(dir, CERT_NAME);
    const pwdPath = path.join(dir, PWD_NAME);
    if (!fs.existsSync(certPath) || !fs.existsSync(pwdPath)) return null;
    const certEncrypted = fs.readFileSync(certPath);
    const pwdEncrypted = fs.readFileSync(pwdPath);
    // Para el cert (binario) usamos encryptString → encryptString espera
    // string. Codificamos en base64 para el storage cifrado.
    const certBase64 = safeStorage.decryptString(certEncrypted);
    const password = safeStorage.decryptString(pwdEncrypted);
    return {
      cert: Buffer.from(certBase64, "base64"),
      password,
    };
  } catch {
    return null;
  }
}

async function setRepresentationCert(certBuffer, password) {
  try {
    const { safeStorage } = require("electron");
    if (!safeStorage.isEncryptionAvailable()) return false;
    const dir = _certDir();
    fs.mkdirSync(dir, { recursive: true });
    const certBase64 = Buffer.from(certBuffer).toString("base64");
    fs.writeFileSync(path.join(dir, CERT_NAME), safeStorage.encryptString(certBase64));
    fs.writeFileSync(path.join(dir, PWD_NAME), safeStorage.encryptString(String(password)));
    return true;
  } catch {
    return false;
  }
}

module.exports = { hasRepresentationCert, getRepresentationCert, setRepresentationCert };
