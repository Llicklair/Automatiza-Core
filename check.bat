@echo off
setlocal
chcp 65001 >nul

set ROOT=%~dp0
set RUFF=C:\Users\Marcos\AppData\Local\Programs\Python\Python314\Scripts\ruff.exe
set ERRORS=0

echo ==================================================
echo   AutomatizaPyme -- Pre-push checks
echo ==================================================
echo.

:: ── Backend: ruff lint ──────────────────────────────
echo [1/4] Ruff lint (backend)...
"%RUFF%" check "%ROOT%backend\app" --select E,W,F,I --ignore E501,E402,E701,E702,E731,W293 --quiet
if %errorlevel% neq 0 (
    echo [FAIL] ruff check
    set ERRORS=1
) else (
    echo [OK]   ruff check
)
echo.

:: ── Backend: ruff format ────────────────────────────
echo [2/4] Ruff format check (backend)...
"%RUFF%" format "%ROOT%backend\app" --check --quiet
if %errorlevel% neq 0 (
    echo [FAIL] ruff format -- aplicando formato...
    "%RUFF%" format "%ROOT%backend\app" --quiet
    echo [FIXED] Archivos formateados. Haz commit antes de push.
    set ERRORS=1
) else (
    echo [OK]   ruff format
)
echo.

:: ── Frontend: next build ────────────────────────────
echo [3/4] Next.js build (puede tardar 1-2 min)...
cd /d "%ROOT%frontend"
call npm.cmd run build
if %errorlevel% neq 0 (
    echo [FAIL] next build
    set ERRORS=1
) else (
    echo [OK]   next build
)
cd /d "%ROOT%"
echo.

:: ── Resultado ───────────────────────────────────────
echo ==================================================
if %ERRORS% neq 0 (
    echo [FAIL] Corrige los errores antes de hacer push
) else (
    echo [OK] Todo listo para push
)
echo ==================================================
pause
