const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  onSplashStatus: (callback) => ipcRenderer.on("splash-status", (_, data) => callback(data)),
  openTemplateNative: (filePath) => ipcRenderer.invoke("open-template-native", filePath),
  toggleLocalNetwork: (enabled) => ipcRenderer.invoke("toggle-local-network", enabled),
  getNetworkStatus: () => ipcRenderer.invoke("get-network-status"),
  // SEC.JWT — secure storage para tokens JWT vía Electron safeStorage (DPAPI/Keychain/libsecret).
  // Tokens nunca en `localStorage` ni en disco sin cifrar.
  secureStore: {
    get: (key) => ipcRenderer.invoke("secure-store:get", key),
    set: (key, value) => ipcRenderer.invoke("secure-store:set", key, value),
    remove: (key) => ipcRenderer.invoke("secure-store:remove", key),
    isAvailable: () => ipcRenderer.invoke("secure-store:is-available"),
  },
  // Auto-update
  checkForUpdates: () => ipcRenderer.invoke("check-for-updates"),
  installUpdate: () => ipcRenderer.invoke("install-update"),
  getUpdateChannel: () => ipcRenderer.invoke("get-update-channel"),
  setUpdateChannel: (channel) => ipcRenderer.invoke("set-update-channel", channel),
  onUpdateAvailable: (cb) => ipcRenderer.on("update-available", (_, info) => cb(info)),
  onUpdateNotAvailable: (cb) => ipcRenderer.on("update-not-available", () => cb()),
  onUpdateDownloadProgress: (cb) => ipcRenderer.on("update-download-progress", (_, p) => cb(p)),
  onUpdateDownloaded: (cb) => ipcRenderer.on("update-downloaded", () => cb()),
  onUpdateError: (cb) => ipcRenderer.on("update-error", (_, msg) => cb(msg)),
  removeUpdateListeners: () => {
    ["update-available","update-not-available","update-download-progress","update-downloaded","update-error"]
      .forEach(ch => ipcRenderer.removeAllListeners(ch));
  },
});
