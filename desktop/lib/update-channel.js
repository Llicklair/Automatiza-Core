/**
 * DIS.UPD — gestor del canal de actualización (stable | beta).
 *
 * Persiste la preferencia del usuario en `electron-store` (un JSON
 * cifrado a través de safeStorage si está disponible) y la aplica al
 * `autoUpdater` antes de cada checkForUpdates().
 *
 * Canales soportados:
 *   - `stable` (default) — releases finales, máxima estabilidad.
 *   - `beta`             — pre-releases para early adopters.
 *
 * El canal afecta directamente a qué `latest.yml` consulta autoUpdater
 * (latest.yml vs beta.yml) cuando el publish provider es GitHub.
 */

const SUPPORTED_CHANNELS = ["stable", "beta"];
const DEFAULT_CHANNEL = "stable";
const STORE_KEY = "update.channel";

function normalize(raw) {
  if (typeof raw !== "string") return DEFAULT_CHANNEL;
  const v = raw.toLowerCase().trim();
  return SUPPORTED_CHANNELS.includes(v) ? v : DEFAULT_CHANNEL;
}

/**
 * Crea un gestor de canal sobre una instancia de electron-store y un
 * autoUpdater de electron-updater. Permite inyectar mocks en tests.
 *
 * @param {{ store: { get: Function, set: Function }, autoUpdater: any, logger?: Function }} deps
 */
function createUpdateChannelManager({ store, autoUpdater, logger = () => { } } = {}) {
  if (!store || typeof store.get !== "function" || typeof store.set !== "function") {
    throw new Error("update-channel: `store` debe exponer get() y set()");
  }
  if (!autoUpdater) {
    throw new Error("update-channel: `autoUpdater` requerido");
  }

  function getChannel() {
    return normalize(store.get(STORE_KEY));
  }

  function setChannel(raw) {
    const next = normalize(raw);
    store.set(STORE_KEY, next);
    apply(next);
    logger(`update-channel: ${next}`);
    return next;
  }

  function apply(channel) {
    const ch = channel || getChannel();
    autoUpdater.channel = ch === "beta" ? "beta" : "latest";
    // Permitir prerelease cuando estamos en beta (electron-updater requiere
    // ambos flags para resolver YAMLs alternativos).
    autoUpdater.allowPrerelease = ch === "beta";
  }

  return {
    getChannel,
    setChannel,
    apply,
    /** Lista de canales que la UI puede ofrecer. */
    supported: () => [...SUPPORTED_CHANNELS],
  };
}

module.exports = {
  createUpdateChannelManager,
  SUPPORTED_CHANNELS,
  DEFAULT_CHANNEL,
  normalize,
};
