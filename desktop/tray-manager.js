const { Tray, Menu, nativeImage, clipboard, dialog } = require("electron");
const path = require("path");

let tray = null;

/**
 * Crea el icono en la bandeja del sistema con menú contextual.
 * @param {object} options
 * @param {string} options.lanIP - IP de LAN
 * @param {object} options.urls - URLs de acceso
 * @param {Function} options.onShow - Callback para mostrar la ventana
 * @param {Function} options.onStop - Callback para parar servicios
 * @param {Function} options.onQuit - Callback para salir
 */
function createTray({ lanIP, urls, onShow, onStop, onQuit }) {
  // Icono: usa icon.png si existe, si no crea uno genérico
  const iconPath = path.join(__dirname, "assets", "icon.png");
  let icon;
  try {
    icon = nativeImage.createFromPath(iconPath);
    if (icon.isEmpty()) throw new Error("empty");
    icon = icon.resize({ width: 16, height: 16 });
  } catch {
    // Crear un icono simple si no existe el archivo
    icon = nativeImage.createEmpty();
  }

  tray = new Tray(icon);
  tray.setToolTip("AutomatizaPyme - ERP");

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "AutomatizaPyme",
      enabled: false,
    },
    { type: "separator" },
    {
      label: "Abrir Dashboard",
      click: onShow,
    },
    { type: "separator" },
    {
      label: `IP Local: ${lanIP}`,
      enabled: false,
    },
    {
      label: `Copiar URL LAN: ${urls.lan}`,
      click: () => {
        clipboard.writeText(urls.lan);
      },
    },
    {
      label: `Copiar URL API: ${urls.apiLan}`,
      click: () => {
        clipboard.writeText(urls.apiLan);
      },
    },
    { type: "separator" },
    {
      label: "Usuarios conectados...",
      click: () => {
        dialog.showMessageBox({
          type: "info",
          title: "Acceso LAN",
          message: "Comparte esta dirección con los empleados de tu red:",
          detail:
            `Dashboard: ${urls.lan}\n` +
            `API: ${urls.apiLan}\n\n` +
            `Los usuarios solo necesitan un navegador web.\n` +
            `Asegúrate de que el firewall permite conexiones en los puertos 3000 y 8080.`,
        });
      },
    },
    { type: "separator" },
    {
      label: "Parar servicios",
      click: onStop,
    },
    {
      label: "Salir",
      click: onQuit,
    },
  ]);

  tray.setContextMenu(contextMenu);

  tray.on("double-click", onShow);

  return tray;
}

/**
 * Actualiza el tooltip del tray (p.ej. para mostrar estado).
 */
function updateTooltip(text) {
  if (tray) {
    tray.setToolTip(text);
  }
}

/**
 * Destruye el tray.
 */
function destroyTray() {
  if (tray) {
    tray.destroy();
    tray = null;
  }
}

module.exports = { createTray, updateTooltip, destroyTray };
