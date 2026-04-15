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
    echo Por favor, instala Node.js (version 18 o superior) desde https://nodejs.org/
    echo y vuelve a ejecutar este script.
    echo.
    pause
    exit /b 1
)

:: Ir a la carpeta desktop relative al script
cd /d "%~dp0desktop"
if %errorlevel% neq 0 (
    echo [ERROR] No se encontro la carpeta 'desktop' dentro del proyecto.
    pause
    exit /b 1
)

echo [1/2] Instalando herramientas de compilacion...
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
