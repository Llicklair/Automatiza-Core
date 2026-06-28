# Auditoría de Production-Readiness — AutomatizaCore (SaaS ERP multi-tenant España)

**Fecha:** 2026-06-28
**Alcance:** facturación / contabilidad / banca / RRHH / CRM / fiscal AEAT-VeriFactu
**Auditor jefe:** veredicto consolidado sobre hallazgos verificados (effectiveSeverity).

---

## 1. VEREDICTO: NO-GO

**Hay 5 BLOCKERS confirmados** (confidence: high) que impiden el lanzamiento a producción. Tres de ellos tienen impacto fiscal/legal directo bajo RD 1007/2023, RD 1619/2012 y VeriFactu (emisión de facturas duplicadas, incumplimiento de la cadena de anulación, NIF de SIF ficticio enviable a la AEAT). A esto se suma un conjunto amplio de HIGH (18) que en agregado refuerzan el NO-GO: fuga de información sin autenticación, exposición de JWT en URLs/logs, escritura arbitraria de archivos vía LLM y ausencia total de cobertura de tests en los flujos fiscales más críticos.

**Justificación:** un SaaS ERP fiscal no puede lanzarse mientras existan rutas que produzcan documentos fiscales inválidos o duplicados (BLOCKERS 2-5) ni endpoints sin autenticación que filtren topología interna (BLOCKER 1). La base arquitectónica es sólida (RLS fail-closed, cadena de hashes VeriFactu, Decimal en el núcleo de cálculo), lo que hace los blockers **reparables**, pero deben cerrarse antes de cualquier despliegue público.

---

## 2. Resumen por área

| Área | Estado | BLOCKER | HIGH |
|---|---|---|---|
| Aislamiento Multi-Tenant (backend) | NO LISTO | 0 | 0 |
| AUTH/AUTHZ | NO LISTO | 1 | 0 |
| Secretos y configuración de producción | NO LISTO | 0 | 1 |
| Dinero e Impuestos (billing/fiscal/accounting/AEAT) | NO LISTO | 0 | 1 |
| Cumplimiento Fiscal AEAT/VeriFactu | NO LISTO | 2 | 0 |
| Base de Datos y Resiliencia | NO LISTO | 1 | 1 |
| services / agents / workers (Error Handling) | NO LISTO | 1 | 3 |
| LLM / Agentes | NO LISTO | 0 | 1 |
| Uploads / OCR / Documentos | NO LISTO | 0 | 3 |
| API Surface + middleware | NO LISTO | 0 | 2 |
| Frontend Seguridad (JWT/XSS) | NO LISTO | 0 | 3 |
| Frontend Quality (tests/hooks) | NO LISTO | 0 | 1 |
| CI/CD y Tests | NO LISTO | 0 | 1 |
| Observabilidad / Ops | NO LISTO | 0 | 1 |
| **TOTAL (effectiveSeverity)** | **NO-GO** | **5** | **18** |

> Nota: se usan severidades **efectivas** (tras verificación). Tres hallazgos reportados originalmente como BLOCKER fueron rebajados a HIGH/MEDIUM en verificación: `gated_tool_call` (HIGH — no explotable con la API actual), exclusión de cobertura (HIGH), y `mypy` advisory (MEDIUM). No se inventan hallazgos nuevos.

---

## 3. BLOCKERS (5) — deben cerrarse antes de producción

### B1 — GET /system/preconditions expuesto sin autenticación
- **Área:** AUTH/AUTHZ
- **Archivo:** `backend/app/api/v1/routes/system.py:134`
- **Por qué:** El endpoint declara únicamente `Depends(get_db)`, sin `get_current_user` ni `require_role`. Cualquier cliente anónimo recibe la existencia/estado de tablas fiscales críticas (`invoice_series`, `verifactu_chain`, `fiscal_approval_log`) y el estado de migraciones Alembic. Servicio subyacente: `backend/app/services/system/preconditions.py:21-40`. Contrasta con todos los endpoints vecinos (backups, backfill, diagnostic-bundle) que sí usan `_admin_only` / `require_role("admin")`.
- **Fix:** añadir `_: User = Depends(require_role("admin"))` (o como mínimo `get_current_user`) a la firma del handler.

