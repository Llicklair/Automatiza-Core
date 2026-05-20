# Lecciones aprendidas

Registro de patrones detectados durante el trabajo para no repetir errores.

---

## 2026-05-20 — Electron arranca `alembic upgrade head` en silencio: fallos quedan invisibles

**Contexto**: Aplicando la migración 0029 (AIEmployee contract) tras una sesión
de smoke testing, `alembic_version` estaba en `0027_tasks_is_deleted`.
Faltaba aplicar **dos** migraciones (0028 y 0029), pese a que el usuario
había arrancado AutomatizaPyme.exe en sesiones previas — y Electron está
configurado para correr `alembic upgrade head` al arranque en
`desktop/python-manager.js:360`.

Lo que pasó: 0028 (UNIQUE(tenant_id, nif) en clients) tiene un guard
defensivo que lanza `RuntimeError` si hay duplicados pre-existentes
(documentado en su docstring). El smoke testing había creado 6 clientes
duplicados en el tenant del usuario — el guard se disparó cada vez que
Electron arrancó, alembic abortó, y 0029 nunca tuvo oportunidad de aplicarse.
**Pero el usuario no vio nada** porque los logs de migración van al output
de Python embebido, que el wrapper Electron no escala a la UI.

**Patrón antipatrón**:
1. Migraciones con guards defensivos que pueden `raise` están bien — el
   problema es que el wrapper que las ejecuta no propaga el fallo a la UI.
2. El usuario percibe que la app arranca "normal" y no se entera de que
   la BD está atascada en una revisión vieja. Bugs futuros relacionados
   con columnas faltantes se atribuyen a otra cosa.

**Regla de prevención**:
1. **El wrapper de migraciones Electron debe surfacing fallos**: cualquier
   `RuntimeError` o exit code distinto de 0 de `alembic upgrade head` debe
   bloquear el arranque del backend O mostrar una notificación visible al
   usuario ("La base de datos no se ha podido actualizar: <razón>").
2. **Endpoint admin de health**: `/api/v1/admin/db-status` que devuelva
   `current_revision` vs `head_revision` para detectar drift desde fuera.
   Equivalente al `system_status_check` que ya existe pero específico para
   alembic.
3. **Migraciones que `raise` deben dejar una marca persistente**: e.g.,
   escribir un fichero `migrations_blocked.txt` en `APPDATA/AutomatizaPyme/`
   con el último error, que el frontend pueda leer y mostrar.

**Aplicación**: revisar `desktop/python-manager.js` para asegurar que el
output de `command.upgrade()` se inspecciona y se notifica. Hasta que esté:
cualquier sesión de testing intensivo (smoke, seed) debe terminar con un
`alembic current` manual para verificar el estado de la BD antes de cerrar.

---

## 2026-05-20 — `UPDATE ... WHERE col = ANY(%s)` con UUID requiere cast explícito

**Contexto**: el script de merge de clientes duplicados (resolución previa
a 0028) usaba `UPDATE invoices SET client_id = %s WHERE client_id = ANY(%s)`
pasando una lista Python de objetos `uuid.UUID`. Postgres respondió:
*"operator does not exist: uuid = text"*. La transacción rollback y nada
quedó tocado, pero el patrón es trampa: psycopg2 serializa la lista como
`text[]` por defecto, no como `uuid[]`.

**Patrón antipatrón**:
- Asumir que psycopg2 detecta el tipo del array por el tipo de sus items.
- Mismatch UUID/TEXT se silencia hasta runtime; tests con SQLite no lo
  detectan (SQLite no distingue tipos como Postgres).

**Regla de prevención**:
1. Para `ANY(%s)` con columnas tipadas, **siempre castear** en SQL:
   `ANY(%s::uuid[])`, `ANY(%s::int[])`, etc. Es defensivo y barato.
2. Pasar los items como strings cuando se castea (`[str(u) for u in uuids]`).
   psycopg2 los promociona correctamente al tipo target del cast.
3. Mismo patrón aplica a JOINs/comparaciones con función SQL que devuelva
   text: si hay riesgo de mismatch tipo con la columna, cast explícito.

**Aplicación**: revisión rápida de scripts/migraciones que usen `ANY(%s)`
con tipos custom (UUID, ENUM, JSONB). Si no llevan cast, son bug latente
contra Postgres real.

---

## 2026-05-19 — tz-naive vs tz-aware datetime: SQLite no preserva tzinfo en TIMESTAMPTZ

**Contexto**: Bug encontrado en 6 sitios distintos en la misma sesión.
Patrón: `if obj.expires_at < datetime.now(UTC):` donde `obj` viene del ORM
y `expires_at` está declarado como `Column(DateTime(timezone=True))`. En
Postgres con asyncpg, el atributo llega tz-aware → comparación OK. En
SQLite con aiosqlite, el atributo llega tz-naive (la pérdida ocurre en el
driver) → `TypeError: can't compare offset-naive and offset-aware datetimes`.

**Sitios afectados** (descubiertos por coverage + grep estático):
- `services/workflow/recovery.py` (Task.started_at)
- `services/workflow/approval.py` (PendingApproval.expires_at)
- `api/v1/routes/users.py` x3 (UserInvitation.expires_at)
- `services/auth/service.py` (PasswordResetToken.expires_at)

**Patrón antipatrón**:
```python
if reset_token.expires_at < datetime.now(UTC):  # ← BUG si driver naive
    raise ValueError("expirado")
```

**Patrón correcto**:
```python
from app.core.datetime_utils import as_aware
if as_aware(reset_token.expires_at) < datetime.now(UTC):
    raise ValueError("expirado")
```

**Regla**:
1. Cualquier comparación Python-side de un `datetime` que venga del ORM
   contra `datetime.now(UTC)` debe pasar por `as_aware()` (helper en
   `app/core/datetime_utils.py`).
2. Comparaciones en SQLAlchemy `where()` clauses son SQL nativo, no
   Python — no necesitan coerción (la BD maneja la comparación).
3. Cuando se añada una columna `DateTime(timezone=True)` nueva, verificar
   que todos los `if x.col < now` consumidores usan `as_aware`.

**Por qué `expire_on_commit=False` no ayuda**: `expire_on_commit` controla
si los atributos se invalidan tras commit, no cómo el driver devuelve los
valores. El bug es del driver SQLite, no del session lifecycle.

## 2026-05-19 — DELETE/UPDATE en tablas WORM requiere soft-delete en la tabla origen, no en la WORM

**Contexto**: `cleanup_tasks` (`services/workflow/task.py`) intentaba
`DELETE FROM audit_log WHERE task_id IN (...)` y luego `DELETE FROM tasks`.
La migración `0012_sec_worm_audit.py` crea triggers PL/pgSQL
(`audit_log_no_update`, `audit_log_no_delete`) que rechazan ambas operaciones
con `RAISE EXCEPTION 'Append-only table: % is immutable (SEC.WORM)'`. El
endpoint colgaba 500 y la UI mostraba "Limpiar(N)" en pending eterno.

**Causa raíz**: pensar el cleanup como un DELETE físico cuando hay tablas
satélite con WORM. Tres opciones evaluadas:
1. `ON DELETE SET NULL` en la FK `audit_log.task_id` → **no sirve**: la
   acción CASCADE/SET NULL dispara igualmente los triggers `BEFORE UPDATE`.
2. Saltar `audit_log` y solo borrar tasks sin audit → recurre al mismo
   problema cuando hay FKs apuntando.
3. **Soft-delete en `tasks`** (flag `is_deleted`) → preserva todos los
   registros WORM y sus FKs, oculta la task de las consultas de listado.

**Regla**:
1. Antes de añadir un DELETE o UPDATE a una tabla, comprobar si ella o sus
   referenciantes son WORM (buscar trigger `sec_worm_reject_mutation` o tabla
   con `Append-only` en docstring). La lista actual: `audit_log`,
   `agent_execution_trace`, `verifactu_chain`, `fiscal_approval_log`.
2. Si hay relación WORM, modelar el "borrado" como `is_deleted=True` en la
   tabla NO-WORM y filtrar `is_deleted=False` en todas las lecturas
   relevantes (`list_*`, `get_*`, contextos enriquecidos).
