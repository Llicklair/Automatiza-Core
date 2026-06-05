@echo off
cd /d "%~dp0"
echo ============================================================
echo   Sincronizando codigo fuente al .exe instalado
echo   (npm run sync:rebuild  =  node sync.js --rebuild-frontend)
echo ============================================================
echo.
call npm.cmd run sync:rebuild
echo.
echo ============================================================
echo   SYNC TERMINADO  -  codigo de salida: %errorlevel%
echo   (cierra esta ventana y relanza la app)
echo ============================================================
pause