### B2 — NIF del SIF (productor software) es placeholder `B00000000` sin guard en runtime
- **Área:** Cumplimiento Fiscal AEAT/VeriFactu
- **Archivo:** `backend/app/services/billing/registro_facturacion.py:91` (`_s("VERIFACTU_SIF_NIF", "B00000000")`)
- **Por qué:** RD 1007/2023 y Orden HAC/1177/2024 exigen el NIF real del productor homologado en `SistemaInformatico`. `_s()` (líneas 86-91) hace fallback silencioso a `B00000000` si la variable es None/vacía. `default_sistema_informatico()` (línea 78) no valida ni advierte. `PreproduccionSubmitter.submit()` (`backend/app/services/billing/verifactu_submit.py:258`) firma y envía el XML sin ningún guard previo. `PUT /verifactu/config` permite activar modo `voluntary` sin validar el NIF. No hay referencia a `VERIFACTU_SIF_NIF` en `app/core/` (sin validación de arranque).
- **Fix:** en `PreproduccionSubmitter.submit()` o en `default_sistema_informatico()`, lanzar `VerifactuSubmitError` si `settings.VERIFACTU_SIF_NIF` está vacío o es `B00000000`. Documentar como obligatoria en `.env.example`.

### B3 — Anulaciones generan RegistroAlta R1 pero NO RegistroAnulacion en la cadena
- **Área:** Cumplimiento Fiscal AEAT/VeriFactu
- **Archivo:** `backend/app/services/billing/commands.py:242-245`
- **Por qué:** `create_rectificativa` solo llama `maybe_append_verifactu_record(db, invoice=rect)` (RegistroAlta `TipoFactura=R1`). RD 1007/2023 Art. 9 exige además un `RegistroAnulacion` para el registro VeriFactu de la factura original cuando ya fue remitido. `build_registro_anulacion_xml` (`registro_facturacion.py:296`) y `build_payload_anulacion` (`verifactu_chain.py:84-104`) existen pero solo se invocan desde tests (`tests/test_verifactu_registro_xml.py:112`), nunca en producción. El registro original queda vigente en la cadena junto a su R1 → cadena inválida, riesgo de rechazo AEAT.
- **Fix:** en `create_rectificativa`, si la original tiene `VerifactuRecord` remitido, invocar también `append_verifactu_anulacion_record` (a crear) que use `build_payload_anulacion` + `build_registro_anulacion_xml` y encadene la huella antes del commit atómico.

### B4 — Batch de facturas recurrentes: excepción en un item corrompe la sesión y descarta todo el lote
- **Área:** Base de Datos y Resiliencia
- **Archivo:** `backend/app/workers/tasks_scheduler.py:366-413`
- **Por qué:** `_process_recurring_invoices()` (línea 350) abre UNA sola `AsyncSessionLocal()` para todo el loop. El `except` (línea 409) solo hace `logger.error()`: no hay `rollback()` ni savepoint. Cuando cualquier `flush()` falla (`numbering.py:74,77` y `tasks_scheduler.py:391`), SQLAlchemy marca la transacción como "must rollback"; el `db.commit()` final (línea 413) lanza `InvalidRequestError`, descartando TODAS las facturas correctamente generadas. Como `rec.next_run_date` (líneas 406-407) solo se actualiza en el try exitoso, el commit nunca llega y todos los templates se reintentan al día siguiente → riesgo de gap/duplicado en el correlativo (RD 1619/2012 Art. 6.1).
- **Fix:** procesar cada `rec` en su propio savepoint (`async with db.begin_nested() as sp: ... sp.commit()` / `sp.rollback()` en except) o en su propia sub-sesión `AsyncSessionLocal()`. El commit exterior solo persiste lo que tuvo éxito.

### B5 — resume_orchestrator reintenta TODAS las excepciones sin filtro transient → facturas duplicadas
- **Área:** services / agents / workers
- **Archivo:** `backend/app/workers/tasks_orchestrator.py:123-133`
- **Por qué:** A diferencia de `execute_orchestrator` (líneas 92-105, que filtra con `_is_transient_error`), `resume_orchestrator` captura `except Exception` y reintenta 3 veces. Antes del retry, `guard.release()` (línea 125) borra la clave de idempotencia (`idempotency.py:100-111`), garantizando que cada reintento vuelva a ejecutar. `_create_invoice_from_approval` (`_orchestrator_context.py:298-423`) no tiene guard de idempotencia propio: el número se calcula con `SELECT COUNT(*)+1` (líneas 373-376) y la factura se commitea en línea 422. Un error post-commit dispara reintentos que crean facturas adicionales con números FAC distintos → emisión ilegal de facturas duplicadas en un ERP VeriFactu/AEAT.
- **Fix:** aplicar el mismo `_is_transient_error` que `execute_orchestrator`; para errores no-transient, marcar la tarea como failed sin reintentar. Idealmente, verificar antes de insertar si ya existe una Invoice vinculada al `task_id`/`approval_id`.

