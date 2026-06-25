# Inbox /forja — hallazgos en app/agents (2026-06-25, barrido #11)

0 auto-fixes: judgment/fiscal/ya-evaluado. Para tu criterio:

## Para revisar
1. **billing/_invoice_write_tools.py:37,95 (y _invoice_query/_albaran/_invoice_create) usan
   `AsyncSessionLocal()` directo, no `tool_session(tenant_id)`** — `inventory/tools.py` sí usa
   `tool_session`. El finder lo marca [alta] por posible fuga de tenant bajo concurrencia.
   ⚠️ MATIZ: el aislamiento RLS ya se evaluó como SÓLIDO (listener global + fail-closed; un asesor
   previo sobredimensionó esto — ver memoria `rls-isolation-is-sound`), y los ContextVar de asyncio
   son task-locales (no heredan otro tenant). Probable severidad real: MEDIA (consistencia, no P0).
   Fix recomendado (consistencia): alinear billing a `tool_session(tenant_id)` como inventory. Toca
   sesión/transacción en ruta fiscal → revisión humana (no cambia cálculos).

2. **billing/agent.py sin `recursion_limit` explícito** [marginal]. LangGraph capa a 25 por defecto;
   un loop de tool-calling rebota 25 veces y lanza `GraphRecursionError` que el dispatcher captura en
   el `except Exception` genérico (→ AgentResult(success=False), correcto). Mejora: `compile(recursion_limit=15)`
   + capturar `GraphRecursionError` explícito antes del catch-all para fallar más rápido.

3. **orchestrator/_dispatch_handlers.py:232 timeout 300s vs comentario "180s"** [media]. Mismatch
   código/comentario; con doble-retry (300+300) puede superar el guard global de 600s sin cancelar el
   task en vuelo. Decidir el timeout correcto (180 vs 300, ¿intencional?) y envolver `_execute_one` en
   un `wait_for` global. Decisión de diseño.

4. **tenant_context.py:56-57 `enforce_tenant` no fuerza cuando ContextVar es None** [baja]. Documentado
   ("sin contexto no podemos forzar"), pero es brecha silenciosa para agentes invocados directos. Fix
   limpio de bajo riesgo: `log.error` cuando ContextVar None y `tenant_id` en kwargs (auditable).
   Candidato a auto-fix en un turno futuro (solo observabilidad, cero cambio de comportamiento).
