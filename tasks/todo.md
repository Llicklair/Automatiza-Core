# Limpieza de menús e interfaz — sidebar

Fecha: 2026-05-04
Archivo central: `frontend/src/components/layout/nav-config.ts`

## Contexto

El sidebar tiene varios labels duplicados y páginas reales que no aparecen. Las
páginas `/tareas`, `/actividades`, `/aprobaciones` no son huérfanas: son
redirects intencionales hacia `/mi-equipo` y `/bandeja` (URLs legacy). No se
tocan.

## Cambios propuestos

### 1. Renombrar item top "Tareas" → "Mi equipo"
- **Por qué**: el label dice "Tareas" pero `href = /mi-equipo`. Engaña y choca
  con `Proyectos › Tareas`.
- **Cómo**: en `nav-config.ts:30`, cambiar `label: "Tareas"` por
  `label: "Mi equipo"`. Mantener icono `Sparkles` o cambiar a `Users2`.
- **Riesgo**: ninguno. Solo afecta al label visible y `ROUTE_LABELS`.

### 2. Diferenciar "Calendario" duplicado
- **Por qué**: top-level `/calendario` y `CRM › Calendario` (`/crm/calendario`)
  comparten label exacto.
- **Cómo**: renombrar el de CRM a "Calendario CRM" o "Eventos comerciales"
  (`nav-config.ts:68`). El del top queda como "Calendario".
- **Riesgo**: ninguno.

### 3. Aplanar la sección "Integraciones"
- **Por qué**: la sección padre se llama "Integraciones" y tiene un hijo
  "Conexiones" (`/integraciones`) y otro "Mensajería"
  (`/configuracion/integraciones`). Confuso.
- **Cómo**:
  - Convertir "Integraciones" en item plano apuntando a `/integraciones`
    (sin subItems).
  - Mover "Mensajería" → `/configuracion/integraciones` dentro del submenú
    "Configuración" como una entrada más.
- **Riesgo**: ninguno. Las URLs no cambian.

### 4. Añadir páginas reales que faltan en el sidebar
- **`/correos`** → bajo "Herramientas" como "Correos" (icono `Mail`).
- **`/excel`** → bajo "Herramientas" como "Importar Excel"
  (icono `FileSpreadsheet`).
- **Riesgo**: ninguno, son enlaces nuevos.

### 5. (OPCIONAL — pendiente de tu visto bueno) hubs de sección sin enlace
Páginas raíz que existen pero no se exponen en el sidebar:
`/ventas`, `/compras`, `/crm`, `/contabilidad`, `/rrhh`, `/tesoreria`,
`/inventario`, `/configuracion`. Antes de tocar nada, hay que confirmar si
contienen un panel resumen útil o si solo son scaffolding. Si son útiles,
añadirlas como primera subentrada "Resumen" en cada submenú padre.

### 6. (NO TOCAR salvo que pidas) etiquetas vs URL
- `Tesorería › Cuentas` → `/banca`
- `Inventario › Productos` → `/catalogo`
Son URLs legacy con label correcto. No rompe nada; renombrar la URL implicaría
mover páginas y migrar imports. Dejarlo.

## Verificación post-cambio

1. `tsc --noEmit` en `frontend/`.
2. Abrir el sidebar en cada sección y confirmar que:
   - "Mi equipo" aparece en lugar de "Tareas".
   - No hay dos "Calendario" iguales.
   - "Integraciones" es un item plano y "Mensajería" vive en Configuración.
   - "Correos" e "Importar Excel" aparecen en Herramientas.
3. `gitnexus_detect_changes()` para confirmar que solo cambia
   `nav-config.ts` (+ posibles imports de iconos nuevos).

## Estado

- [ ] 1. Renombrar "Tareas" → "Mi equipo"
- [ ] 2. Diferenciar "Calendario" CRM
- [ ] 3. Aplanar "Integraciones"
- [ ] 4. Añadir "Correos" y "Excel" en Herramientas
- [ ] 5. Decidir sobre hubs de sección (requiere confirmación)
- [ ] 6. Verificación tsc + sidebar visual

---

# Auditoría global — refactor + limpieza + debug

Fecha: 2026-05-16
Estado: pendiente de validación

## Contexto

Auditoría completa del proyecto (147.716 LOC, 7.887 nodos / 19.784 edges en
GitNexus). Frontend TS limpio, backend con varios hallazgos accionables.

