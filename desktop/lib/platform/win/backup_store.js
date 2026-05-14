/**
 * BackupStore — gestión de destinos de backup (DIS.IFACE).
 *
 * Contrato:
 *   async listDestinations(): Promise<BackupDestination[]>
 *   async validateDestination(path: string): Promise<{ok: boolean, error?: string}>
 *   async writeBackupFile(destination: string, name: string, data: Buffer): Promise<string>
 *
 * Windows (esta implementación): rutas locales (HDD/SSD), unidades de red
 * mapeadas (`\\server\share`) y unidades USB detectadas. Verificación de
 * permisos mediante `fs.access(W_OK)`.
 *
 * TODO_macos: validar también /Volumes para USB+disks externos, integración
 * opcional con Time Machine API si fuera de utilidad.
 *
 * TODO_linux: mount points en /media o /mnt, validación XDG_DATA_HOME.
 */

const fs = require("fs");
const path = require("path");

async function listDestinations() {
  // En MVP devolvemos solo el path por defecto sugerido. La UI puede
  // ampliar con drives detectados via WMIC en versiones siguientes.
  const home = require("os").homedir();
  return [
    {
      label: "Documentos del usuario",
      path: path.join(home, "Documents", "AutomatizaPyme-Backups"),
      type: "local",
    },
  ];
}

async function validateDestination(targetPath) {
  try {
    fs.mkdirSync(targetPath, { recursive: true });
    fs.accessSync(targetPath, fs.constants.W_OK);
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

async function writeBackupFile(destination, name, data) {
  fs.mkdirSync(destination, { recursive: true });
  const fullPath = path.join(destination, name);
  fs.writeFileSync(fullPath, data);
  return fullPath;
}

module.exports = { listDestinations, validateDestination, writeBackupFile };
