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
