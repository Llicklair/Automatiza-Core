/*
 * Copyright © 2026 Marcos Recio <marcosreciosanchez@gmail.com> — AutomatizaCore
 * SPDX-License-Identifier: LicenseRef-Proprietary
 */
const { app, BrowserWindow, dialog, shell, ipcMain, Menu, safeStorage } = require("electron");
const fs = require("fs");
const path = require("path");
const { autoUpdater } = require("electron-updater");

// ── SEC.JWT — secure storage handlers ───────────────────────────────────────
// Tokens JWT cifrados con safeStorage (DPAPI/Keychain/libsecret) en
// `<userData>/secure/<key>.dat`. Whitelist de keys para evitar abuso del API.

const SECURE_STORE_KEYS = new Set(["access_token", "refresh_token"]);

function secureStoreFilePath(key) {
  return path.join(app.getPath("userData"), "secure", `${key}.dat`);
}

function isSecureStoreAvailable() {
  try {
    return safeStorage.isEncryptionAvailable();
  } catch {
    return false;
  }
}

ipcMain.handle("secure-store:is-available", () => isSecureStoreAvailable());

ipcMain.handle("secure-store:get", (_event, key) => {
  if (!SECURE_STORE_KEYS.has(key)) return null;
  try {
    if (!isSecureStoreAvailable()) return null;
    const filePath = secureStoreFilePath(key);
    if (!fs.existsSync(filePath)) return null;
    const buffer = fs.readFileSync(filePath);
    return safeStorage.decryptString(buffer);
  } catch {
    return null;
  }
});

ipcMain.handle("secure-store:set", (_event, key, value) => {
  if (!SECURE_STORE_KEYS.has(key)) return false;
  if (typeof value !== "string") return false;
  try {
    if (!isSecureStoreAvailable()) return false;
    const filePath = secureStoreFilePath(key);
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    const encrypted = safeStorage.encryptString(value);
    fs.writeFileSync(filePath, encrypted);
    return true;
  } catch {
    return false;
  }
});

ipcMain.handle("secure-store:remove", (_event, key) => {
  if (!SECURE_STORE_KEYS.has(key)) return false;
  try {
    const filePath = secureStoreFilePath(key);
    if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
    return true;
  } catch {
    return false;
  }
});

const { startAll, stopAll, killOrphanProcesses, getBackendEnv, waitForHTTP } = require("./service-manager");
const { stopBackend, startBackend } = require("./python-manager");
const { getLanIP, getAccessURLs } = require("./network-utils");
const { createTray, destroyTray } = require("./tray-manager");

// ── Auto-updater ───────────────────────────────────────────────────────────

// DIS.UPD — gestor del canal stable/beta persistido en electron-store.
let updateChannelMgr = null;
// electron-store v11 es ESM-only (no se puede `require`). Se precarga con
// import() dinámico en el arranque (ver app.whenReady -> _loadElectronStore) y
// se cachea la clase aquí para usarla de forma síncrona desde este gestor lazy.
let _ElectronStore = null;
async function _loadElectronStore() {
  if (!_ElectronStore) {
    _ElectronStore = (await import("electron-store")).default;
  }
  return _ElectronStore;
}
function _ensureUpdateChannelMgr() {
  if (updateChannelMgr) return updateChannelMgr;
  if (!_ElectronStore) {
    console.warn("electron-store aún no precargado; gestor de canal no inicializado");
    return null;
  }
  try {
    const Store = _ElectronStore;
    const { createUpdateChannelManager } = require("./lib/update-channel");
    const store = new Store({ name: "update-prefs" });
    updateChannelMgr = createUpdateChannelManager({
      store, autoUpdater, logger: (m) => console.log(m),
    });
  } catch (e) {
    console.warn("update-channel manager no inicializado:", e.message);
  }
  return updateChannelMgr;
}

function setupAutoUpdater() {
  if (!app.isPackaged) return; // solo en builds empaquetados

  autoUpdater.autoDownload = true;
  autoUpdater.autoInstallOnAppQuit = true;

  // DIS.UPD — aplica la preferencia de canal antes del primer check.
  try { _ensureUpdateChannelMgr()?.apply(); } catch { /* swallow */ }

  autoUpdater.on("update-available", (info) => {
    mainWindow?.webContents.send("update-available", { version: info.version });
  });
  autoUpdater.on("update-not-available", () => {
    mainWindow?.webContents.send("update-not-available");
  });
  autoUpdater.on("download-progress", (p) => {
    mainWindow?.webContents.send("update-download-progress", {
      percent: Math.round(p.percent),
      transferred: p.transferred,
      total: p.total,
    });
  });
  autoUpdater.on("update-downloaded", () => {
    mainWindow?.webContents.send("update-downloaded");
  });
  autoUpdater.on("error", (err) => {
    mainWindow?.webContents.send("update-error", err.message);
  });

  autoUpdater.checkForUpdates().catch(() => {}); // silencioso en arranque
}

