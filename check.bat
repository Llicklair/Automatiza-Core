@echo off
setlocal
chcp 65001 >nul
set RUFF=C:\Users\Marcos\AppData\Local\Programs\Python\Python314\Scripts\ruff.exe
set ERRORS=0

echo ==================================================
echo   AutomatizaPyme — Pre-push checks
echo ==================================================
echo.

:: ── Backend: ruff lint ──────────────────────────────
echo [1/4] Ruff lint (backend)...
"%RUFF%" check backend\app\ --select E,W,F,I --ignore E501,E402,E701,E702,E731,W293 --quiet
if %errorlevel% neq 0 (
    echo [FAIL] ruff check
    set ERRORS=1
) else (
    echo [OK]   ruff check
)

:: ── Backend: ruff format ────────────────────────────
echo [2/4] Ruff format check (backend)...
"%RUFF%" format backend\app\ --check --quiet
if %errorlevel% neq 0 (
    echo [FAIL] ruff format -- aplicando formato...
    "%RUFF%" format backend\app\ --quiet
    echo [FIXED] ruff format aplicado, vuelve a hacer commit
    set ERRORS=1
) else (
    echo [OK]   ruff format
)

:: ── Frontend: next build (tsc + build) ─────────────
echo [3/4] Next.js build (frontend)...
cd frontend
call npm.cmd run build >nul 2>&1
if %errorlevel% neq 0 (
    echo [FAIL] next build -- ejecuta: cd frontend ^&^& npm run build
    set ERRORS=1
) else (
    echo [OK]   next build
)
cd ..

:: ── Git status ──────────────────────────────────────
echo [4/4] Git status...
git diff --name-only --cached
echo.

:: ── Resultado ───────────────────────────────────────
echo ==================================================
if %ERRORS% neq 0 (
    echo [FAIL] Hay errores — corrigelos antes de hacer push
) else (
    echo [OK] Todo listo para push
)
echo ==================================================
pause
