#!/usr/bin/env node
// Copyright © 2026 Marcos Recio <marcosreciosanchez@gmail.com> — AutomatizaPyme
// SPDX-License-Identifier: LicenseRef-Proprietary
/**
 * Launcher que limpia ELECTRON_RUN_AS_NODE antes de arrancar Electron.
 * VS Code setea esta variable porque él mismo es una app Electron,
 * y causa que electron.exe se ejecute como Node.js puro.
 */
const { spawn } = require("child_process");
const path = require("path");

const electronPath = require("electron");

// Copiar env sin ELECTRON_RUN_AS_NODE
const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

const child = spawn(electronPath, ["."], {
  cwd: __dirname,
  env,
  stdio: "inherit",
  windowsHide: false,
});

child.on("close", (code) => process.exit(code ?? 0));

process.on("SIGINT", () => child.kill("SIGINT"));
process.on("SIGTERM", () => child.kill("SIGTERM"));
