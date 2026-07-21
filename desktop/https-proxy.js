/*
 * Copyright © 2026 Marcos Recio <marcosreciosanchez@gmail.com> — AutomatizaCore
 * SPDX-License-Identifier: LicenseRef-Proprietary
 *
 * Proxy HTTPS local para la red (LAN).
 *
 * Por qué: el navegador del móvil solo permite la cámara (getUserMedia) en
 * contexto seguro — HTTPS o localhost. Sobre http:// con IP de LAN la cámara
 * queda bloqueada. Y con un certificado auto-firmado Android carga la página
 * pero SIGUE bloqueando la cámara (certificado no confiable). Por eso montamos
 * un mini-CA local (tipo mkcert): un CA propio que firma el certificado del
 * proxy; instalando el CA en el móvil UNA vez, el certificado pasa a ser de
 * confianza y la cámara funciona.
 *
 * El CA público se sirve en GET /ca.crt (MIME application/x-x509-ca-cert, que
 * dispara la instalación en Android). Rutas: /api → backend (8080), el resto →
 * frontend (3000). Un solo origen → el frontend usa rutas relativas (base.ts).
 * Proxy con módulos nativos de Node (http/https).
 */
"use strict";

const https = require("https");
const http = require("http");
const fs = require("fs");
const path = require("path");

let serverRef = null;

// ── Certificados: mini-CA local + hoja firmada por él ───────────────────────

function _generateCA() {
  const forge = require("node-forge");
  const keys = forge.pki.rsa.generateKeyPair(2048);
  const cert = forge.pki.createCertificate();
  cert.publicKey = keys.publicKey;
  cert.serialNumber = "01";
  const now = new Date();
  cert.validity.notBefore = new Date(now.getTime() - 24 * 3600 * 1000);
  cert.validity.notAfter = new Date(now.getTime() + 3650 * 24 * 3600 * 1000);
  const attrs = [
    { name: "commonName", value: "AutomatizaCore Local CA" },
    { name: "organizationName", value: "AutomatizaCore" },
  ];
  cert.setSubject(attrs);
  cert.setIssuer(attrs);
  cert.setExtensions([
    { name: "basicConstraints", cA: true, critical: true },
    { name: "keyUsage", keyCertSign: true, cRLSign: true, critical: true },
  ]);
  cert.sign(keys.privateKey, forge.md.sha256.create());
  return {
    certPem: forge.pki.certificateToPem(cert),
    keyPem: forge.pki.privateKeyToPem(keys.privateKey),
  };
}

function _generateLeaf(lanIP, caCertPem, caKeyPem) {
  const forge = require("node-forge");
  const caCert = forge.pki.certificateFromPem(caCertPem);
  const caKey = forge.pki.privateKeyFromPem(caKeyPem);
  const keys = forge.pki.rsa.generateKeyPair(2048);
  const cert = forge.pki.createCertificate();
  cert.publicKey = keys.publicKey;
  cert.serialNumber = "00" + Date.now().toString(16); // positivo y único-ish
  const now = new Date();
  cert.validity.notBefore = new Date(now.getTime() - 24 * 3600 * 1000);
  cert.validity.notAfter = new Date(now.getTime() + 3650 * 24 * 3600 * 1000);
  cert.setSubject([{ name: "commonName", value: lanIP || "localhost" }]);
  cert.setIssuer(caCert.subject.attributes);
  const altNames = [
    { type: 2, value: "localhost" },
    { type: 7, ip: "127.0.0.1" },
  ];
  if (lanIP) altNames.push({ type: 7, ip: lanIP });
  cert.setExtensions([
    { name: "basicConstraints", cA: false },
    { name: "keyUsage", digitalSignature: true, keyEncipherment: true },
    { name: "extKeyUsage", serverAuth: true },
    { name: "subjectAltName", altNames },
  ]);
  cert.sign(caKey, forge.md.sha256.create());
  return {
    certPem: forge.pki.certificateToPem(cert),
    keyPem: forge.pki.privateKeyToPem(keys.privateKey),
  };
}

/** Devuelve { key, cert (cadena hoja+CA), caPem }. El CA es persistente; la hoja
 *  se regenera si cambia la IP de LAN. El CA público se escribe a un .crt para
 *  poder instalarlo en el móvil. Carga perezosa de node-forge: si falta la dep,
 *  el llamador captura el error y la app sigue (sin HTTPS). */
async function ensureCert(lanIP, userDataDir) {
  const caFile = path.join(userDataDir, "ca.json");
  const leafFile = path.join(userDataDir, "leaf.json");
  const caCrtFile = path.join(userDataDir, "AutomatizaCore-CA.crt");

  let ca = null;
  try {
    const parsed = JSON.parse(fs.readFileSync(caFile, "utf8"));
    if (parsed && parsed.certPem && parsed.keyPem) ca = parsed;
  } catch {
    /* generar */
  }
  if (!ca) {
    ca = _generateCA();
    try {
      fs.mkdirSync(userDataDir, { recursive: true });
      fs.writeFileSync(caFile, JSON.stringify(ca));
    } catch {
      /* no cachear no es fatal */
    }
  }
  try {
    fs.writeFileSync(caCrtFile, ca.certPem);
  } catch {
    /* idem */
  }

  let leaf = null;
  try {
    const parsed = JSON.parse(fs.readFileSync(leafFile, "utf8"));
    if (parsed && parsed.lanIP === lanIP && parsed.certPem && parsed.keyPem) leaf = parsed;
  } catch {
    /* generar */
  }
  if (!leaf) {
    leaf = { lanIP, ..._generateLeaf(lanIP, ca.certPem, ca.keyPem) };
    try {
      fs.writeFileSync(leafFile, JSON.stringify(leaf));
    } catch {
      /* idem */
    }
  }

  return {
    key: leaf.keyPem,
    cert: `${leaf.certPem}\n${ca.certPem}`,
    caPem: ca.certPem,
    caPath: caCrtFile,
  };
}

// ── Proxy (módulos nativos) ─────────────────────────────────────────────────

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

/** Arranca el proxy HTTPS en 0.0.0.0:<httpsPort>. Devuelve { server, url, caUrl,
 *  caPath } o lanza si no puede escuchar (el llamador lo captura). */
async function startHttpsProxy({
  lanIP,
  userDataDir,
  frontendPort = 3000,
  backendPort = 8080,
  httpsPort = 8443,
}) {
  await stopHttpsProxy();
  const { key, cert, caPem, caPath } = await ensureCert(lanIP, userDataDir);
  const routePort = (url) => (url && url.startsWith("/api") ? backendPort : frontendPort);

  const server = https.createServer({ key, cert }, (req, res) => {
    // El CA público, para instalarlo en el móvil (Android dispara el instalador
    // de certificados con este Content-Type).
    if (req.url === "/ca.crt" || (req.url || "").startsWith("/ca.crt?")) {
      res.writeHead(200, {
        "Content-Type": "application/x-x509-ca-cert",
        "Content-Disposition": 'attachment; filename="AutomatizaCore-CA.crt"',
      });
      res.end(caPem);
      return;
    }
    proxyHttp(req, res, routePort(req.url));
  });
  server.on("upgrade", (req, socket, head) => {
    proxyUpgrade(req, socket, head, routePort(req.url));
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(httpsPort, "0.0.0.0", () => {
      server.removeListener("error", reject);
      server.on("error", (err) => console.error("[https-proxy]", err.message));
      resolve();
    });
  });

  serverRef = server;
  const url = `https://${lanIP || "localhost"}:${httpsPort}`;
  return { server, url, caUrl: `${url}/ca.crt`, caPath };
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
