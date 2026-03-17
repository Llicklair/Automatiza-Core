@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

set DB_CONTAINER=atomatizaciondeempresas-db-1
set DB_USER=pyme_user
set DB_NAME=pyme_db
set BACKUP_DIR=%~dp0backups
set KEEP_LAST=7

:MENU
cls
title AutomatizaPyme - Panel de Control
echo.
echo  ================================================
echo       AutomatizaPyme  -  Panel de Control
echo  ================================================
echo.
call :STATUS_LINE
echo.
echo  -- PROYECTO -------------------------------------
echo    [1]  Arrancar proyecto completo
echo    [2]  Parar contenedores
echo    [3]  Reiniciar contenedores
echo    [4]  Reconstruir imagenes  (tras cambios)
echo  -- BASE DE DATOS --------------------------------
echo    [5]  Hacer backup ahora
echo    [6]  Restaurar backup
echo    [7]  Aplicar migraciones  (alembic upgrade)
echo  -- DIAGNOSTICO ----------------------------------
echo    [8]  Ver logs en tiempo real
echo    [9]  Estado de contenedores
echo   [10]  Abrir dashboard  (http://localhost:3000)
echo   [11]  Abrir API docs   (http://localhost:8080/docs)
echo  -------------------------------------------------
echo    [0]  Salir
echo  -------------------------------------------------
echo.
set /p OPCION=  Elige una opcion:

if "%OPCION%"=="1"  goto ARRANCAR
if "%OPCION%"=="2"  goto PARAR
if "%OPCION%"=="3"  goto REINICIAR
if "%OPCION%"=="4"  goto REBUILD
if "%OPCION%"=="5"  goto BACKUP
if "%OPCION%"=="6"  goto RESTAURAR
if "%OPCION%"=="7"  goto MIGRACIONES
if "%OPCION%"=="8"  goto LOGS
if "%OPCION%"=="9"  goto ESTADO
if "%OPCION%"=="10" goto ABRIR_DASH
if "%OPCION%"=="11" goto ABRIR_API
if "%OPCION%"=="0"  goto FIN
echo.
echo  Opcion no valida. Pulsa una tecla...
pause >nul
goto MENU


:: =============================================================================
:ARRANCAR
cls
echo.
echo  ================================================
echo       Arrancando proyecto...
echo  ================================================
echo.
echo  [1/4] Comprobando Docker...
docker info >nul 2>&1
if %errorlevel% equ 0 (
    echo        Docker ya esta corriendo.
    goto docker_ok
)
echo        Iniciando Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
echo        Esperando a que Docker arranque...
:wait_docker_loop
ping 127.0.0.1 -n 4 >nul
docker info >nul 2>&1
if %errorlevel% neq 0 goto wait_docker_loop

:docker_ok
echo        Docker listo!
echo.
echo  [2/4] Iniciando contenedores...
docker-compose up -d
if %errorlevel% neq 0 (
    echo        ERROR: Fallo docker-compose.
    pause
    goto MENU
)
echo.
echo  [3/4] Esperando base de datos...
:wait_db_loop
ping 127.0.0.1 -n 3 >nul
docker-compose exec -T db pg_isready -U %DB_USER% -d %DB_NAME% >nul 2>&1
if %errorlevel% neq 0 goto wait_db_loop
echo        Base de datos lista!
echo        Aplicando migraciones...
docker-compose exec -T api alembic upgrade head
if %errorlevel% neq 0 (
    echo        AVISO: Migraciones fallaron o ya estaban aplicadas.
)
echo.
echo  [4/4] Lanzando frontend (Next.js)...
echo        Liberando puerto 3000 si esta ocupado...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
)
ping 127.0.0.1 -n 2 >nul
start "AutomatizaPyme - Frontend" cmd /k "cd /d "%~dp0frontend" && npm.cmd run build && npm.cmd start"
echo.
echo  ================================================
echo   PROYECTO LISTO
echo   Dashboard : http://localhost:3000
echo   API Docs  : http://localhost:8080/docs
echo  ================================================
echo.
echo  Pulsa cualquier tecla para volver al menu...
pause >nul
goto MENU


:: =============================================================================
:PARAR
cls
echo.
echo  Parando contenedores...
docker-compose down
echo  Liberando puerto 3000...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":3000 " ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
)
echo.
echo  Todo parado. Pulsa una tecla...
pause >nul
goto MENU


:: =============================================================================
:REINICIAR
cls
echo.
echo  Reiniciando contenedores...
docker-compose restart
echo.
echo  Reinicio completado. Pulsa una tecla...
pause >nul
goto MENU


:: =============================================================================
:REBUILD
cls
echo.
echo  Reconstruyendo imagenes (puede tardar varios minutos)...
echo.
docker-compose down
docker-compose build --no-cache
docker-compose up -d
echo.
echo  Aplicando migraciones...
ping 127.0.0.1 -n 6 >nul
docker-compose exec -T api alembic upgrade head
echo.
echo  Rebuild completado. Pulsa una tecla...
pause >nul
goto MENU


:: =============================================================================
:BACKUP
cls
echo.
echo  ================================================
echo       Backup de Base de Datos
echo  ================================================
echo.
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

for /f "tokens=1-3 delims=/" %%a in ('date /t') do set FECHA=%%c-%%b-%%a
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set HORA=%%a%%b
set FILENAME=backup_%FECHA%_%HORA%.sql

