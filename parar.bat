@echo off
chcp 65001 >nul
title AutomatizaPyme — Deteniendo proyecto...

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║         AutomatizaPyme — Parada de Servicios       ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ─── PASO 1: Docker ────────────────────────────────────────────────────────
echo [1/2] Deteniendo contenedores Docker...
docker-compose down
if %errorlevel% neq 0 (
    echo      AVISO: Hubo un problema con docker-compose down o no había nada corriendo.
) else (
    echo      Contenedores detenidos y eliminados correctamente.
)

:: ─── PASO 2: Procesos de Node (Frontend) ───────────────────────────────────
echo.
echo [2/2] Limpiando procesos de Node.js (Frontend)...
taskkill /F /IM node.exe /T >nul 2>&1
if %errorlevel% equ 0 (
    echo      Procesos de Node.js finalizados.
) else (
    echo      No se encontraron procesos de Node.js activos.
)

:: ─── Finalización ──────────────────────────────────────────────────────────
echo.
echo  ✅  SISTEMA DETENIDO COMPLETAMENTE
echo  ══════════════════════════════════════════════════
echo  Todos los servicios de backend y frontend han sido
echo  cerrados.
echo  ══════════════════════════════════════════════════
echo.
echo  Presiona cualquier tecla para salir.
pause >nul
exit
