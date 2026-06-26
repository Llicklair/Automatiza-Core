# Inbox /forja v2 — ejecución de tools de agentes (2026-06-26, lente correctitud+errores)

Flujo: capa LangGraph de tools. FIX #1+#2 (aplicar `_isolated`/`enforce_tenant` a RAG y email, como los otros
8 agentes) ya hecho → PR #52, 63 tests verde. Severidad real media (consistencia/defensa en profundidad;
RLS+ContextVar ya eran backstop, NO era fuga explotable). Quedan dos:

## Media — accounting usa `AsyncSessionLocal()` directo en vez de `tool_session()`
3. **`agents/accounting/tools.py:73,118,167,213,279`** — los 5 tools abren `async with AsyncSessionLocal()`
   en vez de `async with tool_session(UUID(tenant_id))`. El contrato de `shared/db.py` marca `tool_session()`
   como "punto único"; `AsyncSessionLocal()` directo es bypass deliberado. HOY funciona porque
   `enforce_tenant` (agent.py:37-39) fija el ContextVar antes de ejecutar la tool → RLS actúa. Pero es una
   ventana de riesgo si se invoca la tool fuera del flujo normal (tests, invocación directa, reset del
   ContextVar en otro contexto async). `create_journal_entry` además ESCRIBE. Fix objetivo: reemplazar los 5
   por `tool_session(UUID(tenant_id))` siguiendo el patrón del resto de agentes. Defensa en profundidad
   (no inflar: RLS cubre el caso normal). Revisar que `tool_session` exista y su firma.

## Baja — `create_journal_entry` no tolera `lines` como string JSON
4. **`agents/accounting/tools.py:36`** — `lines: list[dict]` llega del LLM; si el LLM manda una STRING JSON
   en vez de lista (LangChain lo hace según el modelo), `sum(... for ln in lines)` lanza
   `AttributeError: 'str' object has no attribute 'get'`. Cae en el `try/except Exception` exterior → devuelve
   `"Error creando asiento: ..."` (NO rompe la conversación, bien), pero el mensaje es opaco y el LLM no sabe
   corregirse. Fix objetivo: al inicio, `if isinstance(lines, str): lines = json.loads(lines)` con
   `except (json.JSONDecodeError, TypeError): return "Error: 'lines' debe ser una lista JSON de asientos."`.
   Mejora el feedback al LLM. (Patrón aplicable a otros tools que reciban listas/dicts del LLM.)
