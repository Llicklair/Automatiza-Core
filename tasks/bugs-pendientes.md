# Auditoría de `tasks/lessons.md` vs código actual

> Generado 2026-06-22. Cada item se verificó contra el código (no contra el texto de la lección).
> Clasificación: ABIERTO / RESUELTO / PARCIAL / NO-VERIFICABLE.
> Ordenado por severidad (alta → baja).

| Item (fecha lección) | Clasificación | Evidencia (file:line) | Severidad | Esfuerzo |
|---|---|---|---|---|
| Wrapper Electron NO surfacing fallos de `alembic upgrade head` (2026-05-20) | **ABIERTO** | `desktop/service-manager.js:575` llama `runMigrations(...)` sin capturar el retorno; `desktop/python-manager.js:444-447` devuelve `false` en fallo pero nadie lo comprueba; el arranque sigue a `startBackend()`. | alta | media |
| Endpoint admin `/api/v1/admin/db-status` (current vs head revision) (2026-05-20) | **ABIERTO** | Sin coincidencias de `db-status`/`db_status` en `backend/app/api`. No existe. | media | media |
| Marca persistente `migrations_blocked.txt` en APPDATA (2026-05-20) | **ABIERTO** | `migrations_blocked` solo aparece en `tasks/lessons.md:208`. No se escribe en ningún sitio. | media | baja |
| HR toolkit no aplica `_isolated()` → prompt injection cross-tenant (2026-05-09, "Bug pendiente") | **RESUELTO** | `backend/app/agents/hr/agent.py:59-61` importa `isolated as _isolated` y hace `tools = _isolated(tools)`. | — | — |
| Path fallback Linux `/app/uploads` en Windows (2026-05-09) | **RESUELTO** | `backend/app/agents/agent_tools/reports.py:32-62` `_resolve_upload_dir` es platform-aware (Win→AppData, POSIX→cwd) y rechaza explícitamente `/app/uploads`; `backend/app/core/paths.py:24-43` `app_data_dir` (AppData/XDG). Las únicas menciones a `/app/uploads` son la guarda que lo descarta. | — | — |
| `os.environ.get("DIR", "/app/...")` disperso por tools (2026-05-09) | **RESUELTO** | Rutas centralizadas en `core/paths.py`; usos restantes de `environ.get(...DIR)` son legítimos (`LLM_TRACE_DIR`, `AUTOMATIZA_APPDIR`, `CV_UPLOAD_DIR` relativo), sin fallback POSIX hardcodeado. | — | — |
| Reverso de stock al borrar/desconfirmar albaranes (2026-05-15, deuda técnica) | **RESUELTO** | `backend/app/services/sales/commands.py:480-484` `_albaran_stock_reverse_reference` (`DELIVERY_NOTE_REVERSED:<id>`); `:549` `_revert_stock_for_albaran` (entrada idempotente); cableado en `update_albaran_status:647-650` (confirmed/delivered→draft) y `delete_albaran:670-672`. | — | — |
| Clasificar `action` por substring en respuesta del LLM (`kw in text.lower()`) (2026-05-08) | **RESUELTO** | `dispatchers/billing.py:62-105` decide `action` desde `intent` (`kw in _intent_lower`) + detección estructurada de fallo, NO desde el texto del LLM. Sin coincidencias de `kw in text.lower()` sobre la respuesta en `dispatchers/`. | — | — |
| `await db.add(...)` (no awaitable) en SQLAlchemy async (2026-06-14, marcado OBSOLETO) | **RESUELTO** | Sin coincidencias de `await db.add(` en `backend`. Confirma la corrección OBSOLETA de la propia lección. | — | — |
| Custom-employee timeout no propaga (2026-05-08) | **RESUELTO** | La propia lección registra "Bug RESUELTO 2026-05-19" (`lessons.md:486`); fix en `_dispatch_handlers.py` (`_release_employee`). | — | — |

## Notas de verificación

- El item de surfacing de migraciones es el único con impacto operativo claro: una migración con guard que hace `raise` (caso 0028 del historial) deja la BD en revisión vieja sin avisar al usuario, y el call site **descarta** el `false`. Para cerrarlo bastaría comprobar el retorno de `runMigrations` y abortar/notificar (ya existe `dialog.showErrorBox` en `desktop/main.js:302`).
- Los tres items ABIERTOS pertenecen a la MISMA lección (2026-05-20) y son complementarios (surfacing + endpoint + marker). Son mejoras de observabilidad, no bugs activos de datos.
- No hubo items NO-VERIFICABLES: todos se confirmaron por código estático. El comportamiento runtime del surfacing (que el `false` se ignore) está confirmado por inspección del call site, no requiere ejecución.
