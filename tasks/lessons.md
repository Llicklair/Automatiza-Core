# Lecciones aprendidas

Registro de patrones detectados durante el trabajo para no repetir errores.

---

## 2026-06-23 — "Prompt caching = margen" es falso por dos vías (verificar antes de barrer)

**Contexto:** El consejo (item 7) marcó "14 SystemMessage sin cachear sangrando margen
en cada invocación" como crítico-para-viabilidad. Verificación en código: el helper
`make_cached_system_message()` ([llm_factory.py:67](../backend/app/core/llm_factory.py#L67))
**ya está adoptado en los 12 agentes principales** y añade `cache_control: ephemeral`
solo si el provider activo es anthropic. Medición de tamaños reales: el system prompt
más grande del repo es inventory ~571 tok; accounting ~460; HR ~480. Los ~18 sitios
`SystemMessage(` directos restantes (tools/services) son todos <450 tok y casi todos
de un solo turno (OCR, CV, clasificación). El mínimo cacheable de prefijo (fuente:
skill claude-api, `shared/prompt-caching.md`) depende del modelo: **`claude-sonnet-4-6`
(default del proyecto, config.py) = 2048 tok; Opus 4.6/4.7/4.8 = 4096 tok**; el 1024 clásico
solo aplica a Sonnet 4.5 y anteriores. Por debajo del umbral, `cache_control` se **ignora**
(silencioso, `cache_creation_input_tokens: 0`).

**Patrón:** Dos premisas falsas independientes hundían el item:
(a) **Elegibilidad** — ningún prompt del código llega al umbral, así que el caching
(adoptado o no) **no ahorra nada hoy**; migrar los 18 restantes es trabajo cero-valor.
(b) **Quién paga** — el modelo comercial real es **BYOK** (la landing: «trae tu clave…
pagas tu consumo directamente al proveedor»). El coste de tokens es del CLIENTE, no
COGS del vendedor → "margen-crítico" no aplica. Si acaso, el caching es un *argumento
de venta* ("baja tu factura de IA"), no margen propio.

**Regla de prevención:**
- Antes de recomendar/ejecutar un barrido de prompt-caching: (1) **medir tokens** del
  prompt real ensamblado (no el literal en `prompts.py` — muchos se concatenan en runtime,
  p.ej. HR `build_system_prompt`) y compararlo con el **umbral del modelo configurado**
  (2048 para sonnet-4-6, 4096 para Opus); (2) confirmar **quién paga** el LLM (BYOK vs SaaS)
  antes de llamarlo "margen".
- La única superficie que podría acercarse al umbral aquí es el **bloque de tools**
  (`.bind_tools(tools)`, reenviado cada turno): docstrings 230–645 tok + firmas/JSON-schema;
  el mayor (billing) ~1459 tok **sigue por debajo de 2048**, así que ni eso cachea en
  sonnet-4-6. Palanca real (si alguna): **congelar el system prompt** (sacar `today`/`tenant_id`
  del bloque cacheado, hoy invalidan el prefijo cada día), no anotar tools.
- No migrar a un helper "por consistencia" cuando el helper es un no-op en ese contexto:
  parece productivo y no mueve ninguna métrica.

---

## 2026-06-23 — El CI verde miente: probar agentes E2E con el LLM real revela otra app

**Contexto:** Auditoría iterando órdenes NL una a una contra el orquestador REAL
(provider `claude_code` = `claude` CLI, sin API key) sobre el tenant Demo Masivo. La
suite pasa en verde porque corre con `ENVIRONMENT=testing` → **MockChatModel**, que
devuelve tool-calls deterministas. Pero el escritorio envía `claude_code`, que hace
**tool-calling basado en prompt** (`<<<TOOL_CALL>>>`), no nativo. Resultado real:
banking/hr/documents/crm-lectura perfectos; pero accounting (sus tools nunca disparan,
alucina una excusa "MCP no registrado"), inventory-create y billing/crm-create devuelven
**0 tool-calls**. CI nunca toca ese camino. Informe: `tasks/e2e_agent_audit_2026-06-23.md`.

**Patrón:** Un mock que "siempre llama la tool" oculta la pregunta más importante del
sistema agéntico: *¿el LLM real decide invocar la tool?*. El verde da falsa confianza
sobre exactamente el mecanismo que falla en producción. Además, dos amplificadores
convierten el fallo en **falso éxito**: (a) `dispatchers/reports.py` fabrica un informe
financiero para CUALQUIER intent (sin guard de relevancia) y lo marca `success=True`;
(b) el clasificador hace `intent.lower()` **sin quitar tildes**, así que "perdidas"
(sin tilde) no casa la keyword "pérdidas y ganancias" y gana un genérico ("dame el
resumen"→report).

**Regla de prevención:**
- Para agentes LLM, además de la suite mock, mantener un **smoke E2E con el provider real**
  sobre un puñado de órdenes de ESCRITURA; el mock no valida la elicitación de tools.
- Clasificadores por keyword: **normalizar diacríticos** (NFKD) antes de matchear; los
  usuarios omiten tildes. Y un match de score 1 con runner-up genérico debe delegar al
  LLM, no resolver (un acierto erróneo se cachea 24 h).
- Dispatchers determinISTAS que "siempre producen algo" necesitan un **guard de
  relevancia** o devolverán artefactos plausibles-pero-falsos marcados como éxito.
- Reutilizable: runner `c:/tmp/run_order.py` (traza tools via `BaseTool.invoke`), python
  embebido del escritorio, tenant Demo Masivo. OJO: agota la cuota de la suscripción
  Claude Code (el escritorio comparte ese pozo).
- Un agente que devuelve 0 tool-calls NO siempre es bug de elicitación del LLM: **verifica
  primero que la tool EXISTE**. El "inventory no crea productos" no era fallo del modelo —
  el agente no tiene `create_product` (solo `batch_adjust_stock`/`batch_update_products`).
  Lee `tools.py`/`prompts.py` del agente antes de culpar al provider. (La causa-G real —
  el modelo lee y narra el create sin emitirlo — sí se arregló con retry write-aware.)

---

## 2026-06-23 — La capa RLS ya estaba sellada; el riesgo real era otro

**Contexto:** Los items 1/3/6 del consejo se vendían como "hardening de aislamiento
multi-tenant P0". Al mapear la superficie: (a) el scheduler ya usa `rls_bypass()` en
los scans cross-tenant y `set_current_tenant()` en el trabajo per-tenant, y sus 9
sesiones/tick son SECUENCIALES (APScheduler serial) — la "presión de conexiones" que
justificaba el refactor SAVEPOINT no existe; (b) `tool_session()` solo se usa en
inventory (8 call-sites, todos con tenant explícito); (c) el verdadero gap era que
`accounting/agent.py` NO aplicaba `_isolated()`/enforce_tenant — confiaba en el
`tenant_id` del LLM (protegido solo por la RLS ambiente).

**Patrón:** Una migración "mecánica" en código de seguridad puede INTRODUCIR el fallo
que pretende evitar. Migrar raw `AsyncSessionLocal` → `tool_session(arg_del_LLM)` en un
agente NO aislado fijaría el ContextVar al tenant que diga el LLM → fuga cross-tenant.
La sesión debe escoparse por el tenant AMBIENTE de confianza, no por el arg.

**Regla de prevención:**
- Antes de un refactor que añade complejidad "por rendimiento", VERIFICAR la premisa
  (¿concurrente o secuencial?) leyendo/perfilando — no asumirla.
- Al revisar aislamiento multi-tenant de agentes, comprobar que CADA agente que arma su
  propia lista de tools aplica `_isolated()`; el que la olvida confía en el LLM.
- `tool_session()` exige `tenant_id` explícito (raise en None); para acceso deliberado
  sin tenant, `AsyncSessionLocal()` dentro de `rls_bypass()`.

---

## 2026-06-22 — requirements.txt no era la fuente de verdad: el backend usa Poetry

**Contexto:** El "consejo de los 7 sabios" priorizó (item #10) "pinear requirements.txt"
porque tenía 33 deps con `>=` y cero `==`. Al contrastarlo, requirements.txt resultó un
**artefacto huérfano/desactualizado**: la fuente de verdad real es Poetry
(`backend/pyproject.toml` + `poetry.lock`, 205 paquetes con hashes). requirements.txt
divergía del árbol testeado (faltaban langchain-anthropic, celery, redis; sobraba
opendataloader-pdf, que ni estaba en el lock). El CI ya era reproducible (poetry.lock);
el agujero estaba en el **instalador de escritorio** (`desktop/python-manager.js:169`),
que hace `pip install -r requirements.txt` desde PyPI **en cada máquina al arrancar** →
100 escritorios resolvían árboles distintos. Además el CI estaba roto: instalaba
`poetry==1.8.2`, incapaz de leer el `poetry.lock` lock-version 2.1 (Poetry 2.x).

**Patrón:** Mismo punto ciego que "leer `tool_session` sin mirar `rls.py`": razonar sobre
un archivo (requirements.txt) **en aislamiento** lleva a conclusiones falsas cuando otra
capa (Poetry) es la que manda. Un archivo de deps con `>=` no implica "sin lock".

**Regla de prevención:**
- Antes de razonar sobre gestión de dependencias, buscar pyproject.toml / poetry.lock /
  Pipfile.lock / uv.lock. No asumir que requirements.txt es autoritativo.
- requirements.txt es ahora un **artefacto GENERADO**: `poetry -C backend export --only
  main --without-hashes -o requirements.txt`. Nunca editarlo a mano; un drift-guard en CI
  lo verifica.
- Mantener requirements.txt **ASCII-only**: en Windows pip lo lee con el locale del
  sistema (cp1252), y un acento (p.ej. `Á`=`0xC3 0x81`) **rompe la instalación cliente**.
- Alinear el pin de Poetry en CI con el lock-version del poetry.lock (lock 2.1 ⇒ Poetry
  2.x). Deps pesadas/opcionales del escritorio (torch vía sentence-transformers,
  celery/redis) van en grupos no-main (`localml`, `cloud`) para excluirlas del export.

---

## 2026-06-21 — Inventariar IA por sus @tool, no por nombres de carpeta

**Contexto:** En un análisis competitivo (Holded vs. AutomatizaPyme) subestimé la capa
de IA: listé los 14 agentes por nombre de dominio pero NO lo que sus herramientas
ejecutan. El usuario corrigió: los agentes hacen mucho más (triaje/envío de correo,
campañas y publicación en redes, redacción de informes a PDF, generación/importación
de Excel, OCR de facturas, ajustes masivos de stock). La diferenciación real vivía en
los `@tool`, no en la estructura de directorios.

**Patrón:** "qué agentes existen" ≠ "qué puede hacer la IA". El valor está en las
funciones `@tool` de cada `agents/<dominio>/tools.py` y en el catálogo de skills
(`agent_tools/ai_team.py::AVAILABLE_SKILLS`), no en los nombres de carpeta.

**Regla de prevención:** Al evaluar/comparar capacidades de IA, inventariar las
herramientas `@tool` (acción + docstring) y el catálogo de skills, no solo los agentes.
Y distinguir siempre lo ejecutable-real de lo DEMO/stub (p.ej. banca PSD2 = datos demo,
scoring de CVs deshabilitado en MVP) para no sobre-prometer en demos comerciales.

---

## 2026-06-21 — "Pestaña rota" = tabla nunca poblada (helper sin call-sites)

**Contexto:** Analítica → IA mostraba "Sin ejecuciones de agentes en este periodo".
La UI y la query (`services/analytics/dashboard.py`, tabla `agent_execution_trace`)
eran correctas: la tabla estaba **vacía en toda la BD** pese a 4.484 tasks ejecutadas.
Causa raíz: el helper `record_agent_execution()` existía y estaba exportado, pero
**ningún sitio lo llamaba** — `grep` de call-sites solo devolvía la def y el re-export.

**Patrón:** Cuando un panel "no funciona" pero dice "sin datos", verificar PRIMERO si
la fuente de datos tiene filas (`SELECT count(*)`) antes de tocar UI/query. Un helper
de persistencia sin call-sites reales es un bug silencioso clásico.

**Regla de prevención:** Ante un empty-state, ordenar el diagnóstico de datos→arriba:
(1) ¿la tabla tiene filas? (2) ¿se escriben en algún call-site? (3) ¿el filtro
tenant/fecha es correcto? Solo entonces sospechar de la UI. Y al instrumentar el
único chokepoint (aquí `invoke_dispatcher`), hacerlo **no-fatal** (try/except +
logger.warning): la observabilidad nunca debe romper el hot-path del agente.

**Status mapping:** el dispatcher emite `success/failed/timeout` pero la analítica
filtra por `ok/error` — mapear explícitamente o las trazas no cuentan.

---

## 2026-06-19 — No ordenar por UUID aleatorio para aserciones de orden

**Contexto:** `test_e2e_verifactu::test_cadena_enlaza_dos_facturas` fallaba ~50% en CI
(flaky) y bloqueaba 3 PRs de Dependabot. El helper `_records` ordenaba por
`VerifactuRecord.id`, un UUID aleatorio (`default=uuid.uuid4`), así que los eslabones
volvían en orden arbitrario y el assert `recs[-1].huella_anterior == recs[-2].huella`
salía bien o mal según el sorteo. Diagnóstico clave: un bump de TypeScript (devDep del
frontend) "rompía" un test Python → imposible → no era el bump, era flakiness.

**Patrón antipatrón:** `ORDER BY id` con PK UUID cuando el test asume orden de creación.
El UUID no es monótono → orden no determinista → test flaky e intermitente.

**Regla de prevención:** para aserciones que dependen del orden de inserción, ordenar por
una columna monótona (`created_at`, o un `serial`/secuencia), nunca por una PK UUID. Ante
sospecha de flakiness, reprodúcela en bucle (correr el test N veces) ANTES de dar el fix
por bueno, y vuelve a correrlo en bucle para confirmarlo.

---

## 2026-06-19 — Tests sobre BD: assert por SQLSTATE, no por el texto del mensaje

**Contexto:** en `test_rls_postgres.py` el assert de la violación de RLS comprobaba
`"row-level security" in str(exc)`. Falló porque el Postgres local emite los mensajes en
**español** ("viola la política de seguridad de registros"). La RLS funcionaba; el test
estaba mal escrito.

**Patrón antipatrón:** afirmar el resultado de un error de BD por el texto del mensaje. Los
mensajes de Postgres se localizan según `lc_messages` del servidor → el test es frágil y
no portable (pasa en un equipo, falla en otro).

**Regla de prevención:** verificar errores de Postgres por **SQLSTATE** (p. ej. `42501` =
insufficient_privilege para una violación de `WITH CHECK` de RLS) recorriendo la cadena
`.orig`/`__cause__` (SQLAlchemy envuelve el error de asyncpg). Nunca por `str(exc)`. Idem
para tipos de error portables. Ver helper `_pg_sqlstate` en ese test.

---

## 2026-06-19 — No afirmar hechos externos ni estado del código sin verificar primero

**Contexto:** en la sesión de AEAT/VeriFactu cometí dos errores que el usuario detectó:
1. Di el enlace `sede.fnmt.gob.es` (sin `www.`, muerto) de memoria; la URL real es
   `https://www.sede.fnmt.gob.es`.
2. Afirmé que el test `test_verifactu_registro_xml` estaba en *skip* (por el texto del
   docstring) cuando los XSD ya estaban versionados y el test **pasaba**.

**Patrón antipatrón:** asumir como verdad (a) URLs/plazos/normativa de fuentes externas y
(b) el estado actual del código por su documentación/informes, sin comprobarlo. Con un
usuario que valida y tiene aversión al detalle fiscal, esto erosiona la confianza.

**Regla de prevención:**
1. URLs/plazos/normativa externos → verificar con WebSearch antes de afirmar; si no se puede,
   marcarlo explícitamente como "por confirmar".
2. Estado del código ("ya está hecho", "está en skip", "ya existe") → comprobar con
   grep/ls/git/ejecutar el test, NO inferir del docstring ni de un informe. Los informes
   (cleanup, auditorías) caducan — re-verificar contra el código actual antes de actuar.

---

## 2026-06-11 — Subagentes de migración i18n reportan "Done" con trabajo a medias

**Contexto:** un subagente encargado de migrar `configuracion` reportó "Done" pero:
- Renombró `title`→`titleKey` en un array de datos pero dejó el JSX leyendo
  `s.title` (→ `undefined` en runtime, error TS bajo `as const`).
- Llamó `getTranslations("configuracion")` contra un namespace que **no existía
  en NINGÚN** fichero de mensajes → la página renderizaba en blanco.
- Dejó cabecera/subtítulo/"Abrir" hardcodeados sin migrar.

**Regla de prevención:** tras CUALQUIER subagente de migración i18n, el agente
principal DEBE validar 4 cosas antes de dar por buena la tarea:
1. `node scripts/check_i18n_parity.mjs` (exit 0, el número de claves sube).
2. `npx tsc --noEmit` filtrado a los ficheros tocados (sin errores).
3. grep de la página por las cadenas hardcodeadas viejas — deben haber desaparecido.
4. El namespace nuevo existe en `es.json` Y `en.json` con la misma forma.
Nunca dar por buena una migración i18n por el "Done" del subagente sin estos 4 checks.

**Convención:** solo `es.json`/`en.json` llevan claves reales; `ca/eu/gl` son stubs
regenerables (`build_locale_stubs.mjs`) y están exentos del guardia de paridad.

---

## 2026-06-10 — Un custom 'Perfil' (sin capacidades) NO debe interceptar el routing del Coordinador

**Contexto**: la iteración LLM falló en e2e4 (cierre trimestral) por timeout de 180s
del custom `Alicja Wiszczulis` — un AIEmployee con **0/4 capacidades** del contrato
(scope/memoria/conocimiento/workflows) mapeado a `domain=compliance`.
`_resolve_custom_employee` enrutaba a CUALQUIER custom cuyo nombre/rol apareciera en el
texto, **sin mirar el contrato**. Una mención incidental ("auditoría", "cierre")
secuestraba el dominio builtin y disparaba un dispatch custom lento que timeouteaba sin
aportar valor. Mismo anti-patrón que yolanda (SC-8/9).

**Patrón antipatrón**: tratar todo AIEmployee custom como agente autónomo. Un custom que
solo aporta tono/expertise (Perfil) no tiene capacidades para ejecutar nada útil; si
intercepta el routing, solo añade latencia/fallo.

**Regla de prevención (fix)**: `_resolve_custom_employee` aplica ahora
`_meets_employee_contract` — solo enruta a customs con **>=2 de las 4 capacidades**. Los
Perfil mencionados de pasada caen al dominio builtin. La selección explícita por UI
(`addressed_employee_id`) se respeta siempre (la elige el usuario). Cubierto por
`test_classifier_custom_contract.py`.

---

## 2026-06-10 — Toda `@tool` de un dominio debe aceptar `tenant_id` (el LLM lo pasa a todas)

**Contexto**: la iteración LLM (`smoke_orchestrator`) detectó `iter10_marketing`
FAIL: `search_image() got an unexpected keyword argument 'tenant_id'`. El agente
de marketing tiene 4 tools; 3 llevan `tenant_id` como primer parámetro
(`get_product_catalog`, `list_social_accounts`, `create_post`) y `search_image`
no. El LLM, siguiendo la convención del prompt ("pasa `tenant_id` a las tools"),
llamó `search_image(query=..., tenant_id=...)` → TypeError → step failed.

**Patrón antipatrón**: cuando la mayoría de tools de un dominio aceptan
`tenant_id`, el LLM asume que TODAS lo aceptan y lo pasa siempre. Una tool con
firma inconsistente (sin `tenant_id`) revienta con TypeError en cuanto el LLM la
invoca — y **no se ve en tests unitarios** (que la llaman con los args correctos),
solo en ejecución real contra el LLM. Por eso la iteración LLM lo cazó y los tests no.

**Regla de prevención**: toda `@tool` expuesta al LLM dentro de un dominio debe
aceptar `tenant_id` (aunque lo ignore) si sus tools hermanas lo llevan. Mantener
la firma consistente entre tools del mismo agente. Fix: `search_image` ahora
acepta `tenant_id: str = ""` (ignorado; Unsplash es global).

---

## 2026-05-20 — Electron arranca `alembic upgrade head` en silencio: fallos quedan invisibles

> ✅ **RESUELTA 2026-06-22.** Las 3 reglas de prevención están implementadas:
> 1. **Surfacing del fallo** — `runMigrations` (`desktop/python-manager.js`) devuelve
>    `{ok, error}` capturando stderr; `desktop/service-manager.js` aborta el arranque
>    con `throw` si falla (→ `main.js` muestra `dialog.showErrorBox`). Commit `d2335b9`.
> 2. **Endpoint admin** — `GET /api/v1/admin/db-status` (current vs head revision +
>    `up_to_date`). Commit `5ec037a`.
> 3. **Marca persistente** — `service-manager.js` escribe `migrations_blocked.txt` en
>    APPDATA con el error en cada fallo y la borra al volver a migrar OK. Commit `d2335b9`.

**Contexto**: Aplicando la migración 0029 (AIEmployee contract) tras una sesión
de smoke testing, `alembic_version` estaba en `0027_tasks_is_deleted`.
Faltaba aplicar **dos** migraciones (0028 y 0029), pese a que el usuario
había arrancado AutomatizaCore.exe en sesiones previas — y Electron está
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
   escribir un fichero `migrations_blocked.txt` en `APPDATA/AutomatizaCore/`
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
("yolanda sanchez" en el tenant AutomatizaCore) y enruta el plan a
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

**Contexto:** Para validar la Fase 3 (RLS) necesitaba un Postgres corriendo. Vi `Test-NetConnection localhost -Port 5433 → False`, asumí "no hay Postgres" e instalé PostgreSQL 17 vía winget como servicio del sistema. Después descubrimos que `desktop/postgres-manager.js` ya gestiona PostgreSQL 15 portable en `%APPDATA%\AutomatizaCore\pgsql\` — exactamente lo que tendrá el end-user.

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

> ⚠️ **CORRECCIÓN 2026-06-14 — OBSOLETA PARA SQLAlchemy 2.0.** El runtime actual es
> **SQLAlchemy 2.0.49**, donde `AsyncSession.delete()` **SÍ es coroutine** (pasó a ser
> awaitable en 2.0 porque puede necesitar cargar relaciones/cascada). Verificado:
> `inspect.iscoroutinefunction(AsyncSession.delete) == True`. Por tanto los ~38
> `await db.delete(obj)` del backend **son CORRECTOS** — NO los toques.
> **`add()`/`add_all()`/`expunge()` siguen síncronos** (no llevan `await`).
> Regla vigente: `await db.delete(obj)` ✅ ; `db.add(obj)` (sin await) ✅.
> El texto histórico abajo aplicaba a SQLAlchemy 1.4 async; se conserva como registro.

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

---

## Commit con la herramienta Bash: NO usar here-string de PowerShell (`@'...'@`)

**Síntoma:** un `git commit` vía la herramienta **Bash** quedó con subject `@ feat(...)` y un `@` suelto al final del body. Hubo que `--amend` + `--force-with-lease`.

**Causa:** usé la sintaxis de here-string de **PowerShell** (`git commit -m @'...'@`) dentro de la **herramienta Bash**. En bash eso NO es un here-string: `@'texto'@` se interpreta como `@` literal + cadena entre comillas simples + `@` literal, todo concatenado → el mensaje empieza y acaba con `@`.

**Regla:**
- **Bash tool** → mensajes multilínea con heredoc bash: `git commit -F - <<'EOF' … EOF` (o `-m $'línea1\nlínea2'`). Nunca `@'...'@`.
- **PowerShell tool** → ahí sí `@'...'@` (con el `'@` de cierre en columna 0).
- Tras commitear, **verifica** `git log -1 --format=%s` antes de dar por hecho el push.

---

## `require` destructurado en un `try`/función ≠ disponible en otra función (Electron)

**Síntoma:** la app empaquetada reventaba al arrancar con `ReferenceError: app is not defined` (solo en build instalada, no siempre en dev).

**Causa:** en `desktop/python-manager.js`, `const { app } = require("electron")` estaba dentro del `try` que calcula `PROJECT_ROOT` (block-scoped). Luego `startBackend()` usaba `app && app.isPackaged` — pero ahí `app` **no estaba declarado** en scope. `x && x.prop` **NO** protege contra un identificador no declarado: lanza `ReferenceError` igual (solo protege contra valor `undefined`/`null` de una variable que SÍ existe).

**Regla:**
- Si vas a usar un símbolo de `require("electron")` (`app`, `safeStorage`…) en **más de una función**, decláralo a **nivel de módulo**, o calcula un **flag de módulo** (`let IS_PACKAGED = false;` asignado en el try) y úsalo.
- El guard correcto contra "no declarado" es `typeof app !== "undefined"`, no `app &&`.

**Aplicación:** la capa Electron (`main.js`, `service-manager.js`, `python-manager.js`, etc.) **no** se actualiza con `npm run sync` — solo con `npm run dist`. Por eso un bug aquí solo aparece tras rebuild+install: revísala con `node --check *.js` y verifica el scope de cada símbolo de `require` antes de empaquetar.

## Los tools `gitnexus_*` no funcionan: el server MCP nunca estuvo dado de alta

**Síntoma:** tras reanalizar con la CLI (`npx gitnexus analyze`) e incluso reiniciar Claude Code, los tools `gitnexus_impact` / `detect_changes` / `query` seguían sin aparecer. `ToolSearch "gitnexus"` → 0 resultados.

**Causa:** se usó GitNexus siempre por **CLI**. En la config solo había permisos `Bash(npx gitnexus:*)` y las skills `gitnexus-*`, pero **ningún servidor MCP registrado** (`claude mcp list` solo mostraba `unrealiq_ai_ue5` y `context-mode`). Reiniciar no podía arreglarlo: no hay nada que cargar. El índice en disco (`.gitnexus/kuzu`) estaba fresco — el problema era solo el alta del server.

**Regla:**
- GitNexus expone el MCP con `npx gitnexus mcp` (stdio, sirve todos los repos indexados). Alta: `claude mcp add gitnexus -s local -- cmd /c npx gitnexus mcp` (o `npx gitnexus setup`).
- En **Windows usa `cmd /c npx ...`**: claude spawnea sin shell y no resuelve `npx.cmd` directamente.
- **No registres el alta desde Git Bash**: MSYS convierte `/c` → `C:/` y queda `cmd C:/ npx ...` (Failed to connect). Hazlo desde **PowerShell** (o `MSYS_NO_PATHCONV=1`).
- Verifica con `claude mcp list` → debe decir `✓ Connected`.

**Aplicación:** registrar un MCP **no inyecta los tools en la sesión en curso** — Claude Code los carga solo al arrancar. Tras el alta + `✓ Connected`, hay que **reiniciar una vez más** para que los `gitnexus_*` estén disponibles.

---

## 2026-06-14 — `gitnexus impact` infra-reporta el blast-radius en la capa de agentes

**Contexto:** trazando el estado del proyecto con GitNexus (vía CLI), `gitnexus impact`
devolvió `risk=LOW / 0 callers` para símbolos centrales que **sí tienen llamadores
reales**: `dispatch_node`, `classify_node`, `run_workflow`, `create_invoice`,
`_dispatch_billing`, `resume_execution`. Verificado por `cypher` directo que las
aristas existen (p. ej. `create_invoice` lo invocan la ruta `api/v1/routes/invoices.py`,
`_invoice_write_tools.py` y los tests). Además `impact --include-tests` provocó un
**segfault de npx**.

**Causa raíz (3 modos de fallo distintos):**
1. **Wiring dinámico**: los nodos LangGraph (`dispatch_node`, `classify_node`,
   `build_orchestrator`) se registran por string en el grafo compilado y se invocan vía
   `graph.ainvoke()`; el dispatch a dominios es por `DISPATCHER_MAP[domain]`; los jobs del
   scheduler se registran en runtime con APScheduler. Nada de eso genera aristas `CALLS`
   estáticas → `impact` reporta LOW, que es técnicamente correcto pero **engañoso**.
2. **Colisión de nombres**: hay símbolos con el mismo nombre en varios ficheros
   (`create_invoice` tiene **3 definiciones**: servicio `services/billing/commands.py`,
   ruta `api/v1/routes/invoices.py`, tool `agents/billing/_invoice_write_tools.py`).
   `impact <name>` resuelve UNA y subcuenta los llamadores de las otras.
3. **Inestabilidad de la CLI**: `impact --include-tests` segfaultea.

**Regla de prevención:**
1. Para símbolos de la **capa IA/orquestación** (`agents/orchestrator/`, nodos de grafo,
   dispatchers, tools `@tool`, jobs del scheduler) **NO te fíes de `impact`**. Usa `cypher`
   dirigido: `MATCH (a:Function)-[r]->(b:Function {name:'X'}) WHERE NOT a.name STARTS WITH
   'test_' RETURN a.name, a.filePath` — eso sí surfacea los llamadores reales. Complementa
   con `gitnexus context`.
2. Antes de usar `impact <name>`, comprueba colisiones:
   `MATCH (f:Function {name:'X'}) RETURN f.filePath` — si hay >1, `impact` por nombre es
   ambiguo; ánclate por `filePath`.
3. `impact` SÍ es fiable para **rutas/servicios planos sin colisión** llamados
   estáticamente (Python normal). El blast-radius bajo en la capa de agentes es un
   artefacto del análisis estático, no una garantía de seguridad.

**Aplicación:** la regla de CLAUDE.md "MUST run impact analysis before editing any symbol"
da **falsa confianza** en el núcleo agéntico. Al editar `dispatch_node`, el classifier, un
dispatcher o una `@tool`, traza los consumidores con `cypher`/`context`, no con `impact`.
Nota relacionada: el grafo no materializa un Process estático para la cadena NL→factura
(es dinámica vía LangGraph), así que tampoco esperes un flow auditable ahí.

---

## 2026-06-14 — La RLS era INERTE: el runtime conectaba como superusuario (bypassa toda policy)

**Contexto:** auditando el flujo de información se detectó que la "única defensa fuerte"
de aislamiento multi-tenant (RLS de Postgres, migración 0016) **no protegía nada**.
Verificación empírica contra la BD viva: el rol con el que conecta la app, `pyme_user`,
es `rolsuper=true rolbypassrls=true`. **Un superusuario (o rol `BYPASSRLS`) bypassa TODAS
las policies aunque la tabla esté `FORCE ROW LEVEL SECURITY`.** Prueba: con un tenant
inexistente en `app.current_tenant`, `pyme_user` veía las 31 facturas; un rol no-super
veía 0. Es decir, el aislamiento dependía al 100% de los `WHERE tenant_id` manuales
(~600 sitios); la RLS era decorativa.

Dos gaps encadenados:
1. **Rol superusuario**: `desktop/postgres-manager.js` hace `initdb --username=pyme_user`
   (bootstrap superuser) y tanto la app como las migraciones conectaban con él.
2. **El "listener SQLAlchemy" no existía**: los docstrings de `core/tenant_context.py`,
   `db/rls.py` y `agents/shared/db.py` afirmaban que un listener ejecutaba
   `SET LOCAL app.current_tenant` en cada transacción. En realidad **solo `get_db()`**
   (ruta HTTP) llamaba a `apply_tenant_rls`; las ~166 sesiones que abren
   `AsyncSessionLocal()` directo (tools, workers, services) nunca lo aplicaban → GUC sin
   setear → la policy permisiva (`OR current_setting IS NULL`) devolvía todos los tenants.

**Patrón antipatrón:**
- Asumir que `ENABLE/FORCE ROW LEVEL SECURITY` protege sin comprobar **con qué rol conecta
  el runtime**. `FORCE` solo somete al *owner* de la tabla; superusuarios y `BYPASSRLS`
  siguen saltándosela. Una capa RLS con la app conectando como superusuario es teatro.
- Docstrings que describen un mecanismo de seguridad (un "listener") que nadie implementó →
  dan falsa confianza. Verifica que el hook EXISTE (`grep`), no que esté documentado.
- Aplicar `SET LOCAL` una sola vez al abrir la sesión: el tenant se conoce TARDE (en HTTP
  tras la SELECT del usuario) o cambia MID-transacción (el scheduler itera tenants) → un
  `after_begin` único deja el GUC obsoleto. Hay que re-assertar **por statement**.

**Regla de prevención (fix aplicado):**
1. El runtime conecta con un rol **`NOSUPERUSER NOBYPASSRLS`** (`pyme_app`); `pyme_user`
   (superusuario) queda SOLO para migraciones/DDL. Split: `settings.DATABASE_URL` (runtime)
   vs `settings.ADMIN_DATABASE_URL` (migraciones). `env.py` prefiere ADMIN.
2. Listener real en `db/rls.py:install_rls_listener` registrado en ambos engines
   (`before_cursor_execute` + caché por-tx limpiada en `begin`), que re-asserta el GUC en
   cada statement con UUID validado inline. Cubre las 166 sesiones sin tocarlas.
3. `WITH CHECK` **simétrico** al `USING` (permisivo cuando no hay tenant): protege
   escrituras cuando el contexto está fijado (bloquea cross-tenant) sin romper los flujos
   sin contexto (login, portal, webhooks, lecturas globales del scheduler). Fail-closed
   total queda como fase posterior (requiere bypass explícito para esas lecturas globales).
4. **`_desktop_migrate.py` en BD nueva hace `create_all` + `stamp head` y SE SALTA los
   `upgrade()`** → ni RLS (0016) ni el rol se crearían en instalaciones nuevas. Por eso la
   creación de objetos de seguridad vive en `app/db/security_bootstrap.py` (fuente única) y
   se invoca SIEMPRE post-migración (idempotente), además de en la migración 0060 para
   despliegues incrementales.

**Verificación:** rol no-super → bogus tenant lee 0 / real 31 / sin-tenant 31 (fail-open);
write cross-tenant **bloqueado** por la policy; 84 tablas con policy simétrica; 342 tests
OK (los 3 fallos `*_requiere_auth` son pre-existentes, 403 de HTTPBearer). Probado contra
el Postgres portable real, no solo en SQLite (donde la RLS es no-op).

**Aplicación:** ante cualquier afirmación de "tenemos RLS/seguridad a nivel de fila",
comprobar SIEMPRE `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname=<rol del
runtime>`. Si es superusuario, la RLS no existe en la práctica. Y cualquier objeto de
seguridad creado por migración `upgrade()` necesita un camino equivalente para las BD
nuevas que arrancan por `create_all`+`stamp`.

---

## 2026-06-14 — Limpieza cross-cutting de filas hijas: FK ON DELETE CASCADE, no parchear N call-sites

**Contexto:** `document_embeddings.document_id` era un `String` SIN foreign key. Al borrar
un `TenantDocument` los embeddings quedaban huérfanos y el RAG (`cosine_topk`, que filtra
solo por `tenant_id`, sin join a `tenant_documents`) seguía sirviendo chunks de documentos
borrados. Y había **varias** vías de borrado (`documents/service.delete_document`,
`snapshot`, `_contracts`, rutas) — ninguna limpiaba embeddings.

**Patrón antipatrón:** resolver una limpieza que debe ocurrir SIEMPRE que se borra una
entidad padre parcheando cada call-site de borrado. Es frágil: cualquier vía nueva (o
existente que se olvidó) reintroduce el huérfano. La integridad referencial es trabajo de
la BD, no de la disciplina de cada caller.

**Regla de prevención:**
1. Si las filas hijas deben morir con el padre, modelarlo con **`ForeignKey(..., ondelete=
   "CASCADE")`** + migración que (a) limpie huérfanos previos, (b) convierta el tipo si la
   columna no casaba (aquí `String`→`uuid` con `USING document_id::uuid`), (c) añada el FK.
   Una sola barrera en la BD cubre todas las vías de borrado, presentes y futuras.
2. **`UUID(as_uuid=True)` exige objetos `uuid.UUID`, NO strings**: el bind processor hace
   `value.hex` y un str peta con `'str' object has no attribute 'hex'`. Al pasar de una
   columna `String` a `UUID`, coercer en TODO sitio de escritura (`UUID(str(x))`) y revisar
   los tests que insertaban con `document_id="marcador"` o `str(uuid4())` — deben pasar
   `uuid4()`/`UUID(...)`. (Producción solo tenía un punto de creación; el resto eran tests.)
3. Con CASCADE en la BD, el retrieval no necesita defenderse del huérfano (no puede
   existir) — menos código y sin coste por query.

**Aplicación:** verificado contra Postgres real con el rol de runtime `pyme_app` y RLS
activa: borrar el `TenantDocument` elimina sus embeddings por cascade (la policy RLS y los
grants de `pyme_app` permiten el cascade dentro del tenant). Misma idea aplicable a otras
columnas `*_id` tipo String sin FK que apunten a entidades borrables.

---

## 2026-06-20 — Test de routing contra el LLM flaky enmascaraba un bug determinista

**Contexto:** evaluando salidas del clasificador, `TestClassifierE2E` fallaba 6/8 y los 6
fallos colapsaban a `compliance`. Pero el mismo input daba dominios distintos entre
corridas: el test ejecuta el **prompt crudo** vía `claude -p`, que es no-determinista (con
`compliance` como atractor erróneo). Producción NO usa esa ruta directa: clasifica con
`cache → custom → keywords → LLM → chat`, y la capa de keywords (determinista) resuelve la
mayoría ANTES del LLM. Al ejercer `_keyword_classify` directamente aparecieron dos bugs
reales que el e2e ocultaba:

1. **`_strong_keyword_match` con first-match-wins**: "¿qué dice la AEAT sobre el modelo
   303?" matchea a la vez `rag` ("qué dice") y `compliance` ("aeat"/"modelo 303"). Como el
   dict listaba `rag` antes, ganaba el genérico → ruteo fiscal a RAG, 100% reproducible. El
   e2e lo daba en VERDE porque el LLM flaky devolvió compliance por suerte.
2. **HR sin tipos de contrato**: "da de alta a María, contrato indefinido" → `unknown` →
   caía al LLM flaky → misrouteado. "contrato" solo vivía en `documents`, empatando.

**Patrón antipatrón:** (a) testear la calidad del routing contra un LLM no-determinista y
fiar la guardia de un único sample — un verde por azar oculta un bug determinista, y un
rojo no distingue "prompt malo" de "el modelo tiró una moneda". (b) Desambiguar keywords
solapados por el ORDEN de inserción del dict: frágil e implícito; un término genérico
colocado "primero" gana a uno específico.

**Regla de prevención:**
1. La lógica determinista (keywords, scoring, regex) se testea **sin el LLM**, con una tabla
   `input→dominio` que es la guardia real. Reservar el e2e con LLM para smoke, nunca como
   única red de routing. → `backend/tests/test_classifier_keyword_routing.py`.
2. Cuando varios patrones solapan, desambiguar por **especificidad explícita**
   (maximal-munch: el keyword más largo gana), no por orden de dict. Es más robusto Y se
   alinea con la intención que el orden manual intentaba aproximar ("modelo 303" > "qué
   dice"; "crea cliente" > "factura"). El orden solo desempata longitudes iguales.
3. Un strong keyword debe ser de alta precisión: "contrato indefinido/temporal/fijo
   discontinuo" son señal HR inequívoca (nadie los dice para archivar un PDF); "qué dice" a
   secas NO es señal rag — el objeto ("según el documento") sí lo es.

---

## 2026-06-21 — Keywords deben ser STEMS, no formas concretas (acento/plural/conjugación)

**Contexto:** campaña de pruebas LLM (todos los dominios, contra tenant Demo Masivo). El
routing por keywords falló en automatizaciones: "lista mis automatizaciones activas" →
`billing`; "automatiza que cada fin de mes se generen las nóminas" → `unknown`→LLM→`hr`. Las
keywords de workflow eran `"automatización"` (con tilde) y `"automatizar"` — y el match es
substring (`kw in intent_lower`), así que NINGUNA captura `"automatiza"`, `"automatizaciones"`
(plural sin tilde) ni el imperativo `"automatiza"`. Es la MISMA familia que el bug de
[2026-06-20]: una forma léxica concreta no cubre las variantes que el usuario teclea.

**Patrón antipatrón:** registrar keywords como palabras "de diccionario" (singular, con
tilde, infinitivo). El usuario escribe plurales, imperativos y sin tildes. El match por
substring las pierde en silencio → cae al LLM (no determinista) → misroute.

**Regla de prevención:**
1. Preferir el **stem más corto e inequívoco** como keyword: `"automatiza"` cubre de un golpe
   automatiza/automatizar/automatización/automatizaciones (todas lo contienen). Un stem >
   N formas concretas y nunca se queda corto ante una flexión nueva.
2. Cubrir variantes recurrentes ("cada fin de mes" junto a "cada lunes/día/semana"), pero
   NO meter términos genéricos ambiguos en _STRONG_ ("cada mes" colisiona con consultas
   "¿cuánto facturamos cada mes?"): esos van solo a _KEYWORD_MAP (scoring) o se omiten.
3. Toda corrección de routing entra como caso en `tests/test_classifier_keyword_routing.py`
   (con su guarda de colisión), no solo el happy path.

**Hallazgos a nivel LLM/agente — investigados: NO eran bugs, eran prompts de test
infraespecificados.** (Lección: un "FAILED" de campaña LLM hay que reproducirlo de forma
determinista antes de creerlo — el verdadero defecto puede estar en el caso de prueba.)
- "da de alta a María, contrato indefinido, 2200€" → el agente HR pidió datos en vez de
  crear. Causa: `create_employee` exige NIF EN 3 CAPAS (firma `nif: str` sin default; guard
  `if not nif.strip(): return Error`; prompt "NIF obligatorio") — por diseño, un empleado sin
  NIF no tributa. El prompt de la campaña venía SIN NIF → pedirlo es correcto, no un fallo.
- "calcula la nómina de un empleado" → el agente respondió "problema técnico con la
  herramienta". Reproducido directo (sin LLM) con un empleado real:
  `calculate_and_create_payroll` FUNCIONA (genera DRAFT con SS/IRPF correctos). El fallo fue
  que el prompt decía "un empleado" (genérico, sin NIF/nombre) → el agente no pudo resolver a
  quién y lo verbalizó mal. Pulido opcional: que el agente diga "¿de qué empleado?" en vez de
  "problema técnico". Tools HR sanas.