Herramientas usadas: `npx tsc --noEmit`, `npm run lint`, `ruff`, `mypy`,
`pytest --collect-only`, scripts AST/heurística sobre el árbol.

---

## P0 — Bugs reales (corregir cuanto antes)

### 0. `app.services.backup.__init__` no reexporta símbolos legacy (16 tests fallan)
**Descubierto al correr la suite completa.** 16 fallos en `tests/test_backup.py`,
todos con `AttributeError`:
- `module 'app.services.backup' has no attribute 'settings'`
- `module 'app.services.backup' has no attribute '_find_pg_dump'`
- `module 'app.services.backup' has no attribute 'parse_db_url'` (inferido)
- `module 'app.services.backup' has no attribute 'BACKUP_DIR'` (inferido)

**Causa:** `backup.py` se convirtió en paquete `backup/` (commits `5bd0e59`
+ `14d7b1f`). El commit `14d7b1f` intenta "restaurar símbolos legacy" pero
no expone `settings`, `_find_pg_dump`, `parse_db_url` desde `__init__.py`.

**Fix:** añadir reexports en `backend/app/services/backup/__init__.py`:
```python
from app.core.config import settings  # noqa: F401
from app.services.backup.legacy_local import (  # noqa: F401
    _find_pg_dump,
    parse_db_url,
    create_backup,
    list_backups,
    delete_backup,
    resolve_safe,
    get_backup_path,
    run_backup_job,
)
```
(ajustar a los nombres reales tras inspeccionar `legacy_local.py`).

**Alternativa más limpia:** reescribir `test_backup.py` para importar
directamente desde los submódulos donde viven los símbolos
(`app.services.backup.legacy_local`).

### 1. `db.delete()` sin `await` borra silenciosamente sin ejecutar
**Archivo:** `backend/app/agents/workflow/agent.py:164`
```python
if action == "delete":
    db.delete(existing_wf)         # ← falta await
    await db.commit()
```
`AsyncSession.delete` es corrutina en SQLAlchemy 2.0+. Sin `await` queda como
coroutine no consumida y el delete depende del flush implícito del commit
(puede o no aplicarse). Mypy lo detecta como `[unused-coroutine]`.

**Fix:** `await db.delete(existing_wf)`.

**Riesgo:** medio — flujo de "borrar workflow desde el agente" puede no
funcionar de forma consistente entre versiones SQLAlchemy.

### 2. Test desactualizado `test_five_tools_registered`
**Archivo:** `backend/tests/test_accounting_agent.py:32`
El agente `accounting` ahora registra 7 tools (`create_pdf_report` y
`create_pdf_text_report` añadidos posteriormente) pero el test sigue
afirmando `len(tools) == 5`.

**Fix:** actualizar a `== 7` y extender `test_tool_names` para incluir las
dos nuevas tools.

### 3. Reverso de albarán confirmado deja stock fantasma
**Archivos:** `backend/app/services/sales/commands.py` (`delete_albaran`,
`update_albaran_status`). Documentado en `tasks/lessons.md` (Step 4 inventario).

`DELETE /albaranes/{id}` sobre un albarán `confirmed` borra el albarán y sus
líneas pero NO genera StockMovement compensatorio. Igual ocurre con
`PATCH /status` de `confirmed → draft`. Resultado: `product.stock_quantity`
queda menor que la realidad.

**Fix mínimo (bloqueo defensivo):** rechazar con 409 si el status es
`confirmed`/`delivered`. Cliente debe pasar primero a `draft` (lo que
también requiere implementar la reversa).

**Fix completo:** generar `StockMovement` tipo `entrada` con
`reference=DELIVERY_NOTE_REVERSED:<id>` al revertir.

### 4. Variable redefinida + type errors TypedDict en orchestrator
- `backend/app/agents/orchestrator/_plan_handlers.py:331` — `params` ya
  definido en línea 213 (`[no-redef]`).
- `backend/app/agents/orchestrator/_plan_handlers.py:416` — TypedDict item
  `agent` recibe `Column[str]` en vez de `str`.
- `backend/app/agents/orchestrator/classifier.py:559` — TypedDict item
  `classified_domain` recibe `Column[str]` en vez de `str | None`.

**Fix:** renombrar la segunda `params` y aplicar `str(...)` explícito al
construir los TypedDict.

