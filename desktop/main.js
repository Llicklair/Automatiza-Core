const { app, BrowserWindow, dialog } = require("electron");
const path = require("path");

const { startAll, stopAll } = require("./service-manager");
const { getLanIP, getAccessURLs } = require("./network-utils");
const { createTray, destroyTray } = require("./tray-manager");

let mainWindow = null;
let splashWindow = null;
let isQuitting = false;

// ── Splash Screen ──────────────────────────────────────────────────────────

function createSplash() {
  splashWindow = new BrowserWindow({
    width: 480,
    height: 320,
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
    icon: path.join(__dirname, "assets", "icon.ico"),
    title: "AutomatizaPyme",
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL("http://localhost:3000");

  // Minimizar a tray en vez de cerrar
  mainWindow.on("close", (e) => {
    if (!isQuitting) {
      e.preventDefault();
      mainWindow.hide();
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

  app.whenReady().then(startup);

  app.on("before-quit", () => {
    isQuitting = true;
    stopAll();
    destroyTray();
  });

  app.on("window-all-closed", () => {
    // No cerrar — se queda en tray
  });
}