---

## 4. HIGH (18) — abordar antes o inmediatamente después del lanzamiento

### Seguridad / exposición sin autenticación
- **H1 — `/metrics` sin autenticación (fuga info interna).** `backend/app/middleware/license_check.py:10` (en `_ALLOWED_PREFIXES`) + `backend/app/main.py:230-247`. Servidor por defecto en `0.0.0.0` (`desktop/python-manager.js:256`). Fix: restringir a loopback o exigir `METRICS_TOKEN`.
- **H2 — `/metrics` sin autenticación (fuga datos de negocio por tenant).** `backend/app/main.py:230` + `backend/app/core/observability.py:187-231`: métricas con label `tenant_id` (`tasks_created`, `tasks_completed`, `approvals_pending`). Violación de confidencialidad RGPD. Fix: bearer `METRICS_BEARER_TOKEN` o `require_role("admin")`. *(Mismo endpoint que H1; cerrar conjuntamente.)*
- **H3 — GET /system/preconditions sin auth (filtra esquema BD).** `backend/app/api/v1/routes/system.py:134`. *(Es el mismo endpoint que B1; el fix de B1 lo resuelve. Reportado por dos áreas.)*

### Cálculo monetario / fiscal
- **H4 — `amount_base + tax_amount` puede no sumar `amount_total` (descuadre 1 céntimo).** `backend/app/services/billing/queries.py:92-99`: `amount_total` se redondea sobre la suma exacta mientras `amount_base` y `tax_amount` se redondean individualmente. El descuadre llega al XML VeriFactu y al asiento PGC. Fix: `amount_total = _round2(total_base) + _round2(total_tax)`.

### Workers / resiliencia
- **H5 — Doble commit (service + emit_event) en la misma sesión → 5xx aunque la factura ya esté creada.** `backend/app/api/v1/routes/invoices.py:342-372` + `backend/app/services/event_bus.py:164`. Solo afecta a `create_invoice` (en `create_rectificativa` es FALSO POSITIVO parcial; `update_status` ya está protegido). Fix: `try/except` alrededor de `emit_event`, devolver 201 y reintentar el evento; o outbox pattern.
- **H6 — `gated_tool_call`: `func_name` sin allowlist (defensa en profundidad ausente).** `backend/app/services/workflow/approval_actions.py:311-323`. Solo `module_name` se valida (`startswith("app.")`). No explotable hoy (el payload solo lo escribe el decorador `@gated_tool`, no input de usuario), pero sin allowlist cualquier otro bug de escritura a DB se convierte en ejecución de código. Fix: allowlist explícita `(module, func)` o validar contra `tool_registry`.
- **H7 — Race condition en `invoice_number` (SELECT COUNT) — 3 sitios.** `approval_actions.py:240-243`, `_orchestrator_context.py:373-376`, `services/sales/commands.py:333-338`. El índice único parcial `uq_invoices_tenant_number_emitted` (`db/models/billing.py:49-57`) evita el duplicado para issued/rectificativa, pero la transacción perdedora falla con excepción no manejada y se generan gaps (viola numeración correlativa Art. 6 RD 1619/2012); tipos fuera del filtro (draft) sin protección. Fix: SEQUENCE por tenant o `FOR UPDATE SKIP LOCKED`.
- **H8 — `_load_task_and_approval` traga excepción crítica + `traceback.print_exc()` a stdout.** `backend/app/workers/_orchestrator_context.py:292-295`. La tarea queda colgada en `awaiting_approval` (el caller `tasks_orchestrator.py:385-387` no actualiza estado) y el stacktrace bypassa el scrubber. Fix: `logger.exception()` + `_mark_task_failed(task_id, ...)`.

### LLM / Agentes
- **H9 — Path traversal en `create_document` (`file_name` del LLM sin sanitizar).** `backend/app/agents/agent_tools/documents.py:86`. `os.path.join(upload_dir, file_name)` con ruta absoluta o `../` escribe fuera del upload_dir; contenido controlado por LLM. (`reports.py:158,311` son FALSOS POSITIVOS: usan `_slugify()`.) Fix: `os.path.basename()` + verificar `commonpath` con `upload_dir`.

