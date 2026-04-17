@echo off
setlocal
chcp 65001 >nul

echo ==================================================
echo   Compilador de AutomatizaPyme (Generador de .exe)
echo ==================================================
echo.

:: Verificar que Node.js esta instalado
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] No se ha encontrado Node.js.
    echo Por favor, instala Node.js ^(version 18 o superior^) desde https://nodejs.org/
    echo y vuelve a ejecutar este script.
    echo.
    pause
    exit /b 1
)

:: Verificar que existe .env en la raiz (requerido por electron-builder)
if exist "%~dp0.env" goto env_ok
if not exist "%~dp0.env.example" goto env_missing
echo [AVISO] No se encontro .env en la raiz. Copiando desde .env.example
copy /Y "%~dp0.env.example" "%~dp0.env" >nul
echo [AVISO] Revisa y edita .env con tus credenciales reales antes de distribuir el .exe
echo.
goto env_ok

:env_missing
echo [ERROR] No existe .env ni .env.example en la raiz del proyecto.
echo electron-builder requiere un archivo .env para empaquetar.
pause
exit /b 1

:env_ok

:: Ir a la carpeta desktop relative al script
cd /d "%~dp0desktop"
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro la carpeta 'desktop' dentro del proyecto.
    pause
    exit /b 1
)

echo [1/2] Instalando dependencias de desktop...
:: Usamos call npm.cmd para evitar problemas con la politica de PowerShell
call npm.cmd install
if %errorlevel% neq 0 (
    echo [ERROR] Ocurrio un problema al instalar las dependencias.
    pause
    exit /b 1
)
echo.

echo [2/2] Generando el instalador (.exe)...
call npm.cmd run dist
if %errorlevel% neq 0 (
    echo [ERROR] Ocurrio un problema al generar el ejecutable.
    pause
    exit /b 1
)
echo.

echo ==================================================
echo [EXITO] El proceso ha finalizado correctamente.
echo.
echo Puedes encontrar el instalador compilado listo en:
echo -^> %~dp0desktop\dist\
echo ==================================================
pause