3. Las FKs entre la tabla soft-deletable y la WORM se preservan; no hace
   falta `NULL out` los referenciantes.

**Aplicación**: revisar el resto de endpoints que hacen DELETE masivo
contra tablas con audit_log/agent_execution_trace asociado. Mismo patrón
aplicable si en el futuro hay cleanup por tenant, por execution_id, etc.

## 2026-05-18 — VALID_DOMAINS y DISPATCHER_MAP deben estar en sync

**Contexto**: Bug SC-4 — `"Dame el resumen contable del mes"` clasificaba
como `chat` aunque las keywords correctamente lo enrutaban a `report`. El
`DISPATCHER_MAP` (dispatchers/__init__.py:38) tenía registrado el dispatcher
`"report"`, pero `VALID_DOMAINS` (state.py:70-89) NO incluía `"report"`. El
`classify_node` filtra contra VALID_DOMAINS y descarta cualquier dominio no
listado → fallback a `chat`.

**Patrón**: hay 3 puntos donde un dominio nuevo debe existir:
1. `VALID_DOMAINS` en `app/agents/orchestrator/state.py`
2. `DISPATCHER_MAP` en `app/agents/orchestrator/dispatchers/__init__.py`
3. Keywords en `_KEYWORD_MAP` y/o `_STRONG_KEYWORDS` en
   `app/agents/orchestrator/classifier.py`

Si falta cualquiera de los 3, el dominio queda silenciosamente inaccesible.

**Regla**: al añadir un dominio al orchestrator, comprobar los 3 sitios.
Mantener la lista de dominios sincronizada — idealmente derivar
DISPATCHER_MAP keys de VALID_DOMAINS en lugar de duplicar la definición.

## 2026-05-19 — Falso positivo: LLM aluciona "no estoy en este contexto" y el agente marca done

**Contexto**: Iter 1 email/A, prompt `iter1_email_search` = "Busca el último email que envié a Lucía sobre el contrato". El clasificador acertó (`email`), el dispatcher invocó al agente email, pero el LLM (Claude) respondió en texto plano: *"Lo siento, pero las herramientas de correo electrónico (check_inbox, check_unread, etc.) no están disponibles en mi contexto actual de Claude Code. Estas herramientas son parte del sistema de Automati[zaPyme]..."*. El log lo detectó (`[ClaudeCode] Claude menciono tools [...] en texto pero no uso el formato correcto`) **pero igualmente devolvió `agent_results[0].success=true` y `status=done`**. La UI le diría al usuario "OK" cuando no se ejecutó ninguna búsqueda.

Los otros 2 prompts del mismo run (`iter1_email_send`, `iter1_email_summarize`) sí invocaron tools correctamente (en modo DEMO porque tenant no tiene OAuth en DB) — el problema está en el prompt 3 específicamente, no en el flujo email general.

**Patrón**: cuando el LLM se rehúsa a invocar tools y devuelve texto explicativo, el wrapper de Claude (`_dispatch_handlers` rama custom o el adaptador del agente email) trata el texto como output válido y propaga `success=true`. La detección heurística `[ClaudeCode] Claude menciono tools […]` existe en logs pero **no marca el step como fallido**.

**Regla**: cualquier respuesta del LLM que matchee el patrón "menciono tools en texto pero no uso el formato correcto" debe degradarse a `AgentResult(success=False, error="llm_refused_tool_use")`. Buscar la fuente del log `[ClaudeCode]` (probablemente en algún adaptador de Claude en `agents/email/` o en un helper común) y añadir la regla allí. Verificar también si el system prompt menciona "Claude Code" — el LLM se confunde de identidad.

**Prevención durante iteraciones futuras**: si un step termina con `error` no nulo PERO `success=true`, marcarlo como sospechoso en el reporte. Añadir al `_format_row` del smoke un flag visible para este caso.

## 2026-05-18 — AIEmployees custom interceptan el dispatch antes que el builtin

**Contexto**: tras fixear SC-1 (CRM-create), el smoke completo expuso SC-9:
`billing_simple` ahora falla con timeout 900s porque el `plan_node`
(_plan_handlers.py:438-462) detecta un AIEmployee custom de domain=billing
("yolanda sanchez" en el tenant AutomatizaPyme) y enruta el plan a
`agent="custom"` en lugar del builtin billing. Yolanda tiene system_prompt
o skills rotas → hangup.

**Patrón**: la presencia de un AIEmployee custom **siempre** desvía el
tráfico del builtin, aunque el custom esté inoperante. Eso significa que
arreglar un bug aguas arriba (clasificación) puede exponer bugs aguas
abajo en customs olvidados.

**Regla**: al probar el orchestrator end-to-end, sembrar tenants limpios
o auditar los AIEmployees custom existentes antes de interpretar timeouts.
Considerar añadir health-check al lookup de customs en
`_plan_handlers.py` que omita aquellos marcados como obsoletos o con
skills inexistentes.

## 2026-05-18 — ExecutionContext sólo propaga claves estructuradas (response text se pierde)

**Contexto**: Bug SC-10 — el plan multi-step de coordinator fallaba en el
step 2 con "no tengo acceso a los datos del paso 1". El mecanismo
`ExecutionContext` SÍ enriquece el intent del siguiente agente, pero
sólo extrae claves listadas en `_EXTRACTABLE_KEYS` del output de los
pasos previos (invoice_id, client_name, employee_id, etc.).

Como los agentes devuelven `{"action": "completed", "response":
"<markdown con los datos>"}` y los datos están EMBEBIDOS en el texto
markdown del `response`, `_extract_entities` no encuentra ninguna clave
estructurada → `key_data = {}` → el contexto enriquecido para el step
N+1 es sólo `"Paso 1 (rag): completed ✅"` sin datos.

**Patrón**: cualquier feature que dependa de pasar contexto entre steps
de un plan multi-agent requiere que el agente productor exponga claves
estructuradas en su output O que el consumidor reciba el texto del
`response` previo.

**Regla**: al añadir un nuevo agent/dispatcher cuyo output debe alimentar
a otro agent en un plan coordinator, comprobar que el output incluye
claves en `_EXTRACTABLE_KEYS` (o ampliar la lista). Como fallback, el
fix de SC-10 ya incluye `response_preview` (800 chars) en el enriched
intent cuando no hay key_data — usar como red de seguridad, no como
mecanismo principal.

## 2026-05-18 — El classifier cachea 24h por defecto

**Contexto**: tras cada cambio al `_KEYWORD_MAP` o `_STRONG_KEYWORDS` en
classifier.py, las primeras corridas seguían devolviendo el dominio viejo
porque `_CACHE_TTL_CLASSIFY = 86400` (24h) y el cache key es
`f"classify:{_normalize_for_cache(intent)}"`. Sin invalidar el cache,
imposible validar un fix de clasificación.

**Patrón**: cualquier cambio a las reglas del classifier requiere
invalidar el cache `classify:*` del tenant antes de re-testear, o
esperar 24h.