### Uploads / Documentos
- **H10 — ZIP bomb: sin límite de tamaño descomprimido.** `backend/app/services/documents/_file_ops.py:122` (`z.read(info.filename)` sin chequear `info.file_size`). Call sites: `documents.py:162` y `documents.py:235` → `service.py:257`. Fix: límite por entry y acumulado de bytes descomprimidos.
- **H11 — Path traversal en fallback de `update_content`.** `backend/app/services/documents/service.py:547`. `doc.file_name` se almacena verbatim (`service.py:183`) y se usa en `os.path.join(UPLOAD_DIR, ...)` sin contención. Mismo patrón en `service.py:372,395` y `snapshot.py:34,94,108`. Fix: `normpath` + verificar prefijo `UPLOAD_DIR`, o forzar nombre por UUID.
- **H12 — CV upload sin validación de tipo/tamaño.** `backend/app/services/hr/commands.py:416-424` + endpoint `recruitment.py:66-83`. Extensión tomada del cliente, `copyfileobj` sin cap. `CV_UPLOAD_DIR` ruta relativa sin `abspath`. Fix: allowlist de extensiones + límite de bytes.

### API Surface
- **H13 — Token de portal cliente en query param de URL.** `backend/app/api/v1/routes/client_portal.py:89`; frontend `clientes/portal/page.tsx:109,277`. Token TTL hasta 365 días en URL (logs/Referer/historial). Fix: redeem de un solo uso vía POST o fragmento hash `#token=`.

### Frontend seguridad
- **H14 — JWT access+refresh en localStorage en deployment web/SaaS.** `frontend/src/lib/secureStore.ts:71-78`. Modo web confirmado (`base.ts:9-16`, Cloudflare Tunnel) y sin CSP (`next.config.js:8-24`). XSS lee la sesión completa. Fix: refresh token en cookie httpOnly SameSite=Strict (BFF); access token solo en memoria.
- **H15 — JWT en query param de URL (descarga PDF).** `frontend/src/app/(dashboard)/albaranes/_hooks/useAlbaranes.ts:100`. (`useWarehouseScanner.ts:52` es token efímero scoped — patrón legítimo.) Fix: `fetchBlob()` + `createObjectURL`.
- **H16 — JWT en query param de URL WebSocket.** `frontend/src/lib/hooks/useNotificationSocket.ts:36` + backend `api/ws/notifications.py:78` (`token: str = Query(...)`). Reconexión cada 3s vuelca el token en logs. Fix: conectar sin token y autenticar en el primer frame `onopen`.

### Tests / CI
- **H17 — Gap crítico de tests: cero cobertura en facturación/AEAT/nóminas/banca.** `frontend`: 19 tests para ~588 archivos. `calcLine()` (`useNuevaFactura.tsx:19-23`) sin test; e2e con `test.skip()`. Fix: tests unitarios para `calcLine()` y de integración para `handleSubmit`.
- **H18 — Cobertura backend excluye agents/, compliance/, banking/, idempotency.** `backend/pyproject.toml:150-174` (omit) + gate `ci.yml:158` (`--cov-fail-under=57`). El código fiscal de mayor riesgo no se mide. Fix: eliminar esos omit del coverage.run; umbral separado más bajo si es necesario.

---

## 5. Resumen MEDIUM (31) y LOW (6)

**MEDIUM destacados (no bloqueantes, deuda priorizable):**
- `delete_tenant_knowledge` no registrada en `tool_registry.py:169` (asimetría con get/upsert).
- OAuth callback hace `rls_bypass()` sobre el upsert completo; `_OAUTH_STATES` sin TTL (`integrations.py:144`).
- `POST /auth/reset-password` sin rate-limit (DoS, no brute-force — token de 256 bits) (`auth.py:84`).
- Refresh tokens 30 días sin rotación ni revocación (`services/auth/service.py:145`).
- Credenciales BD hardcoded sin validación de arranque (`config.py:54`).
- Float puro en libro de registro CSV (`reports/fiscal.py:374-394`), retención IRPF (`queries.py:320-321`) e IS estimado `amount_base or amount_total` (`reports/fiscal.py:173-177`).
- `target_metadata = None` en `env.py:56` → autogenerate de migraciones inútil (drift silencioso).
- `_retry` duerme antes del primer intento y no filtra errores permanentes (`tasks_orchestrator.py:50-72`).
- Cost tracking con precios hardcoded Anthropic ignorando proveedor real (`agent_budget.py:155`).
- Prompt injection estructural: `user_intent` sin delimitar (`_plan_handlers.py:320`).
- AutoFirma callback sin cota de body (`signing.py:110-145`); `prepare_download` sin verificar prefijo UPLOAD_DIR (`service.py:387-397`).
- `/advisory/boe?limit` sin cota máxima (`advisory.py:23`); `/import/*` sin cota de filas (`import_bulk.py:50`).
- DOMPurify `ALLOW_DATA_ATTR:true` + tags interactivos sobre HTML de email (`useGenerativeUI.ts:11-30`).
- Token portal-cliente en URL sin guard de producción (`clientes/portal/page.tsx:109`).
- Promesas sin catch / `any` / sin estado de error en hooks de facturación (`useNuevaFactura.tsx:44,50`; `useFacturas.tsx:173`; `clientes/page.tsx`).
- `mypy` 100% advisory + error codes deshabilitados en pyproject (`ci.yml:89-95`, `pyproject.toml:94-148`).