let mainWindow = null;
let splashWindow = null;
let isQuitting = false;
/** true = backend en 0.0.0.0 (LAN); false = solo 127.0.0.1 */
let localNetworkEnabled = true;

// ── Splash Screen ──────────────────────────────────────────────────────────

function createSplash() {
  splashWindow = new BrowserWindow({
    width: 480,
    height: 360,
    frame: false,
    resizable: false,
    transparent: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });
  splashWindow.loadFile(path.join(__dirname, "splash.html"));
  return splashWindow;
}

function splashStatus(message, progress) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send("splash-status", { message, progress });
  }
}

// ── Main Window ────────────────────────────────────────────────────────────

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 600,
    icon: app.isPackaged
      ? path.join(process.resourcesPath, "icon.ico")
      : path.join(__dirname, "assets", "icon.ico"),
    title: "AutomatizaCore",
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  mainWindow.loadURL("http://localhost:3000");

  // Abrir URLs OAuth en el navegador externo del sistema
  mainWindow.webContents.on("will-navigate", (event, url) => {
    if (url.includes("accounts.google.com") || url.includes("login.microsoftonline.com")) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    const externalOAuth = [
      "accounts.google.com", "login.microsoftonline.com",
      "twitter.com/i/oauth", "x.com/i/oauth",
      "facebook.com/", "api.instagram.com/oauth",
      "www.linkedin.com/oauth",
    ];
    if (externalOAuth.some((p) => url.includes(p))) {
      shell.openExternal(url);
      return { action: "deny" };
    }
    return { action: "allow" };
  });

  // Minimizar a tray en vez de cerrar
  mainWindow.on("close", (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  // SEC.DEV — DevTools solo en builds no empaquetadas (dev).
  // En producción se bloquean F12, Ctrl+Shift+I y Cmd+Opt+I.
  mainWindow.webContents.on("before-input-event", (event, input) => {
    const key = (input.key || "").toLowerCase();
    const isDevToolsShortcut =
      key === "f12" ||
      ((input.control || input.meta) && input.shift && key === "i") ||
      (input.alt && input.meta && key === "i");

    if (!isDevToolsShortcut) return;

    if (app.isPackaged) {
      event.preventDefault();
    } else {
      mainWindow.webContents.toggleDevTools();
    }
  });

  mainWindow.once("ready-to-show", () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    mainWindow.show();
    mainWindow.focus();
  });

  return mainWindow;
}

// ── Startup ────────────────────────────────────────────────────────────────

async function startup() {
  createSplash();

  const lanIP = getLanIP();
  const urls = getAccessURLs(lanIP);

  try {
    // Arrancar todos los servicios (PostgreSQL + Backend + Frontend)
    await startAll((message, progress) => {
      splashStatus(message, progress);
    });

    // Ventana principal
    createMainWindow();
    setupAutoUpdater();

    // Tray
    createTray({
      lanIP,
      urls,
      onShow: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      },
      onStop: async () => {
        const { response } = await dialog.showMessageBox({
          type: "question",
          buttons: ["Cancelar", "Parar"],
          defaultId: 0,
          title: "Parar servicios",
          message: "¿Parar todos los servicios?",
          detail: "Los usuarios conectados perderán el acceso.",
        });
        if (response === 1) {
          stopAll();
        }
      },
      onQuit: () => {
        isQuitting = true;
        app.quit();
      },
    });
  } catch (err) {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
    }
    dialog.showErrorBox("Error al arrancar", err.message);
    app.quit();
  }
}

// ── IPC Handlers ──────────────────────────────────────────────────────────

ipcMain.handle("check-for-updates", async () => {
  if (!app.isPackaged) {
    mainWindow?.webContents.send("update-not-available");
    return;
  }
  autoUpdater.checkForUpdates().catch((err) => {
    mainWindow?.webContents.send("update-error", err.message);
  });
});

// DIS.UPD — canal de actualización (stable/beta).
ipcMain.handle("get-update-channel", () => {
  const mgr = _ensureUpdateChannelMgr();
  return mgr ? mgr.getChannel() : "stable";
});

ipcMain.handle("set-update-channel", (_event, channel) => {
  const mgr = _ensureUpdateChannelMgr();
  if (!mgr) return { ok: false, error: "manager no disponible" };
  const applied = mgr.setChannel(channel);
  // Triggar un re-check inmediato con el nuevo canal.
  if (app.isPackaged) {
    autoUpdater.checkForUpdates().catch((err) => {
      mainWindow?.webContents.send("update-error", err.message);
    });
  }
  return { ok: true, channel: applied };
});

