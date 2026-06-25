# Auditoría de Seguridad — Backend Python (FastAPI/SQLAlchemy/LangGraph)

Fecha: 2026-06-25 · Alcance: `backend/app/` · Modo: solo lectura, sin modificar código.

Nota metodológica: el RLS global (listener fail-closed + `enforce_tenant`) se confirma sólido;
los usos de `rls_bypass()` revisados (login, register, OAuth/Telegram/AutoFirma callbacks) son
pre-tenant legítimos y re-anclan el tenant tras resolverlo. No se hallaron `text()` con
interpolación ni SQL crudo con f-strings. Los `subprocess` usan `create_subprocess_exec`/listas
de args (sin `shell=True`) con valores derivados de `DATABASE_URL`, no de entrada de usuario.

## Resumen por severidad

| Severidad | Nº |
|-----------|----|
| CRITICAL  | 0  |
| HIGH      | 2  |
| MEDIUM    | 4  |
| LOW       | 3  |

---

## HIGH

| # | Archivo:línea | Descripción | Fix |
|---|---------------|-------------|-----|
| H1 | `services/integration/messaging.py:58-62` (`verify_webhook_secret`) | Si `TELEGRAM_WEBHOOK_SECRET` está vacío (default), la verificación devuelve `True` incondicionalmente: el webhook `/telegram/webhook` (`messaging.py:29`) queda **sin autenticación** y cualquiera puede inyectar updates falsos, disparar el orquestador LLM (coste/abuso) y la vinculación de chats. | Hacer fail-closed: si el secreto no está configurado, rechazar (403) en vez de aceptar; exigir el secreto al registrar el webhook. |
| H2 | `api/v1/routes/signing.py:110-153` (`autofirma_callback`) | Callback público sin auth que acepta el resultado firmado identificándose solo por `session_token` (query/body). No se observa verificación de origen/firma del payload de AutoFirma ni rate-limit en el callback; un atacante que adivine/intercepte el token puede inyectar un `signed_hash` arbitrario en una sesión de firma. | Validar que el `session_token` es de un solo uso y no expirado, añadir `@limiter.limit`, y verificar criptográficamente el contenido firmado antes de persistir el hash. |

---

## MEDIUM

| # | Archivo:línea | Descripción | Fix |
|---|---------------|-------------|-----|
| M1 | `core/security.py` (`create_client_portal_access_token`) | El JWT del portal de cliente dura **7 días** fijos y no es revocable (no consulta `ClientPortalToken.is_active`): revocar el token de portal en BD no invalida los JWT ya emitidos hasta que expiran. | Reducir TTL (p.ej. 1-24h) y validar contra el estado `is_active`/expiración del token de portal en `get_current_client_portal`. |
| M2 | `api/v1/routes/integrations.py:133-150` (`google_callback`) | El HTML de respuesta concatena `settings.FRONTEND_URL` en un `<script>` (`window.location.href='...'`) y hace `postMessage(..., '*')` con `targetOrigin` comodín, exponiendo el mensaje OAuth a cualquier ventana. | Usar `targetOrigin` explícito en `postMessage` y no interpolar config directamente en JS inline. |
| M3 | `services/documents/_tabular.py:93-118` + `routes/documents.py:580` (`import-db`) | `import_database` lee `await file.read()` y `import_tabular_file` guarda en disco **sin límite de tamaño** (a diferencia de `save_file_to_disk`/restore que sí limitan). DoS por memoria/disco con ficheros grandes. | Aplicar el límite de tamaño (50/100MB) antes de leer/guardar en la ruta de import tabular. |
| M4 | `api/v1/routes/admin.py` restore/backup + `services/backup/legacy_local.py` | `PGPASSWORD` se pasa por entorno del subprocess (correcto), pero el `stderr` de `psql` se devuelve al cliente (`detail=f"Error al restaurar: {err}"`, `restore_backup`), pudiendo filtrar rutas/estructura de BD. | No reflejar `stderr` crudo al cliente; loguear server-side y devolver mensaje genérico. |

---

## LOW

| # | Archivo:línea | Descripción | Fix |
|---|---------------|-------------|-----|
| L1 | `core/config.py:21,116` | `SECRET_KEY` tiene default inseguro (mitigado por `check_secrets` que aborta el arranque), pero `TELEGRAM_WEBHOOK_SECRET`/`LANGFUSE_SECRET_KEY` no se validan → ver H1. | Validar también los secretos cuyo vacío degrada la seguridad. |
| L2 | `middleware/security_headers.py:20-30` | Sin `Content-Security-Policy`; HSTS solo en `ENVIRONMENT=="production"`. Cobertura de cabeceras incompleta. | Añadir CSP restrictiva y `Permissions-Policy`. |
| L3 | `middleware/rate_limit.py` (`_client_ip`) | `storage_uri="memory://"`: el rate-limit no es compartido entre workers/procesos; con varios workers el límite efectivo se multiplica. | Usar storage compartido (Redis) si se escala a multi-worker. |

---

### Top 3 más graves
1. **H1** — Telegram webhook sin auth cuando el secreto no está configurado (`verify_webhook_secret` fail-open).
2. **H2** — Callback de firma AutoFirma público sin verificación del payload firmado ni rate-limit.
3. **M1** — JWT de portal de cliente de 7 días no revocable (revocación en BD no surte efecto).
