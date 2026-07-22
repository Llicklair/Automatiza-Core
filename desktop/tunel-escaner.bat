@echo off
title Tunel escaner movil - AutomatizaCore
echo ============================================================
echo  Tunel Cloudflare para el escaner movil (camara sin instalar
echo  certificado). Requiere la app de AutomatizaCore ABIERTA.
echo.
echo  1) Espera a que aparezca la URL https://xxxx.trycloudflare.com
echo  2) Pegala en Inventario ^> Escaner ^> "URL publica / tunel"
echo  3) Genera el QR y escanealo con el movil
echo.
echo  La URL cambia en cada arranque. Cierra esta ventana (o Ctrl+C)
echo  para apagar el tunel, y vacia el campo para volver a la via
echo  local (https://IP:8443, sin internet).
echo ============================================================
echo.
"C:\Program Files (x86)\cloudflared\cloudflared.exe" tunnel --url https://localhost:8443 --no-tls-verify
pause