ipcMain.handle("install-update", () => {
  // DIS.SVC — paramos los servicios ANTES de quitAndInstall.
  // Sin esto el instalador puede fallar al reemplazar binarios que el
  // backend (uvicorn) tiene abiertos. Marcamos isQuitting=true para que
  // el handler `close` no intercepte ocultando la ventana.
  try {
    isQuitting = true;
    stopAll();
  } catch (err) {
    // No bloqueamos el update por un fallo de stop — el instalador lidiará
    // con los handles bloqueados a coste de un primer arranque más lento.
    console.warn("install-update: stopAll falló:", err.message);
  }
  autoUpdater.quitAndInstall();
});

ipcMain.handle("open-template-native", async (_event, filePath) => {
  await shell.openPath(filePath);
});

ipcMain.handle("open-external", (_event, url) => {
  shell.openExternal(url);
});

ipcMain.handle("toggle-local-network", async (_event, enabled) => {
  const newHost = enabled ? "0.0.0.0" : "127.0.0.1";
  const lanIP = getLanIP();
  try {
    stopBackend();
    const env = getBackendEnv(lanIP);
    env._BACKEND_HOST = newHost;
    startBackend(env);
    await waitForHTTP(8080, 120000);
    localNetworkEnabled = enabled;
    return { ok: true, host: newHost, lanIP, localNetworkEnabled };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

ipcMain.handle("get-network-status", async () => {
  const lanIP = getLanIP();
  const urls = getAccessURLs(lanIP);
  return { localNetworkEnabled, lanIP, urls };
});

// ── Impresión de tickets (TPV) ─────────────────────────────────────────────
// El renderer manda el HTML del ticket (autocontenido, 80 mm) y lo imprimimos
// en una ventana oculta. Con `silent` + `deviceName` va directo a la impresora
// (térmica de TPV); sin ellos abre el diálogo del sistema (cualquier impresora).

ipcMain.handle("list-printers", async () => {
  try {
    if (!mainWindow || mainWindow.isDestroyed()) return [];
    return await mainWindow.webContents.getPrintersAsync();
  } catch (err) {
    return [];
  }
});

ipcMain.handle("print-ticket", async (_event, payload = {}) => {
  const { html, opts } = payload || {};
  const options = opts || {};
  let printWin = null;
  try {
    printWin = new BrowserWindow({
      show: false,
      webPreferences: {
        sandbox: true,
        contextIsolation: true,
        nodeIntegration: false,
        javascript: false, // el ticket es HTML estático: sin JS por seguridad
      },
    });
    await printWin.loadURL("data:text/html;charset=utf-8," + encodeURIComponent(html || ""));
    // Margen para decodificar el QR (data-URI SVG) antes de imprimir.
    await new Promise((r) => setTimeout(r, 200));
    const result = await new Promise((resolve) => {
      const printOpts = {
        silent: !!options.silent,
        printBackground: true,
        margins: { marginType: "none" },
      };
      if (options.deviceName) printOpts.deviceName = options.deviceName;
      printWin.webContents.print(printOpts, (success, failureReason) => {
        resolve({ success, failureReason: failureReason || null });
      });
    });
    return result;
  } catch (err) {
    return { success: false, failureReason: String(err && err.message ? err.message : err) };
  } finally {
    // Retardo antes de destruir para no cortar el spooling del trabajo.
    if (printWin && !printWin.isDestroyed()) {
      const win = printWin;
      setTimeout(() => {
        if (win && !win.isDestroyed()) win.destroy();
      }, 1500);
    }
  }
});

// ── Single instance lock (debe ir ANTES de whenReady) ──────────────────────

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.show();
      mainWindow.focus();
    }
  });

  // ── App lifecycle ────────────────────────────────────────────────────────

  app.whenReady().then(async () => {
    // SEC.DEV — deshabilita el menú nativo en producción para cerrar
    // el camino "View → Toggle DevTools" y similares.
    if (app.isPackaged) {
      Menu.setApplicationMenu(null);
    }
    // electron-store v11 (ESM): precargar la clase antes de startup(), que
    // dispara setupAutoUpdater() -> _ensureUpdateChannelMgr().
    try {
      await _loadElectronStore();
    } catch (e) {
      console.warn("No se pudo precargar electron-store:", e.message);
    }
    return startup();
  });

  app.on("before-quit", () => {
    isQuitting = true;
    stopAll();
    destroyTray();
  });

  app.on("will-quit", () => {
    // Segunda red de seguridad: matar lo que quede
    try { stopAll(); } catch {}
  });

  app.on("window-all-closed", () => {
    // No cerrar — se queda en tray
  });

  // Última red de seguridad: si el proceso Node muere por cualquier razón
  process.on("exit", () => {
    try { killOrphanProcesses(); } catch {}
  });

  process.on("SIGTERM", () => {
    isQuitting = true;
    stopAll();
    destroyTray();
    app.quit();
  });

  process.on("uncaughtException", (err) => {
    console.error("Uncaught exception:", err);
    try { stopAll(); } catch {}
    app.quit();
  });
}
