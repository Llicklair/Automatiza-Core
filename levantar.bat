@echo off
chcp 65001 >nul
title AutomatizaPyme — Levantando proyecto...

echo.
echo  ╔══════════════════════════════════════════════════╗
echo  ║         AutomatizaPyme — Arranque Completo         ║
echo  ╚══════════════════════════════════════════════════╝
echo.

:: ─── PASO 1: Docker ────────────────────────────────────────────────────────
echo [1/4] Comprobando Docker...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo      Docker ya está corriendo. Abriendo interfaz de Docker Desktop...
    start docker-desktop://
    goto docker_ready
)

echo      Docker no está activo. Iniciando Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
start docker-desktop://
echo      Esperando a que Docker arranque (puede tardar ~30 segundos)...


:wait_docker
ping 127.0.0.1 -n 4 >nul
docker info >nul 2>&1
if %errorlevel% neq 0 goto wait_docker

:docker_ready
echo      Docker listo!


:: ─── PASO 2: Docker Compose ────────────────────────────────────────────────
echo.
echo [2/4] Iniciando contenedores (API, DB, Redis, Worker)...
echo      NOTA: Ollama (LLM local) NO arranca por defecto para ahorrar RAM/CPU.
echo      Para usarlo ejecuta: docker-compose --profile llm up -d
echo.
docker-compose up -d
if %errorlevel% neq 0 (
    echo      ERROR: Falló docker-compose. Verifica que Docker Desktop esté abierto.
    pause
    exit /b 1
)

:: ─── PASO 3: Base de Datos y Migraciones ───────────────────────────────────
echo.
echo [3/4] Esperando a la Base de Datos...
:wait_db
ping 127.0.0.1 -n 4 >nul
docker-compose exec -T db pg_isready -U pyme_user -d pyme_db >nul 2>&1
if %errorlevel% neq 0 goto wait_db

echo      Aplicando cambios en la base de datos...
docker-compose exec -T api alembic upgrade head
if %errorlevel% neq 0 (
    echo      AVISO: Las migraciones fallaron o ya estaban aplicadas.
)

:: ─── PASO 4: Frontend ──────────────────────────────────────────────────────
echo.
echo [4/4] Compilando y lanzando interfaz de usuario (Next.js)...
start "AutomatizaPyme — Frontend" cmd /k "cd /d "%~dp0frontend" && npm.cmd run build && npm.cmd start"

:: ─── Finalización ──────────────────────────────────────────────────────────
echo.
echo  ✅  PROYECTO LISTO
echo  ══════════════════════════════════════════════════
echo  🌐 Dashboard:    http://localhost:3000
echo  🔧 Backend API:  http://localhost:8080
echo  ══════════════════════════════════════════════════
echo.
echo  Se ha abierto una nueva ventana para el Frontend.
echo  Puedes minimizar esta ventana, pero no la cierres.
echo.
pause