### 5. Componente con `fetch()` directo (viola regla frontend)
**Archivo:** `frontend/src/app/(dashboard)/configuracion/mantenimiento/page.tsx`
Hace 2 llamadas a `fetch()` saltándose `lib/api/client.ts` (no maneja JWT
refresh ni errores estándar).

**Fix:** mover a `lib/api/mantenimiento.ts` (o módulo existente afín) y
consumirlo desde el componente.

### 6. `useEffect` con dependencia `load` ausente
6 archivos con `react-hooks/exhaustive-deps`:
- `bienvenida/page.tsx:105`
- `configuracion/autonomia/page.tsx:68`
- `configuracion/regap/page.tsx:56`
- `configuracion/verifactu/page.tsx:39`
- `inventario/stock/_hooks/useStock.ts:80`
- `rrhh/gastos/page.tsx:99`

**Fix:** envolver `load` en `useCallback` y añadirla a deps, o mover `load`
dentro del `useEffect`. Suprimir con comentario justificado solo si es
intencional (carga única en mount).

---

## P1 — Refactor estructural

### 7. Rutas con demasiado código (regla "ZERO business logic" en routes/)
- `backend/app/api/v1/routes/hr.py` — 746 líneas
- `backend/app/api/v1/routes/documents.py` — 518 líneas

Las rutas deben validar + delegar. Extraer la lógica restante a
`services/hr/` y `services/documents/`.

### 8. Funciones gigantes (>200 líneas) en generadores PDF
- `services/pdf_reports/_snapshot_monthly.py:32 generate_snapshot_pdf` — 464 líneas
- `services/pdf/_payroll.py:32 generate_payroll_pdf` — 369 líneas
- `services/pdf/albaranes.py:30 generate_albaran_pdf` — 242 líneas
- `services/pdf_reports/_operational_treasury.py:59 generate_cashflow_report_pdf` — 241 líneas

Partir por secciones del documento (header, body, footer, tablas).

### 9. Dispatchers del orchestrator demasiado largos
- `agents/orchestrator/dispatchers/reports.py:30 _dispatch_report` — 220 líneas
- `agents/orchestrator/dispatchers/billing.py:20 _dispatch_billing` — 192 líneas
- `agents/orchestrator/_plan_handlers.py:165 _plan_from_llm` — 189 líneas
- `agents/orchestrator/_dispatch_handlers.py:452 dispatch_node` — 153 líneas

Partir por acción concreta (`_dispatch_report_pdf`, `_dispatch_report_excel`).

### 10. Páginas frontend monolíticas
- `frontend/src/app/(dashboard)/portal/page.tsx` — 752 líneas
- `frontend/src/app/(dashboard)/analitica/page.tsx` — 712 líneas

Extraer subcomponentes y hooks en `_components/` y `_hooks/` locales.

### 11. Services importando agents (rompe pirámide)
- `services/ai/node_dispatch.py`, `node_engine.py`, `node_graph_helpers.py`
- `services/email_sender.py`
- `services/integration/heartbeat.py`
- `services/workflow/_execution.py`

Decisión pendiente: ¿servicios pueden invocar agents (vía orchestrator) o
debe ser solo al revés? Si es "solo al revés", revertir la dependencia con
callbacks o eventos.

---

## P2 — Limpieza (ruff)

### 12. `ruff check --fix` (242 issues auto-corregibles)
**Comando:** `ruff check backend --config backend/pyproject.toml --fix`

Auto-fixables:
- 60 I001 imports desordenados
- 58 UP017 `datetime.timezone.utc` → `datetime.UTC`
- 25+53 F401 imports no usados (app + tests)
- 20 UP006 `Dict/List` → `dict/list`
- 16 UP041 `asyncio.TimeoutError` → `TimeoutError`
- 12 UP037 anotaciones citadas innecesarias
- 10 UP012 `.encode("utf-8")` redundante
- 7 UP038 isinstance con tupla
- 3 F841 variables no usadas
- 2 UP015 modos `open()` redundantes
- 1 UP034 paréntesis sobrantes

**Riesgo:** bajo (auto-fix solo aplica cambios seguros). Revisar diff antes
de commitear.

