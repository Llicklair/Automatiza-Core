const os = require("os");

/**
 * Devuelve la primera IPv4 no-interna (IP de LAN).
 */
function getLanIP() {
  const interfaces = os.networkInterfaces();
  for (const name of Object.keys(interfaces)) {
    for (const iface of interfaces[name]) {
      if (iface.family === "IPv4" && !iface.internal) {
        return iface.address;
      }
    }
  }
  return "127.0.0.1";
}

/**
 * Devuelve las URLs formateadas para mostrar al usuario.
 *
 * Incluye una variante por NOMBRE DE EQUIPO (`lanHost`) además de por IP: el
 * nombre sobrevive a cambios de IP por DHCP si la red soporta mDNS/NetBIOS, por
 * lo que es un enlace más estable para compartir con los empleados.
 */
function getAccessURLs(lanIP) {
  const hostname = os.hostname();
  return {
    local: "http://localhost:3000",
    lan: `http://${lanIP}:3000`,
    apiLocal: "http://localhost:8080",
    apiLan: `http://${lanIP}:8080`,
    hostname,
    lanHost: `http://${hostname}:3000`,
  };
}

module.exports = { getLanIP, getAccessURLs };
