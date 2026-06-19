/**
 * Resolución en runtime de la base del backend. Un único sitio para los tres
 * consumidores (cliente HTTP, reporter de errores y WebSocket de notificaciones)
 * para que no se escape ningún `:8080` hardcodeado.
 *
 * Dos modos, decididos por la URL desde la que se carga la app:
 *
 *  1. ACCESO DIRECTO — Electron local, `next dev`, o LAN. El frontend corre en
 *     `:3000` y el backend en `:8080` del MISMO host → devolvemos una URL
 *     absoluta a `:8080`.
 *
 *  2. ACCESO REMOTO tras un proxy inverso (Cloudflare Tunnel) — la app se sirve
 *     en un puerto estándar (443/80) bajo un hostname público. Devolvemos
 *     MISMO ORIGEN (base vacía) y el túnel enruta `/api/v1/*` y `/ws/*` al
 *     backend. Así NO se dispara CORS y el `:8080` nunca se expone a internet.
 *
 * Discriminador: es acceso directo si el puerto es 3000 (frontend) o si el host
 * es loopback (Electron/dev/tests jsdom). Cualquier otro caso (hostname público,
 * puerto estándar) es un proxy → mismo origen.
 */

const DIRECT_HOSTS = new Set(["localhost", "127.0.0.1", "::1", "[::1]"]);

function isDirect(hostname: string, port: string): boolean {
    return port === "3000" || DIRECT_HOSTS.has(hostname);
}

/** Base HTTP del backend. Vacía ("") en modo remoto → peticiones relativas al origen. */
export function resolveApiBase(): string {
    if (typeof window === "undefined") return "http://127.0.0.1:8080";
    const { protocol, hostname, port } = window.location;
    return isDirect(hostname, port) ? `${protocol}//${hostname}:8080` : "";
}

/** Base WebSocket absoluta (el constructor WebSocket no admite URLs relativas). */
export function resolveWsBase(): string {
    if (typeof window === "undefined") return "ws://127.0.0.1:8080";
    const { protocol, hostname, host, port } = window.location;
    const wsProto = protocol === "https:" ? "wss:" : "ws:";
    return isDirect(hostname, port) ? `${wsProto}//${hostname}:8080` : `${wsProto}//${host}`;
}
