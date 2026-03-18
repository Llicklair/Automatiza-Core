const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  onSplashStatus: (callback) => ipcRenderer.on("splash-status", (_, data) => callback(data)),
});
