#!/usr/bin/env node
/**
 * sync.js — Sincroniza backend/frontend del proyecto al app instalada.
 * Uso: node sync.js [--rebuild-frontend]
 *
 * Evita reinstalar el .exe tras cada cambio de codigo.
 * Copia solo archivos modificados (compara mtime).
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// --- Config ---
const PROJECT_ROOT = path.resolve(__dirname, "..");
const POSSIBLE_NAMES = ["automatizapyme-desktop", "AutomatizaPyme"];
const PROGRAMS_DIR = path.join(
    process.env.LOCALAPPDATA || path.join(require("os").homedir(), "AppData", "Local"),
    "Programs"
);
const INSTALL_DIR = POSSIBLE_NAMES
    .map(n => path.join(PROGRAMS_DIR, n))
    .find(p => fs.existsSync(path.join(p, "resources", "project")))
    || path.join(PROGRAMS_DIR, POSSIBLE_NAMES[0]);
const RESOURCES_DIR = path.join(INSTALL_DIR, "resources");
const TARGET_PROJECT = path.join(RESOURCES_DIR, "project");

const REBUILD_FRONTEND = process.argv.includes("--rebuild-frontend");

// --- Helpers ---
function log(msg) { console.log(`[sync] ${msg}`); }
function warn(msg) { console.warn(`[sync] WARN: ${msg}`); }
function error(msg) { console.error(`[sync] ERROR: ${msg}`); process.exit(1); }

const crypto = require("crypto");

const IGNORE_PATTERNS = [
    "node_modules", ".next", "__pycache__", ".venv", "venv",
    ".pyc", ".pyo", ".git", ".DS_Store", "Thumbs.db",
    "dist", "build", ".pytest_cache", ".mypy_cache", ".ruff_cache",
];

function fileHash(filePath) {
    try {
        return crypto.createHash("md5").update(fs.readFileSync(filePath)).digest("hex");
    } catch { return null; }
}

function shouldIgnore(name) {
    return IGNORE_PATTERNS.some(p => name === p || name.endsWith(p));
}

let copied = 0, skipped = 0, created = 0;

function syncDir(src, dest) {
    if (!fs.existsSync(src)) return;
    if (!fs.existsSync(dest)) {
        fs.mkdirSync(dest, { recursive: true });
        created++;
    }

    const entries = fs.readdirSync(src, { withFileTypes: true });
    for (const entry of entries) {
        if (shouldIgnore(entry.name)) continue;

        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);

        if (entry.isDirectory()) {
            syncDir(srcPath, destPath);
        } else {
            // Solo copiar si es mas nuevo o no existe
            if (fs.existsSync(destPath)) {
                const srcStat = fs.statSync(srcPath);
                const destStat = fs.statSync(destPath);
                if (srcStat.mtimeMs <= destStat.mtimeMs) {
                    skipped++;
                    continue;
                }
            }
            fs.copyFileSync(srcPath, destPath);
            copied++;
        }
    }

    // Eliminar archivos en destino que ya no existen en origen
    if (fs.existsSync(dest)) {
        const destEntries = fs.readdirSync(dest, { withFileTypes: true });
        for (const entry of destEntries) {
            if (shouldIgnore(entry.name)) continue;
            const srcPath = path.join(src, entry.name);
            const destPath = path.join(dest, entry.name);
            if (!fs.existsSync(srcPath)) {
                if (entry.isDirectory()) {
                    fs.rmSync(destPath, { recursive: true, force: true });
                } else {
                    fs.unlinkSync(destPath);
                }
                log(`  eliminado: ${path.relative(dest, destPath)}`);
            }
        }
    }
}

// --- Main ---
function main() {
    log(`Proyecto: ${PROJECT_ROOT}`);
    log(`App instalada: ${INSTALL_DIR}`);

    if (!fs.existsSync(INSTALL_DIR)) {
        error(`App no encontrada en ${INSTALL_DIR}. Instala primero con el .exe`);
    }
    if (!fs.existsSync(TARGET_PROJECT)) {
        error(`Directorio project/ no encontrado en ${TARGET_PROJECT}`);
    }

    // 1. Sync backend — detectar cambios en requirements.txt
    const reqSrc = path.join(PROJECT_ROOT, "backend", "requirements.txt");
    const reqDest = path.join(TARGET_PROJECT, "backend", "requirements.txt");
    const reqHashBefore = fileHash(reqDest);

    log("Sincronizando backend...");
    copied = skipped = created = 0;
    syncDir(
        path.join(PROJECT_ROOT, "backend"),
        path.join(TARGET_PROJECT, "backend")
    );
    log(`  Backend: ${copied} copiados, ${skipped} sin cambios, ${created} dirs creados`);

    // Si requirements.txt cambió, invalidar hash de deps para forzar reinstalación
    const reqHashAfter = fileHash(reqDest);
    if (reqHashBefore !== reqHashAfter) {
        const APPDATA_DIR = path.join(
            process.env.APPDATA || path.join(require("os").homedir(), "AppData", "Roaming"),
            "AutomatizaPyme"
        );
        const depsHashFile = path.join(APPDATA_DIR, "deps_requirements.hash");
        try { fs.unlinkSync(depsHashFile); } catch {}
        log("  requirements.txt cambió → las dependencias se reinstalarán al iniciar la app");
    }

    // 2. Sync frontend (solo source, no .next ni node_modules)
    log("Sincronizando frontend...");
    copied = skipped = created = 0;
    syncDir(
        path.join(PROJECT_ROOT, "frontend"),
        path.join(TARGET_PROJECT, "frontend")
    );
    const frontendChanged = copied > 0;
    log(`  Frontend: ${copied} copiados, ${skipped} sin cambios, ${created} dirs creados`);

    // 3. Sync .env
    const envSrc = path.join(PROJECT_ROOT, ".env");
    const envDest = path.join(TARGET_PROJECT, ".env");
    if (fs.existsSync(envSrc)) {
        fs.copyFileSync(envSrc, envDest);
        log("  .env copiado");
    }

    // 4. Borrar .next si el frontend cambió o se pidió rebuild explícito
    if (REBUILD_FRONTEND || frontendChanged) {
        const nextDir = path.join(TARGET_PROJECT, "frontend", ".next");
        if (fs.existsSync(nextDir)) {
            fs.rmSync(nextDir, { recursive: true, force: true });
            const reason = frontendChanged ? "archivos de frontend cambiaron" : "--rebuild-frontend";
            log(`  .next eliminado (${reason}) — el frontend se rebuildeará al iniciar la app`);
        }
    }

    log("");
    log("Sincronización completada. Reinicia la app para aplicar los cambios.");
    log("(Cierra desde el system tray > Salir, luego vuelve a abrir)");
}

main();