**Regla**: en sesiones de iteración sobre el classifier, mantener a mano
un script `clear_classify_cache.py` (ver `c:\tmp\` en mi sesión) que
itere los prompts conocidos e invoque `llm_cache.invalidate()`. Para
una sesión profesional, plantearse exponer un endpoint admin
`DELETE /admin/llm-cache?prefix=classify` o un flag `--no-cache` al
script smoke.

---

## 2026-05-02 — Verificar hallazgos de subagentes Explore antes de actuar

**Contexto:** Durante la auditoría Fase 1 de multi-tenancy (`docs/multitenancy/tenant_scoped_tables.md`), un subagente Explore reportó tres "hallazgos críticos". Al leer el código real, dos de los tres eran falsos positivos:

- `generative_ui.py:91` — el subagente vio `select(Client...)` en línea 91 y reportó "sin filtro tenant", pero la línea 92 contenía `.where(Client.tenant_id == tenant_id)`. El query SÍ filtraba.
- `DocumentEmbedding sin tenant_id` — el modelo en `embeddings.py:16` SÍ tiene `tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)`. El subagente reportó incorrectamente que no existía.
- `node_engine.py:334, 340` — query sin filtro de tenant pero NO vulnerable porque los IDs vienen de BD ya validada upstream (en endpoint y en `run_workflow`). Reportado como crítico pero realmente es solo "defensa en profundidad recomendable".

**Patrón:** Los subagentes Explore leen extractos limitados de archivos. Pierden contexto de:
- Métodos chained (`.where()` después del `select()` en línea siguiente)
- Validación upstream que ocurre fuera del archivo inspeccionado
- Constraints de seguridad en otra capa (endpoint, middleware, dependencia FastAPI)

**Regla:** Antes de aplicar correcciones a hallazgos reportados como "críticos" por un subagente:
1. Leer la función completa con la herramienta Read directamente.
2. Confirmar la cadena de validación upstream cuando un identificador entra como parámetro.
3. Reportar al usuario "hallazgo X confirmado" o "hallazgo X falso positivo" antes de editar código.

**Aplicación:** Esta regla se aplica especialmente cuando el subagente reporta "missing where" / "missing filter" / "missing validation" — estos patrones son los que más fácilmente generan falsos positivos por lectura parcial.

---

## 2026-05-03 — Comprobar gestores portables del proyecto antes de instalar dependencias system-wide

**Contexto:** Para validar la Fase 3 (RLS) necesitaba un Postgres corriendo. Vi `Test-NetConnection localhost -Port 5433 → False`, asumí "no hay Postgres" e instalé PostgreSQL 17 vía winget como servicio del sistema. Después descubrimos que `desktop/postgres-manager.js` ya gestiona PostgreSQL 15 portable en `%APPDATA%\AutomatizaPyme\pgsql\` — exactamente lo que tendrá el end-user.

**Consecuencias:**
- Postgres 17 system-wide redundante con la portable que produce el producto.
- Pruebas hechas contra una versión de Postgres distinta a la de producción.
- Tiempo perdido en descubrir y revertir.

**Patrón:** "puerto cerrado → no existe el servicio" es una conclusión incompleta cuando el proyecto tiene su propio gestor de runtime. Los proyectos desktop empaquetados (Electron + backend embebido) frecuentemente descargan y arrancan sus propios servicios bajo demanda — no están corriendo permanentemente.

**Regla:** Antes de `winget install`, `apt install`, `brew install`, etc. para un servicio (Postgres, Redis, Mongo, Java, Python runtime):
1. Grep el repo: `desktop/`, `scripts/`, `install/`, `bin/` por archivos como `*-manager.js`, `setup_*.sh`, `install_*.bat`, `python-manager.js`, `jre-manager.js`.
2. Si existe un gestor del proyecto, leerlo. Probablemente descarga binarios portables a `APPDATA` / `~/.local/share` / equivalente.
3. Usar ese setup en lugar de instalar system-wide. Es exactamente lo que tiene el end-user.
4. Si NO hay gestor, valida con el usuario antes de instalar system-wide.

**Aplicación:** Crítico para proyectos con app desktop empaquetada o cualquier instalación que aspire a "self-contained" / portable.

---

## 2026-05-03 — `db.delete()` en SQLAlchemy async NO es awaitable

**Contexto:** La operación DELETE de clientes fallaba silenciosamente. La causa era `await db.delete(obj)` en `services/sales/commands.py`. SQLAlchemy async hace que `session.execute()`, `session.commit()`, `session.refresh()`, `session.flush()`, `session.rollback()` sean awaitables, pero `session.delete()`, `session.add()`, `session.expunge()` son **síncronos** — añadir `await` provoca que se ignore la operación sin error visible.

**Impacto descubierto:** El bug estaba en 28 puntos del backend (17 archivos): billing, crm, hr, sales, user_service, template_service, project_service, documents, workflow, agents.

**Regla:** En SQLAlchemy async (`AsyncSession`):
- ✅ Awaitable: `execute()`, `commit()`, `rollback()`, `refresh()`, `flush()`, `merge()`, `scalar()`, `scalars()`
- ❌ NO awaitable (síncronos): `add()`, `delete()`, `expunge()`, `add_all()`

**Prevención:** Al escribir cualquier `await db.<método>()`, verificar que el método retorna una corrutina. `delete()` y `add()` modifican el estado interno de la sesión sin I/O — son síncronos por diseño.

**Aplicación:** Revisar con grep `await db\.delete\(` y `await db\.add\(` en cualquier codebase SQLAlchemy async antes de hacer merge a main.

## 2026-05-08 — Bug RESUELTO 2026-05-19: custom employee timeout no se propaga

**Síntoma original**: tasks dirigidas al CTO custom tardaban ~8 minutos en pasar
de `executing` a `failed` aunque el timeout interno en `_invoke_dynamic_employee`
era 300s.

**Causa raíz confirmada (hipótesis 1)**: tras `TimeoutError` en
`graph.ainvoke()`, la sesión BD del handler podía quedar sucia (otros nodos del
graph hicieron writes sin commit). El `await db.commit()` posterior para marcar
`employee.status = "idle"` esperaba locks indefinidamente.

**Fix aplicado 2026-05-19** en
`backend/app/agents/orchestrator/_dispatch_handlers.py`:
- Helper `_release_employee(db, employee, label)` que hace `rollback()` PRIMERO
  (limpia estado sucio), luego `commit()` envuelto en `wait_for(10s)` —
  cualquier fallo del cleanup queda log y no bloquea la propagación del error
  original.
- Aplicado en ambos `except` (`TimeoutError` y `Exception`) de
  `_invoke_dynamic_employee`.

**Hipótesis 2 (subprocess zombie)** ya estaba mitigada por el fix de
`claude_code._agenerate` (kill+wait en TimeoutError, 2026-05-09).

## 2026-05-08 — Bug pendiente: custom employee timeout no se propaga

**Síntoma**: tasks dirigidas al CTO custom (Marcos Recio, domain=custom) tardan ~8 minutos en pasar de `executing` a `failed` aunque el timeout interno configurado en `_invoke_dynamic_employee` es 300s.

**Lo que SÍ pasa**: al final el task acaba en `failed` con "Error: Claude Code CLI no respondio en el tiempo limite". El timeout sí se dispara — pero el cleanup tarda mucho.

**Hipótesis a investigar**:
1. `await db.commit()` post-TimeoutError puede bloquearse si la sesión quedó sucia.
2. El subprocess de claude_code sigue corriendo tras `subprocess.run(timeout=...)`.
3. La excepción se traga antes de propagarse al TaskRunner.

**Reproducir**: pedir al CTO un informe extenso. La task queda `executing` >> 300s.

**Vías de investigación próxima sesión**:
- Logs stdout del backend en vivo durante el timeout
- Activar LLM_TRACE_ENABLED y verificar que claude_code respeta callbacks
- Añadir logs explícitos en _invoke_dynamic_employee tras cada await

---

## 2026-05-08 — No clasificar operaciones por substring matching de la respuesta del LLM

**Contexto:** En `dispatchers/billing.py` la `action` (`draft_created`, `summary`, `completed`...) se decidía buscando keywords en el texto que devolvía el LLM (`"borrador"`, `"draft"`, `"factura creada"`). Una consulta de listado de facturas contiene la palabra **"Borrador"** en cada fila (es el estado), por lo que `is_creation=True` y la UI mostraba *"✅ Factura creada"* en respuesta a *"Lista las facturas"*. Falso positivo trivial.

En paralelo, `_summarize_handlers.py` truncaba la respuesta de cada agente a `text[:500]` antes de pasársela al LLM resumidor → tablas con 10 facturas se reducían a 3 con campos `—` vacíos. El usuario veía datos incompletos en cualquier listado largo.

**Patrón antipattern:** clasificar/inspeccionar la salida natural del LLM con `kw in text.lower()` o trocearla por longitud arbitraria. La salida del LLM es texto libre — varía entre invocaciones, depende del prompting, y contiene palabras del dominio que también aparecen en otros contextos.

**Regla de prevención:**
1. Para **clasificar la operación**: usar la intención del usuario (`intent`) o las tools efectivamente invocadas (tool_calls del agente), no buscar substrings en la respuesta. La intención es estable; la respuesta no.
2. Para **pasar contexto al siguiente eslabón** (otro LLM, persistencia, UI): no truncar a longitudes arbitrariamente cortas. Si hay riesgo de blow-up, calcular un cap basado en límites reales de tokens del modelo destino, no en números mágicos.
3. **Test de listado obligatorio** cuando se modifica un dispatcher: una consulta de listado nunca debe terminar con `action="*_created"` ni con summary que diga "creada/completada".

**Aplicación:** Este antipatrón aparece típicamente en código orquestador escrito en iteraciones tempranas — funciona en demos cortas y rompe en producción cuando los outputs del LLM crecen. Revisar TODOS los dispatchers cuando se vea un `kw in lower(text)` antes del set de `action`.

---

## 2026-05-09 — Auto-snapshot PDF en dispatchers + paths Linux por defecto en Windows

**Contexto:** Probando el catálogo de tools serializadas, descubrimos un cluster de bugs entrelazados:

1. **Cada dispatcher** (billing, crm, documents, misc) llamaba a `_save_ai_result_as_document` al terminar la sub-tarea — generando un PDF "snapshot" del texto del agente. Una nota txt simple acababa creando además un PDF "Análisis Documento" no pedido. Una petición de informe PDF generaba **4 archivos** (PDF correcto + xlsx + 2 snapshots). Cada dispatcher chequeaba `_messages_already_generated_pdf` solo sobre SUS propios messages, no cross-dispatcher → multiplicación.

2. **Path fallback Linux en Windows**: múltiples tools (`agent_tools/documents.py`, `billing/_invoice_pdf_tools.py`, `hr/_payroll_pdf.py`, `helpers._save_ai_result_as_document`) usaban `os.environ.get("UPLOAD_DIR", "/app/uploads")`. En Windows, `UPLOAD_DIR=""` (intencional, ver `_resolve_upload_dir`) caía al fallback `/app/uploads/` que el OS resuelve a `C:\app\uploads\`. Resultado: archivos perdidos en una raíz que nadie consulta. La UI de Documentos no encontraba nada.

3. **Categorías inventadas por el LLM**: `create_document` tenía la signatura `category: str = "informes"` con docstring genérica. El LLM inventaba categorías como `"general"`, `"documentos"` que NO existen en el `FOLDERS` del frontend (`facturas, bancos, nominas, fiscal, crm, excels, informes, correos, automatizaciones, rrhh, otros`). Los archivos quedaban invisibles aunque la BD los tuviera.

4. **Decomposición multi-agent**: el orchestrator descomponía una petición unitaria *"Genera informe PDF de facturación"* en sub-tareas para `billing` + `documents`. Ambos sub-agents tenían `create_pdf_text_report` en su toolkit y generaban PDFs con títulos LIGERAMENTE distintos ("Q1 2026" vs "Q1 Q2 2026") → dedup por slug fallaba.

**Patrón antipattern compuesto:**
- Asumir que generar artifacts siempre es valioso → cada operación crea un snapshot post-hoc.
- Fallbacks de path con cadenas POSIX hardcoded (`/app/uploads`) en código que corre en Windows.
- Tools sin restricción de valores válidos para parámetros enum-like (categorías).
- Toolkits demasiado generosos: cualquier agente puede generar cualquier tipo de archivo.

**Reglas de prevención:**
1. **Antes de auto-persistir un artifact** desde un dispatcher/orchestrator, preguntar: ¿el usuario lo pidió? ¿algún otro nodo ya lo generó? Si la respuesta a la primera no es clara, NO crear. Si la segunda es ambigua, hay que añadir guard cross-dispatcher (búsqueda por `task_id`, `tenant_id+category+ventana`).
2. **Path fallbacks deben ser platform-aware**. Centralizar en una helper (ej: `_resolve_upload_dir(category)`) que sepa de Windows/macOS/Linux/AppData/XDG. Prohibir hardcodear `/app/uploads` o cualquier ruta Linux en código que corre fuera de Docker.
3. **Tools cuyo argumento debe matchear UI** (categorías, estados, tipos): documentar la lista exacta en el docstring + normalizar contra un set válido en runtime (mapear inválidos a un catch-all conocido — ej: "otros"). No confiar en que el LLM eligirá lo que existe.
4. **Toolkits estrictos por dominio**: un agente NO debe tener tools para actuar fuera de su dominio. Documents NO debería poder generar informes financieros. Si esa flexibilidad se necesita, va al orchestrator/coordinador, no al agente.
5. **Cross-dispatcher dedup**: si una helper se llama desde N dispatchers para el mismo `task_id`, debe deduplicar internamente — el primer save gana, los demás se ignoran. No depende de cada dispatcher disciplinarse solo.

**Aplicación:** Cuando se vea un dispatcher que termina con un `await _save_*` sin condicionar a la intención original o a si otro nodo ya guardó, **es bug latente**. Cuando se vea `os.environ.get("DIR", "/app/...")` en código Python que corre en Windows, **es bug pendiente**. Cuando se vea `category: str = "..."` sin validación + UI con categorías hardcoded, **es bug invisible** — la BD se llena de filas que el usuario nunca verá.

---

## 2026-05-09 — Workflows: campos del prompt y handlers per-dispatcher

**Contexto:** Probando AUTOMATIZACIONES end-to-end aparecieron dos bugs entrelazados:

1. **Prompt de `parse-nl` no documentaba `conditions`** ([prompts/workflow_parse.txt]). El schema de `trigger_config` en código (`services/workflow/conditions.py`) sí soporta `conditions` con operadores (`gt`, `lt`, `eq`, AND/OR/NOT) y `evaluate_conditions()` filtra eventos. Pero el prompt al LLM solo decía `{"events": [...]} OR {"cron": "..."} OR {}`. Resultado: filtros como *"factura > 5000€"* quedaban embebidos en `action_config.instruction` como prosa, el workflow se disparaba para CADA `invoice_created` y el LLM tenía que decidir si actuar — gasto duplicado y filtro no fiable.

2. **`PendingApproval` solo se creaba en `dispatchers/billing.py`**. Cuando un workflow event-based de facturación se enrutaba al agente `custom` (Marcos CTO) o cualquier otro dispatcher, la respuesta del LLM podía decir *"Aprobación Requerida"* perfectamente pero nadie creaba la fila en `pending_approvals` ni cambiaba el estado a `awaiting_approval`. La task terminaba `done` con texto que prometía gating que el sistema NO hacía → **aprobación humana fantasma**.

**Patrón antipatrón compuesto:**
- Prompts del LLM que omiten capacidades reales del schema → el LLM no produce campos que el sistema sí sabe consumir.
- Lógica de proceso (aprobación, gating, audit) escrita inline en UN dispatcher en vez de extraída a una helper compartida que se invoque en un punto centralizado post-dispatch.
- Detección de señales semánticas (aprobación, error, creación) por substring matching en la respuesta del LLM — frágil pero contagioso: el primer dispatcher que lo hace marca el estilo del resto.

**Reglas de prevención:**
1. **Sincronizar prompts con schema**. Cada vez que se añada un campo opcional al schema de un endpoint que parsea lenguaje natural, el prompt del LLM debe documentarlo con ejemplos. Auditoría rápida: comparar campos validados por Pydantic vs campos mencionados en el prompt — todo campo persistible debe ser parseable.
2. **Lógica cross-dispatcher va a helper centralizada**. Si una operación (crear PendingApproval, snapshot, audit, broadcast) debe ocurrir SIEMPRE que se cumpla cierta condición independientemente del routing del orchestrator, **no puede vivir en un solo dispatcher**. El sitio natural es un nodo post-dispatch (`summarize_node` o un nuevo node) o un hook en el flujo de execution. Idempotente para no duplicar si un dispatcher ya hizo el trabajo.
3. **Workflows requieren tests end-to-end con BD**. Una task que termina `done` no implica que el sistema haya respetado el contrato del usuario. Para workflows de aprobación: verificar fila `pending_approvals` + status del workflow + ausencia de side-effects que la aprobación debía gatear.

**Aplicación:** Cuando se añada un campo nuevo al schema de un endpoint LLM-driven, el prompt es parte de la PR — no se mergea sin actualizar. Cuando se vea código de "post-procesamiento" inline en un solo dispatcher (creación de PendingApproval, audit, broadcast) y el sistema admite múltiples dispatchers para el mismo dominio, hay bug latente esperando: cualquier nuevo routing destino se lo salta.

---

## 2026-05-09 — Handlers que leen campos `extracted_data` que nadie rellena

**Contexto:** Probando `list_invoices` (Ana Valdés), el agent_result tenía `output.response` con la lista correcta (10 facturas, 17.399,08 €) pero `agent_result.summary` decía *"📊 Encontradas 0 facturas. Total: 0,00 €."*. Mismatch flagrante visible en logs / UI / notificaciones.

**Causa raíz:** [`_format_summary` en `agents/orchestrator/utils.py`](backend/app/agents/orchestrator/utils.py) tenía un branch `if action == "summary"` que leía `output["extracted_data"]["invoices"]` y `["total"]` para componer el texto. Pero la tool `list_invoices` devuelve un **string** plano (`"Facturas recientes (N):..."`) y el dispatcher [`dispatchers/billing.py`](backend/app/agents/orchestrator/dispatchers/billing.py) construye `output = {"action": ..., "response": final_text}` SIN `extracted_data`. El branch leía un dict vacío → `len([]) = 0` y `total = 0` siempre.

**Patrón antipatrón:** **código fósil de un contrato pasado**. La tool fue refactorizada para devolver string (probablemente para mejor consumo del LLM), pero el handler `_format_summary` se quedó esperando datos estructurados que ya nadie produce. El test "los números coinciden" se omitió porque el output cosmético no era cubierto por tests.

**Regla de prevención:**
1. **Cuando una tool cambia de devolver dict→string** (o viceversa), `grep` por `output.get("<campo_que_devolvía>"` en todo el orquestador y dispatchers. Cualquier consumidor que lea ese campo está roto silenciosamente.
2. **Handlers de formateo deben leer las claves que el dispatcher realmente produce**, no claves aspiracionales. Si solo se garantiza `action` y `response`, lee solo eso. Para evitar que el LLM y el handler diverjan, el patrón ya correcto en `compliance` / `banking` / `rag` es: `output.get("response")` + recorte a 200 chars + emoji prefix.
3. **Test mínimo de "summary refleja realidad"**: para cada tool de query (list_*, search_*, check_*), un test que simule output del agente y verifique que `summary` no contiene `0` cuando hay datos, ni texto contradictorio con `output.response`.

**Aplicación:** Cualquier `handler.get("foo", default)` cuyo `default` se devuelva en producción habitualmente (`[]`, `0`, `""`) es candidato a código fósil. Loguear o testear que el default NO se está cubriendo en flujos reales antes de creerse que el branch sirve.

---

## 2026-05-09 — Tools transversales pertenecen a `agent_tools/`, no a un agente concreto

**Contexto:** Probando *"Busca el cliente con NIF B12345678"* (Ana, billing), el coordinator lo enrutó al CRM (decisión semánticamente correcta — clientes son del dominio CRM). Pero el agente CRM **no tenía `search_client` en su toolkit**: la tool vivía solo en `agents/billing/_client_tools.py`. El LLM del CRM intentó invocarla y obtuvo `"No such tool available"` → respondió en texto *"Las herramientas del CRM no están disponibles..."* y el dispatcher CRM marcó `success=True, action=completed` porque su detección de errores era débil (`final_text.lower().startswith("error")` — la respuesta no empezaba con "error").

**Patrón antipatrón compuesto:**
- Una tool **transversal** (clientes son consumidos por billing, CRM, banking, e-commerce…) vivía como tool privada de un agente concreto. Cualquier otro agente que la necesitara tenía que (a) importarla violando "agents NEVER import other agents" o (b) reimplementarla.
- Dispatcher con detección de error débil (solo prefix matching) → cuando el LLM falla por **falta de tool** y responde en prosa, no se detecta. La task queda `done` con `success=True` y `summary="✅ completed"`.
- Toolkit del CRM sin tools de consulta de clientes pese a que el system prompt prometía "gestión de cartera de clientes".

**Reglas de prevención:**
1. **Tools por dominio funcional, no por agente**: si una tool consulta o modifica una entidad que más de un dominio usa (`Client`, `Document`, `TenantKnowledge`, `Email`), va en `app/agents/agent_tools/<entidad>.py` y la importan los toolkits que la necesiten. Solo lógica que es **inherente al agente** (e.g. `_resolve_client` que es helper privado del flujo de creación de factura) se queda en `agents/<X>/`.
2. **Cada dispatcher con detección de errores semánticos**, no solo prefix `"error"`: ya tenemos el patrón completo en `dispatchers/billing.py:89-108` (lista de frases de fallo comunes en español + check de `agent_status` del graph). Replicarlo en cualquier dispatcher nuevo. Cuando se vea `is_error = text.startswith("error")` solo, es bug latente.
3. **Cuando el coordinator re-rutea a un agente, ese agente debe tener las tools necesarias para la operación**. Pre-flight de testing: para cada prompt del catálogo, verificar que el agente al que termina llegando tiene en su toolkit las tools mencionadas en su system prompt + las que naturalmente esperaría usar.
4. **Validador opcional sugerido**: tests que comparen `tools` registradas por agente vs tools mencionadas en el system prompt. Cualquier mismatch es bug pendiente (system prompt promete algo que no existe, o tool registrada nunca documentada al LLM).

**Aplicación:** Cuando se vea una `@tool` async en `agents/<X>/`, preguntarse: *¿algún otro agente necesitará esto en los próximos 6 meses?* Si la respuesta es "probablemente sí", al `agent_tools/`. Cuando se vea `dispatchers/<X>.py` con detección de error de una sola línea, replicar el patrón compuesto de billing. Cuando un agente promete en system prompt una capacidad ("consulto clientes", "leo emails"), el toolkit debe tener al menos una tool que la realice — si no, es bait-and-switch que el LLM va a descubrir al primer intento.

---

## 2026-05-09 — Tools de query deben exponer los IDs que las tools de write exigen

**Contexto:** Probando *"Marca como pagada la factura más reciente de Construcciones Valdemar S.L."*, el LLM:
1. Llamó a `list_invoices` y encontró la factura (nº `IA-789610CF`, `document_id: 07893052-...`).
2. Llamó a `update_invoice_status(invoice_id=document_id, ...)` → *"Factura no encontrada"*.
3. Reintentó con `invoice_id="IA-789610CF"` → *"UUID malformado"*.
4. Se rindió diciendo "estoy teniendo un problema técnico".

El LLM **no tenía manera de saber** el UUID correcto del Invoice: `list_invoices` exponía solo `invoice_number` (string `IA-XXX`) y `document_id` (UUID del PDF/TenantDocument, NO del Invoice). Las tools `update_invoice_status` / `update_invoice` / `send_invoice_by_email` exigen `Invoice.id` (UUID) → cadena rota.

**Patrón antipatrón:** una **tool de query** que oculta el ID primario de la entidad rompe cualquier cadena compuesta "list → write" porque las **tools de write** suelen pedir UUID. El LLM tiene que adivinar — confunde `invoice_number`, `document_id`, `client_id` — y falla silenciosamente con errores como "no encontrado" o "UUID malformado". El usuario ve "estoy teniendo un problema técnico" sin pista de qué pasó.

**Reglas de prevención:**
1. **Toda tool de query (list_*, search_*, get_*) debe exponer en cada fila el UUID primario de la entidad** con un nombre coherente con el campo que esperan las tools de write (`invoice_id`, `client_id`, `payroll_id`, etc.). Los identificadores legibles (números de factura, NIFs, slugs) son útiles para el usuario pero **insuficientes** como contrato entre tools.
2. **Cuando una tool expone múltiples IDs para una misma fila** (e.g. `invoice_id` + `document_id`), la docstring debe explicar **exactamente qué consume cada uno**: quién quiere `invoice_id`, quién quiere `document_id`. Sin esa diferenciación, el LLM elige el primero que ve.
3. **Tools de write deberían ser robustas a inputs comunes del LLM**: si el LLM pasa un `invoice_number` en lugar de UUID, una opción defensiva es probar primero `Invoice.id == UUID(x)` y si falla con `ValueError`, hacer fallback a `Invoice.invoice_number == x`. Mejor que una `ValueError` críptica al usuario.
4. **Detección de errores en el dispatcher** debe incluir las frases que el LLM produce **cuando una tool falla repetidamente**: "problema técnico", "uuid malformado", "factura no encontrada", "no consigo". Sin esto, la task termina `success=True, action=summary` con un texto que dice abiertamente "no pude hacer X".

**Aplicación:** Cuando se añada una tool de write que requiera UUID, **revisar la tool de query correlacionada** (`list_*` para `update_*`/`delete_*`, `search_*` para `get_*`/`add_*`). Si la query no expone ese UUID, es bug pendiente. Test obligatorio: una cadena `list → update → list` debe terminar con la entidad realmente modificada en BD.

---

## 2026-05-09 — `except Exception` que traga AttributeError de columnas inexistentes

**Contexto:** Probando `send_invoice_by_email` con Gmail OAuth conectado, el correo **llegaba** al destinatario pero **sin el PDF adjunto**. La respuesta del LLM mencionaba "PDF adjunto" porque inventaba el detalle, pero el ToolMessage real decía *"con 0 adjuntos (ids_in=['07893052-...'])"* — la `attachment_ids` correcta entraba a `_load_attachments` pero salía lista vacía.

**Causa raíz:** `_load_attachments` en `agents/email/tools.py` hacía `select(TenantDocument.file_path, TenantDocument.title)`. La columna `title` **no existe** en `TenantDocument` (los campos reales son `file_name`, `file_type`, `file_path`, `file_size`, etc.). SQLAlchemy lanzaba `AttributeError: 'TenantDocument' object has no attribute 'title'` y el bloque `except Exception as _e: logger.warning(...)` se la tragaba con un mensaje genérico *"Error leyendo adjunto para email"* — sin doc_id, sin tenant, sin la excepción real visible. Cualquier llamada a la tool quedaba con `attachments=[]` invisible para el caller.

**Patrón antipatrón compuesto:**
1. **`except Exception` bloque-amplio** que captura errores de programación (AttributeError, TypeError, ImportError…) junto a errores transitorios (FileNotFoundError, IOError). Esos primeros indican bugs en código, no condiciones runtime — taparlos congela el bug en producción.
2. **Logs de error sin contexto identificador**: el log decía solo *"Error leyendo adjunto"* — no decía qué doc_id, qué tenant, qué excepción concreta. Imposible diagnosticar sin instrumentar.
3. **Refactor de modelo silencioso**: `title` probablemente existió en una versión anterior de `TenantDocument`. Cuando se renombró/eliminó, nadie regrep'eó por `TenantDocument.title` para buscar consumidores. Tests no lo cubrieron porque las pruebas de email envían sin adjuntos o usan mocks.

**Reglas de prevención:**
1. **`except Exception` solo para errores transitorios conocidos**: cuando una operación toca BD/archivo/red, atrapar tipos específicos (`OSError`, `SQLAlchemyError`, `httpx.HTTPError`). Para errores de programación, propagar — ya se descubrirán antes de producción. Si se usa `except Exception` por seguridad operacional (no romper un envío de email entero por un adjunto malo), el log MUST incluir tipo, mensaje completo, y todos los identificadores (doc_id, tenant, path…).
2. **Refactor de modelo SQLAlchemy obliga grep cross-codebase**: cuando se renombra o elimina una columna, buscar `Model.column_name` literal en TODO el código (no solo en services del propio dominio — los consumidores cross-domain como `_load_attachments` pueden estar lejos). Lint/test obligatorio: tests E2E que ejerciten el path completo (lista→write→download).
3. **Tests de adjuntos REALES en CI**: una suite de "email integration" debe enviar al menos un email con adjunto y verificar que el output del cliente (Gmail API response, MIME multipart count) lleva el adjunto. Mocks de `_load_attachments` que devuelven lista hardcoded **no habrían cazado este bug**.
4. **`logger.warning` no es suficiente para bugs silenciosos**: usar `logger.exception()` (incluye traceback) cuando el exception captura puede ser un bug de código, no operacional. Y si la operación es **silenciosa para el caller** (el caller no sabe que algo falló), elevar al menos un evento o métrica observable.

**Aplicación:** Cuando se vea cualquier `except Exception` cuyo log no incluya el tipo de la excepción ni los identificadores del input que causó el fallo, marcarlo como bug pendiente — es una bomba de tiempo que oculta refactors inacabados, schemas obsoletos, y errores de tipo. Cuando se renombre una columna SQLAlchemy o un campo Pydantic, el grep posterior es **parte del refactor**, no opcional.

---

## 2026-05-09 — `asyncio.wait_for(proc.communicate())` no mata el subprocess en timeout (Windows)

**Contexto:** Probando *"Genera un informe en PDF de facturación del último trimestre"* (Ana, billing), la task se quedaba en `executing` indefinidamente — más de 7 minutos, 0 plan steps, 0 agent_results. El timeout configurado en el provider `claude_code` era 290s. Reproduce el bug latente que ya estaba apuntado del CTO custom: `_invoke_dynamic_employee` reportaba que el TimeoutError tardaba ~8 min en propagarse cuando teóricamente debía dispararse en 300s.

**Causa raíz:** [`backend/app/core/llm/claude_code.py:_agenerate`](backend/app/core/llm/claude_code.py) hacía:

```python
proc = await _spawn_process()
stdout, stderr = await asyncio.wait_for(
    proc.communicate(input=prompt.encode("utf-8")),
    timeout=self.timeout,
)
...
except asyncio.TimeoutError:
    text = "Error: Claude Code CLI no respondio en el tiempo limite."
```

En Windows, `asyncio.wait_for` cuando levanta `TimeoutError` **intenta cancelar la task interna** (`proc.communicate`), pero esa task está bloqueada en un read syscall sobre stdout/stderr del subprocess — un syscall **no cancelable** desde Python. El subprocess de `claude` sigue corriendo y la task asíncrona queda en limbo: el `wait_for` no termina hasta que el subprocess termine por sí mismo (puede tardar minutos para PDFs largos), y mientras tanto la task del orquestador no progresa.

Para prompts cortos (lista facturas, búsqueda) el CLI responde antes del timeout y nunca se dispara el caso patológico. Para PDFs largos (4-6 páginas con tablas) el CLI tarda más, sobrepasa el timeout, y el bug aflora.

**Patrón antipatrón:**
- Confiar en `asyncio.wait_for` para liberar recursos cuando la task interna toca subprocess/sockets/file I/O nativos. La cancelación de tasks asyncio NO cancela syscalls bloqueantes — solo señala "deja de esperar" pero los descriptores siguen abiertos.
- Capturar `TimeoutError` y devolver un string de error sin matar al subprocess. El subprocess queda zombie consumiendo recursos.
- Asumir que el comportamiento Linux/Mac (donde la cancelación suele funcionar mejor) se traslada idéntico a Windows.

**Reglas de prevención:**
1. **Subprocess + asyncio.wait_for siempre con kill() en el except**: tras `TimeoutError`, llamar `proc.kill()` explícitamente para cerrar los fd. Eso libera el read syscall y la corrutina de `communicate` puede salir. Después `await asyncio.wait_for(proc.wait(), timeout=5)` para reaper sin colgar el cleanup.
2. **Capturar la referencia al `proc` fuera del try**: si el except no tiene acceso al proceso (porque está dentro del scope try), no se puede matar.
3. **Mismo patrón para cualquier I/O nativo bloqueante**: file reads grandes, socket reads, FFI calls. La cancelación de asyncio es cooperativa — solo funciona si la task chequea cancelación periódicamente. Subprocess.communicate NO chequea.
4. **Test de cuelgue**: para cada provider que use subprocess, un test que simule un proceso lento (`sleep 600`) y verifique que `_agenerate` retorna en `timeout + 10s` máximo. Sin este test, el bug ressurge en cada refactor.

**Aplicación:** Cualquier `await asyncio.wait_for(proc.communicate(...), ...)` sin un `proc.kill()` en su `except TimeoutError` es bug latente en Windows. El mismo patrón aplica a `httpx.AsyncClient.get(timeout=...)` cuando el servidor remoto deja la conexión abierta sin enviar bytes — el timeout dispara pero la conexión TCP queda abierta (httpx la cierra correctamente, pero subprocess raw no).

---

## 2026-05-09 — Tool calling vía JSON prompt-based: LLMs producen newlines literales en strings

**Contexto:** Tras arreglar el cuelgue de `claude_code` (bug subprocess timeout), la task PDF de facturación terminó OK pero el archivo creado fue **`Informe_Facturacion_Q1_2026.md`** — un markdown plano de 6,2 KB, NO un PDF. El LLM había construido un `<<<TOOL_CALL>>>` perfecto para `create_pdf_text_report`, con marcadores de inicio y fin correctos. El parser de claude_code lo extraía pero `json.loads` fallaba silenciosamente y caía al fallback "texto plano".

**Causa raíz:** El `body` del tool_call contenía **markdown multilinea con newlines reales** (no escapados como `\n` dentro del JSON). Ejemplo de lo que el LLM produjo:

```json
{"tool_calls": [{"name": "create_pdf_text_report", "arguments": {"body": "# Informe
**Período:** ...
Este informe recoge...", ...}}]}
```

Esos newlines literales dentro del valor `"body"` violan el JSON spec (RFC 7159 §7: control characters U+0000..U+001F NOT allowed inside strings; deben escaparse). `json.loads` lanza `JSONDecodeError`, el parser de claude_code lo captura, loguea "JSON malformado" y devuelve el texto crudo como AIMessage. → Billing nunca invoca la tool, el coordinator delega a `documents` agent, que crea un `.md` con `create_document`.

**Por qué se dispara con PDFs y no con tools simples:** las tools simples (`list_invoices`, `update_invoice_status`) tienen argumentos cortos (UUIDs, números, strings de una línea) — el LLM los emite sin newlines. PDFs piden bodies markdown de 4-6 páginas con párrafos, listas y tablas — ahí los newlines literales son inevitables.

**Patrón antipatrón:** confiar en `json.loads` strict para parsear JSON que viene de un LLM en formato prompt-based. Los LLMs no son procesadores JSON — emiten texto que "parece" JSON. Cualquier valor de string con saltos de línea, comillas internas mal escapadas o caracteres unicode complejos rompe el parse.

**Reglas de prevención:**
1. **Tool calling prompt-based necesita parser tolerante**: si el provider no soporta function calling nativo (Anthropic API, OpenAI, Gemini con `bind_tools`), el parser DEBE manejar los modos de fallo más comunes: newlines literales en strings, comillas no escapadas, trailing commas, comments. Estrategia: tras `JSONDecodeError`, intentar normalizar (escapar control chars) y reintentar.
2. **Function calling nativo > prompt-based**: si el deploy puede permitirlo, preferir providers con function calling nativo. El SDK serializa los argumentos correctamente y el parsing es trivial. `claude_code` CLI no lo tiene, por eso es prompt-based — pero el parser debe ser ROBUSTO al output ruidoso.
3. **Detectar fallos silenciosos del parser con métricas**: si el LLM intenta llamar una tool y el parser cae al fallback de texto plano, eso es un fallo invisible al usuario. Loguear con WARNING incluyendo head del JSON y el error, y exponerlo en métricas (e.g. counter `claude_code_tool_parse_failures`). Sin esto, el bug sólo se detecta cuando un humano nota que la tool no se ejecutó.
4. **Tests con prompts realistas**: los unit tests del parser deben usar fixtures con tool_calls que tengan bodies multilinea, comillas internas, listas markdown. Si el test solo cubre `{"name": "x", "arguments": {"a": "b"}}`, no atrapa estos bugs.

**Aplicación:** Cualquier provider que parsee tool calls del output de un LLM en prompt-based debe pasar la suite mínima: body markdown con headers, body con `"comillas"` dobles dentro, body con tabla pipe `|`. Si esos casos rompen el parse strict, el parser necesita el mismo fallback de escape control chars que aplicamos aquí.

---

## 2026-05-09 — Guard cross-dispatcher de duplicados de documento vía ContextVar `current_task`

**Contexto:** Tras arreglar el parser JSON (PDF report ya generaba el .pdf real), el coordinator descomponía la instrucción "informe PDF de facturación" en billing + documents. Billing creaba el PDF correctamente (15.1 KB). Documents agent, al recibir su sub-tarea, no tenía `create_pdf_text_report` en su toolkit (decisión de diseño correcta — documents lee/clasifica, no genera informes), así que el LLM caía a `create_document` con el cuerpo en markdown → segundo archivo `.md` (6.3 KB) con el mismo informe. **Dos archivos en BD para una misma instrucción**: confunde búsqueda RAG (`search_documents_semantic`), `list_tenant_documents`, e indexación de embeddings.

**Causa estructural:** las tools que crean documentos (`create_document`, `create_pdf_text_report`) operan independientemente sin saber en qué `task_id` están corriendo. El existente guard `_messages_already_generated_pdf` solo detecta duplicados dentro del MISMO dispatcher (mira `messages` del propio agente). El de `create_pdf_text_report` con ventana de 90s funciona para reentradas inmediatas pero no cubre el caso billing→documents secuencial separado por minutos.

**Patrón de fix:** ContextVar `current_task` paralelo al ya existente `current_tenant`. Lo setea el TaskRunner del orquestador (`tasks_orchestrator.py`) antes de invocar agentes. Cada @tool de creación de documento:
1. Lee `get_current_task()`.
2. Antes de crear, query `tenant_documents` por `(tenant_id, task_id, category)`. Si hay documento existente → no-op informativo *"Ya existe '{name}'... usa update_existing_document si quieres añadir contenido"*.
3. Asigna el `task_id` al `TenantDocument` que crea (clave para que guards futuros lo detecten).

**Reglas de prevención:**
1. **ContextVars son la herramienta correcta para "scoping implícito"**: cuando una tool necesita saber tenant/task/user/request_id pero no tiene cómo recibirlo del LLM, no inventes un wrapper que lo inyecte explícitamente. Usa `ContextVar` y setea desde el punto de entrada (worker, request handler, scheduler). asyncio garantiza que cada Task hereda copia del contexto al crearse — concurrencia segura.
2. **`task_id` debe asignarse a TODO documento creado en el contexto de una task**: si una tool persiste algo y olvida `task_id`, los guards futuros y la trazabilidad se rompen. Lint: cualquier `TenantDocument(...)` o equivalente que no incluya `task_id` debería tener un comment justificando por qué (e.g. uploads manuales del usuario).
3. **Mensajes de no-op informativos > excepciones silenciosas**: cuando el guard detecta duplicado, devuelve un mensaje al LLM explicando qué pasó y sugiriendo alternativa (`update_existing_document`). El LLM lo procesa y responde al usuario. Mejor que `return ""` o lanzar exception que el LLM interpreta como fallo.
4. **Test del cluster cross-dispatcher**: prompts del catálogo que típicamente disparan la descomposición del coordinator (los que tocan multiples dominios: "envía/genera/notifica") deben verificar que el resultado en BD es UN documento, no N.

**Aplicación:** Cualquier @tool que cree filas de un modelo "scoped por task" debe consultar `get_current_task()` antes y aplicar guard. El patrón se generaliza a otras entidades (e.g. `create_email_draft`, `create_invoice` con guard contra duplicados accidentales). El cost overhead es 1 query SELECT antes de cada INSERT — despreciable y previene cluster de bugs de duplicación.

---

## 2026-05-09 — Validación de unicidad asimétrica entre query y insert (case-sensitive vs upper)

**Contexto:** Probando *"Crea un empleado: Juan Pérez, NIF 12345678Z, salario 2500€"* tras `list_employees` (que mostró que ese NIF ya existía para María García López), el sistema **CREÓ un nuevo empleado duplicado** con el mismo NIF. La tool `create_employee` tiene una validación previa al insert pero estaba escrita asimétricamente:

```python
# Validación: lookup case-sensitive
result = await db.execute(
    select(Employee).where(
        Employee.tenant_id == UUID(tenant_id),
        Employee.nif == nif.strip(),  # ← sin upper
    )
)
# Insert: case-INsensitive (sube a UPPER)
emp = Employee(nif=nif.strip().upper(), ...)
```

Si el LLM emitía `"12345678z"` (minúscula), el query buscaba `Employee.nif == "12345678z"` y NO encontraba a María (que tiene `"12345678Z"`). El insert subía a `"12345678Z"` y creaba el duplicado. Resultado: dos empleados con mismo NIF en el mismo tenant, integridad de datos rota a nivel real (en España un NIF identifica unívocamente a una persona).

**Patrón antipatrón compuesto:**
- Validación de unicidad **solo en código** sin constraint a nivel BD. Cualquier ruta no validada (race condition, otra tool, una API directa) puede saltarse el check.
- **Asimetría entre el lookup y el insert**: el insert normaliza (UPPER) pero el lookup no. Cualquier valor que el normalizador toque pero el query no, escapa la validación.
- Tabla con un solo PK en `id` y NINGUNA constraint de negocio: cero defensa-en-profundidad.

**Reglas de prevención:**
1. **Constraint UNIQUE a nivel BD es obligatoria** para cualquier campo de negocio que represente una identidad real (NIF, CIF, email, IBAN, número de licencia). El código de aplicación es la primera línea de defensa, la BD es la barrera infalible que protege contra race conditions y rutas no auditadas. Ejemplo correcto: `CREATE UNIQUE INDEX ON employees (tenant_id, UPPER(nif)) WHERE nif IS NOT NULL` (partial + case-insensitive).
2. **Lookup y insert deben usar la misma normalización**: si el insert hace `.upper()`, el lookup hace `func.upper(column) == value.upper()`. Si el insert hace `.strip().lower()`, el lookup también. Mantener una helper `_normalize_nif(s)` y aplicarla en ambos puntos.
3. **Catch `IntegrityError` post-insert como red de seguridad**: incluso con validación previa correcta, una concurrencia o un bug futuro pueden colarlos. Capturar `IntegrityError` y devolver mensaje claro al LLM (e.g. *"Ya existe un empleado con NIF X (detectado por restricción de unicidad de BD)"*).
4. **Auditoría de tablas existentes**: tablas heredadas que originalmente solo tenían PK pueden necesitar UNIQUEs retroactivamente (employees, clients, invoices, products). Antes de añadir el constraint, ejecutar query para limpiar duplicados existentes — la migración fallaría si hay duplicados.

**Bug pendiente (no aplicado en esta iteración):** `agents/hr/tools.py` no aplica `_isolated()` al toolkit. Eso significa que el LLM de HR puede pasar un `tenant_id` arbitrario que no se sobrescribe por el ContextVar. No causó este bug específico (los duplicados estaban en el mismo tenant), pero es vector de prompt injection cross-tenant. Aplicar `_isolated()` requiere construir una lista `tools = [...]` (que HR no tiene exportada) — refactor pequeño pero fuera del scope de la sesión actual.

**Aplicación:** Cualquier modelo SQLAlchemy con un campo "identificador real" (DNI, NIF, IBAN, MAC, IMEI, ISBN, license plate) sin UNIQUE constraint **es bug latente**. Auditoría rápida: `grep "class.*Base" db/models/` y por cada modelo verificar que los campos de negocio críticos tienen `unique=True` en el `Column(...)` o un partial UNIQUE INDEX en migración. Cualquier validación de unicidad escrita solo en código sin constraint complementaria en BD es defensa-en-profundidad ausente.

---

## 2026-05-15 — Reverso de movimientos de stock al borrar/desconfirmar albaranes (deuda técnica)

**Contexto:** Step 4 del trabajo de inventario introdujo auto-descuento de stock cuando un albarán pasa a `confirmed` (genera un `StockMovement` de tipo `salida` con `reference=DELIVERY_NOTE:<id>`). El flujo opuesto **no está cubierto**:

- `DELETE /albaranes/{id}` borra el albarán (cascade elimina sus líneas) pero NO devuelve el stock previamente descontado. El movimiento queda huérfano y el inventario queda artificialmente bajo.
- `PATCH /albaranes/{id}/status` con `confirmed → draft` (regresión) tampoco crea movimiento compensatorio.

**Por qué se dejó así en este round:** la introducción del auto-descuento es de bajo riesgo (aditiva), pero el reverso obliga a decidir:
- ¿Quién está autorizado a desconfirmar un albarán? (impacta a tooltips y permisos)
- ¿Generamos un `StockMovement` de tipo `entrada` con `reference=DELIVERY_NOTE_REVERSED:<id>`, o "anulamos" el original marcándolo como `voided`?
- ¿Permitimos eliminar un albarán confirmado sin antes pasarlo a draft? (probablemente no — flujo seguro: forzar revert primero).

**Regla:** Cuando un servicio crea efectos colaterales en otra tabla (stock_movements, journal_entries, audit_log), añadir la simetría de borrado/reversa en la misma iteración o, si se posterga, dejar (a) un test que falle con `xfail` documentando el caso, (b) entrada en `lessons.md`, (c) bloqueo defensivo: por ejemplo, `delete_albaran` rechaza con 409 si el status es `confirmed`/`delivered`, forzando al cliente a regresar a `draft` primero.

**Aplicación pendiente:** O bien implementar reverso (issue futuro), o bien aplicar el bloqueo defensivo en `delete_albaran` y `update_albaran_status` (confirmed → draft) cuanto antes. Mientras tanto, el bug latente es: "tras borrar un albarán confirmado, el stock_quantity del producto queda menor que la realidad".

---

## 2026-05-15 — Doble barrel `lib/api.ts` y `lib/api/index.ts` — TS prefiere el archivo

**Contexto:** Añadí `StockValuation` y `StockValuationByCategory` en `frontend/src/lib/api/erp.ts` y los re-exporté en `frontend/src/lib/api/index.ts`. Al importar desde un componente con `import { type StockValuation } from "@/lib/api"`, `tsc` daba:

```
error TS2305: Module '"@/lib/api"' has no exported member 'StockValuation'.
```

**Causa:** Existen dos archivos compitiendo por el alias `@/lib/api`:
- `frontend/src/lib/api.ts` (archivo, shim de compatibilidad)
- `frontend/src/lib/api/index.ts` (directorio + index, barrel "moderno")

Node y TypeScript resuelven primero el **archivo `.ts`** sobre el `directorio/index.ts` cuando ambos existen. El `api.ts` shim re-exporta tipos uno a uno y NO usa `export *`, por lo que cualquier tipo nuevo en `api/erp.ts` queda invisible al consumidor hasta añadirlo también ahí.

**Regla:** Cuando añadas un tipo nuevo en `frontend/src/lib/api/<modulo>.ts`, modifica **ambos barrels**:
1. `frontend/src/lib/api/index.ts` (línea ~133 bloque `from "./erp"`)
2. `frontend/src/lib/api.ts` (línea ~10 bloque `from "./api/erp"`)

Lo mismo aplica si añades un nuevo método al objeto `api` — exporta en `index.ts` y verifica que `api.ts` también lo re-exporte (hoy solo hace `export { api } from "./api/index"`, así que los métodos del runtime sí se propagan; los **tipos** no).

**Prevención más limpia (deuda):** Reemplazar el contenido de `frontend/src/lib/api.ts` por `export * from "./api/index";` para que todo lo de `index.ts` (runtime + tipos) se propague automáticamente. Riesgo: si hay tipos con nombres colisionados o que `api.ts` no quería exponer, podrían filtrarse. Auditar antes de hacerlo.

**Aplicación:** Cualquier sesión que añada tipos al cliente API debe tocar los dos archivos hasta que se consolide el barrel.
