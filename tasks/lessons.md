# Lecciones aprendidas

Registro de patrones detectados durante el trabajo para no repetir errores.

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

## 2026-05-08 — Bug pendiente: custom employee timeout no se propaga

**Síntoma**: tasks dirigidas al CTO custom (`Marcos Recio`, domain=custom) tardan
~8 minutos en pasar de `executing` a `failed` aunque el timeout interno
configurado en `_invoke_dynamic_employee` es 300s.

**Lo que SÍ pasa**: al final, el task acaba en `failed` con error
"Error: Claude Code CLI no respondio en el tiempo limite". Es decir, el
timeout SÍ se dispara — pero se queda colgado en alguna parte del cleanup
(probablemente `await db.commit()` o `log_activity` post-timeout).

**Lo que NO pasa**: el wait_for(300s) que envuelve `graph.ainvoke()` no
parece propagarse hasta el polling externo en menos de ~480s.

**Hipótesis a investigar**:
1. Tras el TimeoutError, `employee.status = "idle"` + `db.commit()` puede
   bloquearse si la sesión de BD quedó sucia.
2. El subprocess `claude_code` sigue corriendo en background tras
   `subprocess.run(timeout=...)` y eso bloquea el event loop.
3. La excepción se traga en algún sitio antes de propagarse al TaskRunner.

**Cómo reproducirlo**:
1. Pedir al CTO un informe extenso ("informe de e-commerce B2B 2026 con tablas...")
2. Observar que `tenant_documents` no recibe el PDF inmediatamente y la
   task queda en `executing` mucho más allá de los 300s configurados.

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
