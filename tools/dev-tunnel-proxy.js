#!/usr/bin/env node
/**
 * dev-tunnel-proxy.js — SOLO para la prueba de acceso remoto SIN dominio (Fase 1).
 *
 * Un quick tunnel de Cloudflare (`cloudflared tunnel --url`) solo expone UN
 * puerto, pero la app necesita dos: frontend (3000) y backend (8080). Este proxy
 * los unifica en http://localhost:8088 con el MISMO ruteo por path que hará el
 * túnel con nombre en producción:
 *     /api/v1/*  +  /ws/*   →  backend  :8080
 *     resto                 →  frontend :3000
 *
 * Uso:
 *   1) node tools/dev-tunnel-proxy.js
 *   2) cloudflared tunnel --url http://localhost:8088
 *   3) abre la URL *.trycloudflare.com desde el móvil en 4G
 *
 * No es parte del producto: en producción se usa el ingress de cloudflared
 * (ver docs/remote-access-cloudflare.md), no este proxy.
 */
const http = require("http");
const net = require("net");

const PORT = 8088;
const FRONTEND = { host: "127.0.0.1", port: 3000 };
const BACKEND = { host: "127.0.0.1", port: 8080 };

function target(url) {
    return url.startsWith("/api/v1") || url.startsWith("/ws") ? BACKEND : FRONTEND;
}

// Peticiones HTTP normales
const server = http.createServer((req, res) => {
    const t = target(req.url);
    const proxyReq = http.request(
        { host: t.host, port: t.port, method: req.method, path: req.url, headers: req.headers },
        (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
        }
    );
    proxyReq.on("error", (e) => {
        res.writeHead(502);
        res.end("proxy error: " + e.message);
    });
    req.pipe(proxyReq);
});

// WebSocket / upgrade (notificaciones en /ws)
server.on("upgrade", (req, socket, head) => {
    const t = target(req.url);
    const up = net.connect(t.port, t.host, () => {
        up.write(
            `${req.method} ${req.url} HTTP/1.1\r\n` +
            Object.entries(req.headers)
                .map(([k, v]) => `${k}: ${v}`)
                .join("\r\n") +
            "\r\n\r\n"
        );
        if (head && head.length) up.write(head);
        up.pipe(socket);
        socket.pipe(up);
    });
    up.on("error", () => socket.destroy());
    socket.on("error", () => up.destroy());
});

server.listen(PORT, "127.0.0.1", () => {
    console.log(`[unifier] http://localhost:${PORT}  → /api/v1,/ws → 8080 · resto → 3000`);
    console.log(`[unifier] ahora: cloudflared tunnel --url http://localhost:${PORT}`);
});
