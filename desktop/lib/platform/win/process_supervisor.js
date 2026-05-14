/**
 * ProcessSupervisor — control de procesos del backend Postgres/Python (DIS.IFACE).
 *
 * Contrato:
 *   spawn(command: string, args: string[], options: object): ChildProcess
 *   async kill(pid: number, force?: boolean): Promise<void>
 *   async isRunning(pid: number): Promise<boolean>
 *
 * Windows (esta implementación): usa `taskkill /T /F` para terminar árboles
 * de procesos. Heredados de `service-manager.js` y `python-manager.js` —
 * esta capa abstrae para que macOS/Linux puedan usar SIGTERM/SIGKILL nativos.
 *
 * TODO_macos: `kill -TERM <pid>` con escalado a `kill -9` si no responde en 5s.
 * Para árboles de procesos: `pkill -P <pid>` (descendientes directos) +
 * recurse manual si fuera necesario.
 *
 * TODO_linux: igual que macOS, usando `kill` y `pkill` estándares POSIX.
 */

const { execSync, spawn } = require("child_process");

function spawnProcess(command, args, options = {}) {
  return spawn(command, args, options);
}

async function kill(pid, force = false) {
  if (!pid) return;
  try {
    const flags = force ? "/F /T" : "/T";
    execSync(`taskkill /PID ${pid} ${flags}`, { stdio: "ignore" });
  } catch {
    // Proceso ya muerto o sin permisos — no propagamos error
  }
}

async function isRunning(pid) {
  if (!pid) return false;
  try {
    const output = execSync(`tasklist /FI "PID eq ${pid}" /NH`, { stdio: "pipe" }).toString();
    return output.includes(String(pid));
  } catch {
    return false;
  }
}

module.exports = { spawn: spawnProcess, kill, isRunning };
