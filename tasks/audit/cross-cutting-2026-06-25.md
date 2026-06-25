# Auditoría transversal — 2026-06-25

Backend Python (658 ficheros en `app/`), frontend TS, desktop Electron. Sin modificar código.

## Resumen por severidad
- CRITICAL: 0
- HIGH: 1
- MEDIUM: 5
- LOW: 6

---

## HIGH

### H1 — Reset de contraseña: fail-open + token en logs
`app/services/auth/email_reset.py:66-72`. Si `SMTP_HOST`/`SMTP_USER` no están configurados, la función **loguea el `reset_url` completo (con el token de reset) en INFO y devuelve `True`** como si el email se hubiera enviado. En un despliegue sin SMTP esto (a) deja el token de recuperación en `logs/`, y (b) hace que el flujo "diga" que envió el correo cuando no lo hizo (fail-open silencioso).
Fix: en producción, si no hay SMTP, devolver `False`/error en vez de loguear el enlace; gatear el log a un flag explícito de desarrollo.

---

## MEDIUM

### M1 — 7 clientes httpx.AsyncClient persistentes nunca se cierran
`integrations/{boe_scraper,gmail_client,google_drive_client,onedrive_client,outlook_client,psd2,telegram_client}.py`. Cada uno crea `self._client = httpx.AsyncClient(...)` en `__init__` y define `aclose()`, pero **ningún caller invoca `aclose()` y no hay handler `lifespan`/`shutdown`** en la app. Si se instancian por request → leak de conexiones/sockets.
Fix: instanciar como singletons y cerrarlos en el `lifespan` de FastAPI, o usar `async with` por llamada como ya hacen `google_oauth.py`/`microsoft_oauth.py`.

### M2 — SECRET_KEY corta/débil
`.env`: `SECRET_KEY` de 18 chars y `POSTGRES_PASSWORD` de 9 chars. Para firmar JWT 18 bytes es flojo.
Fix: regenerar `SECRET_KEY` ≥ 32 bytes aleatorios; documentar requisito mínimo en `config.py`.

### M3 — Drift requirements.txt: `langfuse` no se instala en desktop
`langfuse` se importa en `core/llm_callbacks.py:105` y `core/observability.py:96`, pero en `pyproject.toml` está como `optional = true` y **no aparece en `requirements.txt`** (que es lo que pip-instala el escritorio). El resto de deps `main` sí casan. Los imports están dentro de `try`, así que degrada sin romper, pero la observabilidad LLM queda muda en desktop pese a `LLM_TRACE_ENABLED=true` en `.env`.
Fix: decidir si langfuse es opcional (entonces no asumir trazas) o incluirlo en el export `--only main`.

### M4 — 117 `except Exception` que devuelven el mensaje crudo de la excepción
Patrón en `agents/*/tools.py` y `_*_tools.py` (de 447 `except Exception` totales): `return f"Error ...: {e}"`. Devuelve detalles internos de la excepción al LLM/usuario sin loguear ni re-lanzar. Riesgo de fuga de internals y de enmascarar fallos. Ninguno es de cálculo fiscal directo, pero p.ej. `billing/_invoice_create_async.py:183-215` traga errores de evento/asiento/documento como `warnings` (la factura se crea aunque el asiento contable falle silenciosamente).
Fix: loguear con `logger.exception` y devolver mensaje genérico; revisar que los `warnings` de facturación no oculten descuadres contables.

### M5 — NIF en logs (RGPD)
`agents/hr/_payroll_calc.py:144,182`: `logger.warning(... %s ..., nif, ...)`. El NIF del empleado va a logs en warnings de nómina.
Fix: omitir/pseudonimizar el NIF en logs.

---

## LOW
- **L1** `.env` contiene secretos OAuth reales en disco (GOOGLE/TWITTER/FACEBOOK_CLIENT_SECRET, LANGFUSE_*, UNSPLASH, OAUTH_PROXY_URL). Está en `.gitignore` (solo `.env.example` trackeado) → no commiteado, OK, pero conviene rotar si la máquina se comparte.
- **L2** `AP_DEVMODE=1` en `.env` **no lo lee ningún código** (0 refs en backend/frontend/desktop) → flag muerto/confuso; eliminar o cablear.
- **L3** `subprocess.Popen(...)` dentro de `async def claude_code_login` en `services/tenant_service.py:343` sin `to_thread`; Popen no bloquea al crear, pero cualquier `.wait()`/`.communicate()` posterior sí.
- **L4** `services/ai/stream_tokens.py:79` `logger.debug("publish token falló (silenciado): %s", e)` — "token" aquí es token de streaming LLM, no credencial (falso positivo, anotado).
- **L5** 4 `asyncio.gather` (`dispatchers/chat.py:206`, `_dispatch_handlers.py:576`, `routes/marketing.py:578`, `ai/node_engine.py:191`): `chat.py` usa `return_exceptions=True` y cada loader abre su propia `AsyncSessionLocal()` (correcto, sin sesión compartida). Verificar que `_dispatch_handlers.py:576` no comparta una misma `db` entre las corutinas de `_execute_one`.
- **L6** Endpoint `GET /generative-ui/debug-llm` (`routes/generative_ui.py:32`) — endpoint de diagnóstico LLM expuesto; confirmar que requiere auth/no filtra config.

---

## Aspectos sólidos (sin hallazgos)
- Numeración de facturas/series: `services/billing/numbering.py` usa `pg_advisory_xact_lock` + `SELECT ... FOR UPDATE` (sin race). VeriFactu chain igual.
- 0 `time.sleep`, 0 `requests.*` síncronos, 0 `except:` desnudos, 0 `open()` sin context manager en `app/`.
- `.env` correctamente en `.gitignore`; requirements.txt marcado como generado y solo `langfuse` diverge.
- Clientes OAuth (`google_oauth`, `microsoft_oauth`) usan `async with httpx.AsyncClient()` por llamada (sin leak).
