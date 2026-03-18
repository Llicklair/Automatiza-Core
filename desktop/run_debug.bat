@echo off
cd /d "%~dp0"
echo ====================================================
echo   AutomatizaPyme - Lanzador de Depuracion
echo ====================================================
echo.
echo [1/3] Limpiando procesos antiguos...
taskkill /F /IM AutomatizaPyme.exe /T 2>nul
taskkill /F /IM postgres.exe /T 2>nul
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
echo.
echo [2/3] Instalando dependencias necesarias (electron-store)...
call npm.cmd install
echo.
echo [3/3] Lanzando aplicacion desde el codigo fuente arreglado...
echo (ESTA VENTANA MOSTRARA LOS LOGS EN VIVO)
echo.
call npm.cmd start
pause