echo  Destino: %BACKUP_DIR%\%FILENAME%
echo.
docker inspect --format="{{.State.Running}}" %DB_CONTAINER% 2>nul | findstr "true" >nul
if %errorlevel% neq 0 (
    echo  ERROR: El contenedor de BD no esta corriendo. Arranca primero.
    pause
    goto MENU
)
echo  Exportando base de datos...
docker exec %DB_CONTAINER% pg_dump -U %DB_USER% -d %DB_NAME% --no-password > "%BACKUP_DIR%\%FILENAME%"
if %errorlevel% neq 0 (
    echo  ERROR: El backup fallo.
    if exist "%BACKUP_DIR%\%FILENAME%" del "%BACKUP_DIR%\%FILENAME%"
    pause
    goto MENU
)
for %%A in ("%BACKUP_DIR%\%FILENAME%") do set SIZE=%%~zA
if %SIZE% LSS 1000 (
    echo  ERROR: El archivo generado esta vacio.
    del "%BACKUP_DIR%\%FILENAME%"
    pause
    goto MENU
)
echo  Backup OK: %FILENAME%  (%SIZE% bytes)
echo.
echo  Limpiando backups antiguos (conservando los ultimos %KEEP_LAST%)...
set COUNT=0
for /f "delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\backup_*.sql" 2^>nul') do (
    set /a COUNT+=1
    if !COUNT! GTR %KEEP_LAST% (
        echo    Eliminando: %%F
        del "%BACKUP_DIR%\%%F"
    )
)
echo.
echo  Backup completado. Pulsa una tecla...
pause >nul
goto MENU


:: =============================================================================
:RESTAURAR
cls
echo.
echo  ================================================
echo       Restaurar Base de Datos
echo  ================================================
echo.
if not exist "%BACKUP_DIR%" (
    echo  No existe la carpeta de backups: %BACKUP_DIR%
    pause
    goto MENU
)
echo  Backups disponibles:
echo.
set IDX=0
for /f "delims=" %%F in ('dir /b /o-d "%BACKUP_DIR%\backup_*.sql" 2^>nul') do (
    set /a IDX+=1
    set FILE_!IDX!=%%F
    for %%S in ("%BACKUP_DIR%\%%F") do set SZ=%%~zS
    set /a SZ_KB=!SZ! / 1024
    echo    [!IDX!]  %%F  (!SZ_KB! KB^)
)
if %IDX% EQU 0 (
    echo  No hay backups disponibles.
    pause
    goto MENU
)
echo.
set /p CHOICE=  Elige numero (1-%IDX%) o Enter para cancelar:
if "%CHOICE%"=="" goto MENU
set SELECTED=!FILE_%CHOICE%!
if "!SELECTED!"=="" (
    echo  Opcion invalida.
    pause
    goto MENU
)
echo.
echo  ADVERTENCIA: Sobreescribira TODOS los datos actuales.
echo  Seleccionado: !SELECTED!
echo.
set /p CONFIRM=  Escribe SI para confirmar:
if /i not "%CONFIRM%"=="SI" (
    echo  Cancelado.
    pause
    goto MENU
)
docker inspect --format="{{.State.Running}}" %DB_CONTAINER% 2>nul | findstr "true" >nul
if %errorlevel% neq 0 (
    echo  ERROR: El contenedor de BD no esta corriendo.
    pause
    goto MENU
)
echo.
echo  Restaurando !SELECTED!...
docker exec -i %DB_CONTAINER% psql -U %DB_USER% -d %DB_NAME% < "%BACKUP_DIR%\!SELECTED!"
if %errorlevel% neq 0 (
    echo  ERROR: La restauracion fallo.
    pause
    goto MENU
)
echo.
echo  Base de datos restaurada. Pulsa una tecla...
pause >nul
goto MENU


:: =============================================================================
:MIGRACIONES
cls
echo.
echo  Aplicando migraciones Alembic...
echo.
docker-compose exec -T api alembic upgrade head
echo.
echo  Listo. Pulsa una tecla...
pause >nul
goto MENU


:: =============================================================================
:LOGS
cls
echo.
echo  Elige servicio:
echo    [1]  Todos
echo    [2]  API
echo    [3]  Worker
echo    [4]  Base de datos
echo.
set /p LSVC=  Opcion:
if "%LSVC%"=="2" ( docker-compose logs -f api )   & goto MENU
if "%LSVC%"=="3" ( docker-compose logs -f worker ) & goto MENU
if "%LSVC%"=="4" ( docker-compose logs -f db )     & goto MENU
docker-compose logs -f
goto MENU


:: =============================================================================
:ESTADO
cls
echo.
echo  ================================================
echo       Estado de Contenedores
echo  ================================================
echo.
docker-compose ps
echo.
echo  Uso de recursos:
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo.
pause
goto MENU


:: =============================================================================
:ABRIR_DASH
start http://localhost:3000
goto MENU

:ABRIR_API
start http://localhost:8080/docs
goto MENU


:: =============================================================================
:STATUS_LINE
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo  Estado: Docker APAGADO
    exit /b
)
docker-compose ps 2>nul | findstr "Up" >nul
if %errorlevel% equ 0 (
    echo  Estado: CORRIENDO  ^|  http://localhost:3000
) else (
    echo  Estado: Docker activo pero contenedores PARADOS
)
exit /b


:: =============================================================================
:FIN
echo.
echo  Hasta luego!
echo.
exit /b 0
