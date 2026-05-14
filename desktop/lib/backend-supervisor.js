/**
 * DIS.SVC — supervisor de proceso backend con auto-restart.
 *
 * Envuelve un `ChildProcess` de Node y lo reinicia automáticamente si
 * cierra con código distinto de 0 cuando no se le pidió parar. El
 * backoff es exponencial con tope para evitar tormentas de restart
 * cuando la causa es persistente (puerto ocupado, BD corrupta, etc.).
 *
 * Diseñado para ejecutarse desde el proceso main de Electron, NO como
 * Windows Service de SCM. La distinción importa: con el tray + el
 * cierre-a-tray ya existente, Electron actúa como "service host" para
 * el backend. Cerrar la ventana no para el backend (close→hide), y
 * salir explícitamente sí lo para (stopAll()).
 *
 * Uso:
 *
 *   const supervisor = createBackendSupervisor({
 *     name: "backend",
 *     spawn: () => spawnUvicorn(env),
 *     onRestart: ({ attempt, exitCode }) => { logBoot(...) },
 *     onGiveUp: () => { dialog.showErrorBox(...) },
 *   });
 *   supervisor.start();
 *   ...
 *   supervisor.stop();  // marca shouldRun=false, mata el proceso, no reinicia
 */

const DEFAULT_BACKOFF_MS = [1000, 2000, 4000, 8000, 16000, 32000];
const DEFAULT_MAX_ATTEMPTS = 6;

function createBackendSupervisor({
  name = "backend",
  spawn,
  onRestart = () => { },
  onGiveUp = () => { },
  backoffMs = DEFAULT_BACKOFF_MS,
  maxAttempts = DEFAULT_MAX_ATTEMPTS,
} = {}) {
  if (typeof spawn !== "function") {
    throw new Error("backend-supervisor: `spawn` debe ser una función que devuelva un ChildProcess");
  }

  let child = null;
  let shouldRun = false;
  let attempt = 0;
  let restartTimer = null;
  let cleanExitMode = false;

  function _attach(proc) {
    proc.on("exit", (code, signal) => {
      // Si la caída es porque le pedimos parar, no reiniciar.
      if (!shouldRun || cleanExitMode) return;

      attempt += 1;
      if (attempt > maxAttempts) {
        onGiveUp({ name, attempts: attempt });
        shouldRun = false;
        return;
      }
      const delay = backoffMs[Math.min(attempt - 1, backoffMs.length - 1)];
      onRestart({ name, attempt, exitCode: code, signal, delayMs: delay });
      restartTimer = setTimeout(() => {
        if (!shouldRun) return;
        try {
          child = spawn();
          _attach(child);
        } catch (err) {
          onRestart({ name, attempt, error: err.message, delayMs: delay });
        }
      }, delay);
    });
  }

  return {
    start() {
      if (shouldRun) return;
      shouldRun = true;
      attempt = 0;
      cleanExitMode = false;
      child = spawn();
      _attach(child);
      return child;
    },

    /**
     * Para el proceso y desactiva el auto-restart.
     * `clean=true` indica que el exit subsiguiente NO debe disparar restart
     * incluso si llega tras un microtask delay.
     */
    stop({ clean = true } = {}) {
      shouldRun = false;
      if (clean) cleanExitMode = true;
      if (restartTimer) {
        clearTimeout(restartTimer);
        restartTimer = null;
      }
      if (child && !child.killed) {
        try { child.kill(); } catch { /* swallow */ }
      }
      child = null;
    },

    /**
     * Resetea el contador de intentos. Útil tras un período largo de
     * estabilidad cuando no queremos llevarnos el contador histórico.
     */
    resetAttempts() {
      attempt = 0;
    },

    /** Estado del supervisor — útil para diagnostic-bundle. */
    inspect() {
      return {
        name,
        running: !!child && !child.killed,
        shouldRun,
        currentAttempt: attempt,
        maxAttempts,
        pid: child ? child.pid : null,
      };
    },
  };
}

module.exports = { createBackendSupervisor };
