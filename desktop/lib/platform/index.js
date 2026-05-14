/**
 * DIS.IFACE — Abstracciones de plataforma para preparar macOS Q4-2026.
 *
 * Las 5 interfaces (`SecretStore`, `BackupStore`, `ProcessSupervisor`,
 * `CertStore`, `PathProvider`) tienen una implementación Windows concreta
 * en este sprint y un contrato documentado con `TODO_macos` para futuras
 * implementaciones nativas. El consenso (Ronda 8 A.19) acordó que crear
 * estas interfaces ahora ahorra 3 semanas de migración a macOS.
 *
 * Patrón: cada interface es un objeto con métodos asíncronos. El consumidor
 * usa el módulo `platform` y nunca importa directamente la implementación.
 */

const os = require("os");

const winSecretStore = require("./win/secret_store");
const winBackupStore = require("./win/backup_store");
const winProcessSupervisor = require("./win/process_supervisor");
const winCertStore = require("./win/cert_store");
const winPathProvider = require("./win/path_provider");

const isWindows = process.platform === "win32";
const isMac = process.platform === "darwin";
const isLinux = process.platform === "linux";

/**
 * Devuelve la implementación de plataforma activa.
 * En MVP solo Windows está soportado. macOS y Linux lanzan error explícito.
 */
function platformImpls() {
  if (isWindows) {
    return {
      secretStore: winSecretStore,
      backupStore: winBackupStore,
      processSupervisor: winProcessSupervisor,
      certStore: winCertStore,
      pathProvider: winPathProvider,
    };
  }
  if (isMac) {
    throw new Error(
      "macOS no soportado en v1 (roadmap público Q4-2026). " +
      "Las interfaces existen — falta implementar versión nativa."
    );
  }
  if (isLinux) {
    throw new Error(
      "Linux solo bajo contrato enterprise. Las interfaces existen — " +
      "falta implementar versión nativa."
    );
  }
  throw new Error(`Plataforma no soportada: ${process.platform}`);
}

module.exports = {
  isWindows,
  isMac,
  isLinux,
  platformImpls,
};