**LOW destacados:**
- `enforce_tenant` fallback `return kwargs` cuando ContextVar es None (`tenant_context.py:54`) — latente, no explotable hoy (el orquestador siempre setea el tenant primero); recomendado fail-closed.
- Telegram background task sin copiar contexto explícito (`messaging.py:88`).
- `GET /` filtra `/docs` en producción (`main.py:369`).
- `AP_DEVMODE=1` variable muerta en `.env:4`.
- Migración 0016 RLS fail-open superada por 0064 — verificar orden de aplicación en arranque.
- Budget guard por tenant desactivado por defecto sin warning (`agent_budget.py:116`).

---

## 6. Plan de remediación priorizado

### Fase 0 — Bloqueante de producción (cerrar TODO antes de lanzar)
1. **B5** — filtrar `_is_transient_error` en `resume_orchestrator` + guard de idempotencia en creación de factura. *(Riesgo legal: facturas duplicadas.)*
2. **B4** — savepoint/sub-sesión por item en el batch recurrente. *(Riesgo: pérdida de lote + gap correlativo.)*
3. **B3** — emitir `RegistroAnulacion` en `create_rectificativa`. *(Incumplimiento RD 1007/2023.)*
4. **B2** — guard en runtime que bloquee envío con NIF SIF placeholder. *(Sanción AEAT.)*
5. **B1** — añadir `require_role("admin")` a `/system/preconditions`. *(Fuga de esquema; fix trivial.)*

### Fase 1 — HIGH de seguridad/fiscal (antes de lanzar o en la primera semana)
6. **H1/H2/H3** — proteger `/metrics` (loopback o token) y confirmar B1.
7. **H4** — corregir descuadre de céntimo en totales de factura. *(Coherencia VeriFactu + PGC.)*
8. **H7** — secuenciador de número de factura por tenant (cierra 3 sitios). *(Numeración correlativa.)*
9. **H9, H10, H11, H12** — sanitización de paths y límites de upload (traversal + ZIP bomb + CV).
10. **H13, H14, H15, H16** — eliminar JWT/tokens de URLs y localStorage (BFF + cookies httpOnly + auth en frame WS).
11. **H5, H8** — desacoplar emit_event del commit de factura; arreglar tarea colgada + scrubber.
12. **H6** — allowlist en `gated_tool_call` (defensa en profundidad).

### Fase 2 — HIGH de calidad/CI (primeras semanas post-lanzamiento)
13. **H18** — incluir agents/compliance/banking/idempotency en cobertura medida.
14. **H17** — tests unitarios de `calcLine()` y de integración de creación de factura.

### Fase 3 — MEDIUM/LOW (deuda continua)
15. Rotación de refresh tokens, rate-limit en reset-password, Decimal en CSV/IRPF/IS.
16. `target_metadata` real en migraciones + `alembic check` en CI.
17. Validación de credenciales BD por defecto, fail-closed en `enforce_tenant`, TTL en `_OAUTH_STATES`.
18. Endurecer `mypy` en rutas fiscales; cotas de body en `/import/*` y `/advisory/boe`.

---

**Conclusión:** NO-GO. La arquitectura es recuperable y los 5 BLOCKERS son acotados y reparables, pero ninguno es opcional en un ERP fiscal español. Cerrar la Fase 0 es condición necesaria; la Fase 1 debería completarse antes de exponer el SaaS a internet público.
