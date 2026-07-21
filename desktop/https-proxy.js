/*
 * Copyright © 2026 Marcos Recio <marcosreciosanchez@gmail.com> — AutomatizaCore
 * SPDX-License-Identifier: LicenseRef-Proprietary
 *
 * Proxy HTTPS local para la red (LAN).
 *
 * Por qué: el navegador del móvil solo permite la cámara (getUserMedia) en
 * contexto seguro — HTTPS o localhost. Sobre http:// con IP de LAN la cámara
 * queda bloqueada. Este proxy sirve toda la app por HTTPS en la LAN con un
 * certificado auto-firmado, de modo que /mobile-scanner puede usar la cámara.
 *
 * Rutas: `/api` → backend (8080), el resto → frontend (3000). Un solo origen,
 * así el frontend usa rutas relativas (ver frontend/src/lib/api/base.ts) y no
 * se dispara CORS ni se expone el :8080. Incluye upgrade de WebSocket.
 *
 * Proxy implementado con módulos nativos de Node (http/https) — sin deps extra
 * salvo `selfsigned` para el certificado.
 */
"use strict";

const https = require("https");
const http = require("http");
const fs = require("fs");
const path = require("path");

let serverRef = null;

/** Certificado auto-firmado con la IP de LAN en el SAN. Cacheado en userData;
 *  se regenera si cambia la IP (DHCP) o no existe. */
async function ensureCert(lanIP, userDataDir) {
  const file = path.join(userDataDir, "https-cert.json");
  try {
    const cached = JSON.parse(fs.readFileSync(file, "utf8"));
    if (cached && cached.lanIP === lanIP && cached.key && cached.cert) {
      return { key: cached.key, cert: cached.cert };
    }
  } catch {
    /* no hay cache o es inválida → generar */
  }

  const attrs = [{ name: "commonName", value: lanIP || "localhost" }];
  const altNames = [
    { type: 2, value: "localhost" },
    { type: 7, ip: "127.0.0.1" },
  ];
  if (lanIP) altNames.push({ type: 7, ip: lanIP });

  // Carga perezosa: si la dependencia no está instalada en la app, el proxy
  // falla de forma controlada (lo captura el llamador) en vez de tumbar el
  // proceso principal al cargar el módulo.
  const selfsigned = require("selfsigned");
  // selfsigned 5.x: generate() es asíncrono (devuelve Promise).
  const pems = await selfsigned.generate(attrs, {
    days: 3650,
    keySize: 2048,
    algorithm: "sha256",
    extensions: [{ name: "subjectAltName", altNames }],
  });
  const key = pems.private;
  const cert = pems.cert;
  try {
    fs.mkdirSync(userDataDir, { recursive: true });
    fs.writeFileSync(file, JSON.stringify({ lanIP, key, cert }), "utf8");
  } catch {
    /* no poder cachear no es fatal */
  }
  return { key, cert };
}

function proxyHttp(req, res, port) {
  const upstream = http.request(
    { hostname: "127.0.0.1", port, path: req.url, method: req.method, headers: req.headers },
    (upRes) => {
      res.writeHead(upRes.statusCode || 502, upRes.headers);
      upRes.pipe(res);
    },
  );
  upstream.on("error", () => {
    if (!res.headersSent) res.writeHead(502, { "content-type": "text/plain" });
    res.end("Bad gateway");
  });
  req.pipe(upstream);
}

function proxyUpgrade(req, socket, head, port) {
  const upstream = http.request({
    hostname: "127.0.0.1",
    port,
    path: req.url,
    method: req.method,
    headers: req.headers,
  });
  upstream.on("upgrade", (upRes, upSocket, upHead) => {
    const headers = Object.entries(upRes.headers)
      .map(([k, v]) => `${k}: ${v}`)
      .join("\r\n");
    socket.write(`HTTP/1.1 101 Switching Protocols\r\n${headers}\r\n\r\n`);
    if (upHead && upHead.length) upSocket.unshift(upHead);
    upSocket.pipe(socket);
    socket.pipe(upSocket);
    upSocket.on("error", () => socket.destroy());
    socket.on("error", () => upSocket.destroy());
  });
  upstream.on("error", () => socket.destroy());
  if (head && head.length) upstream.write(head);
  upstream.end();
}

/** Arranca el proxy HTTPS en 0.0.0.0:<httpsPort>. Devuelve { server, url } o
 *  lanza si no puede escuchar (el llamador lo captura y sigue sin HTTPS). */
async function startHttpsProxy({
  lanIP,
  userDataDir,
  frontendPort = 3000,
  backendPort = 8080,
  httpsPort = 8443,
}) {
  await stopHttpsProxy();
  const { key, cert } = await ensureCert(lanIP, userDataDir);
  const routePort = (url) => (url && url.startsWith("/api") ? backendPort : frontendPort);

  const server = https.createServer({ key, cert }, (req, res) => {
    proxyHttp(req, res, routePort(req.url));
  });
  server.on("upgrade", (req, socket, head) => {
    proxyUpgrade(req, socket, head, routePort(req.url));
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(httpsPort, "0.0.0.0", () => {
      server.removeListener("error", reject);
      // Errores posteriores (conexiones sueltas) no deben tumbar la app.
      server.on("error", (err) => console.error("[https-proxy]", err.message));
      resolve();
    });
  });

  serverRef = server;
  const url = `https://${lanIP || "localhost"}:${httpsPort}`;
  return { server, url };
}

function stopHttpsProxy() {
  return new Promise((resolve) => {
    if (!serverRef) return resolve();
    const s = serverRef;
    serverRef = null;
    try {
      s.close(() => resolve());
    } catch {
      resolve();
    }
  });
}

module.exports = { startHttpsProxy, stopHttpsProxy, ensureCert };