### 13. Manual ruff (no auto-fixable)
- 339 E501 line-too-long
- 37 E402 imports tardíos (puede ser intencional — circular imports)
- 30 UP007 `Optional[X]` → `X | None`
- 18 UP035 imports deprecados (`typing.Dict` etc.)
- 13 E702 statements separados por `;`
- 6 E741 nombres ambiguos (`l`, `O`, `I`)

### 14. Limpieza estilística
- 10 TODOs y 2 XXX — revisar y resolver o convertir a issues
- 102 `except Exception:` en agents/services — auditar si tragan errores
  que deberían propagarse
- 1 `print()` en `services/event_bus.py` — sustituir por logger

### 15. Doble barrel `lib/api.ts` + `lib/api/index.ts` (deuda documentada)
Documentado en `tasks/lessons.md` (2026-05-15). Reemplazar contenido de
`frontend/src/lib/api.ts` por `export * from "./api/index";` y auditar
colisiones de nombres.

### 16. `<img>` → `<Image>` en Next.js
- `frontend/src/app/(auth)/login/page.tsx:166`
- `frontend/src/components/layout/Sidebar.tsx:202`

Cosmético (LCP). Bajo impacto.

---

## P3 — Validación pendiente (manual)

### 17. Suite completa de tests
`pytest --collect-only` reporta 1268 tests. La ejecución entera supera el
timeout del entorno de auditoría. Hallazgos parciales:
- 1 fallo confirmado: `test_accounting_agent::test_five_tools_registered`
- Más fallos visibles en el progress bar (29–35 %) no recogidos.

**Acción:** correr localmente
`py -3.11 -m pytest -m "not slow and not e2e" --tb=line -q` y añadir cada
fallo a esta sección como P0/P1.

### 18. Mypy stubs faltantes (cosmético)
Librerías sin stubs: `pandas`, `lxml`, `jose`, `redis`, `celery`,
`langfuse`, `prometheus_client`, `xhtml2pdf`, `opendataloader_pdf`.

**Opciones:** (a) `pip install pandas-stubs types-redis types-python-jose
lxml-stubs` o (b) añadir cada una a la lista de
`[[tool.mypy.overrides]] ignore_missing_imports = true` (ya existe para
langgraph/langchain).

---

## Plan de ataque sugerido

1. **Sesión 1 (este turno o el siguiente):** P0 #1 (delete sin await), P0
   #2 (test 5→7), P0 #4 (no-redef + TypedDict casts), P2 #12
   (`ruff --fix`). Tests + commit por bloque.
2. **Sesión 2:** P0 #3 (reverso albarán — decisión de diseño previa), P0 #5
   (fetch en mantenimiento), P0 #6 (exhaustive-deps por archivo).
3. **Backlog:** P1 (refactor de archivos largos, uno por sesión), P2
   manual, P3 #17 (correr suite y triagear fallos).

## Self-check antes de marcar completado

- [ ] `npx tsc --noEmit` sigue en EXIT 0
- [ ] `ruff check backend` baja a <100 issues
- [ ] `py -3.11 -m pytest backend/tests/test_accounting_agent.py` todo en verde
- [ ] `npm run lint` mantiene 0 errores (warnings tolerados solo si están justificados)
- [ ] `npx gitnexus analyze` ejecutado tras los cambios

## Estado auditoría

- [x] P0 #0 backup package reexports (test ahora importa de legacy_local)
- [x] P0 #1 delete sin await
- [x] P0 #2 test 5→7
- [x] P0 #3 bloqueo defensivo albaran (409 confirmed/delivered) — reversa completa queda como tarea futura
- [x] P0 #4 no-redef + TypedDict casts
- [x] P0 #5 fetch en mantenimiento → system.*
- [x] P0 #6 exhaustive-deps (6 archivos con useCallback)
- [ ] P1 #7 rutas hr/documents
- [ ] P1 #8 funciones PDF gigantes
- [ ] P1 #9 dispatchers orchestrator
- [ ] P1 #10 páginas frontend monolíticas
- [ ] P1 #11 services→agents (decisión arquitectura)
- [x] P2 #12 ruff --fix (607 fixes, 252 archivos)
- [ ] P2 #13 ruff manual (732 issues restantes)
- [ ] P2 #14 TODOs / except Exception / print
- [ ] P2 #15 doble barrel api
- [ ] P2 #16 img → Image
- [x] P3 #17 suite completa ejecutada (1206 pass, 16 fail en test_backup)
- [ ] P3 #18 mypy stubs
