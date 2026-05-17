# Limpieza arquitectónica post-auditoría LLM

Fecha: 2026-05-17
Estado: en planificación
Origen: `tasks/audit-llm-e2e.md` (3 hallazgos 🔴 Alto)

## Estado verificado de los 3 hallazgos 🔴 Alto

### #1. 6 `@tool` sin docstring — ✅ YA RESUELTO
Verificación 2026-05-17: `create_opportunity`, `update_opportunity_stage`,
`create_client` (crm), `send_email` (email), `create_position`,
`list_candidates` (recruitment) **ya tienen docstring**. La auditoría está
stale — los commits posteriores los añadieron (incluso con notas AI Act).
Cerrar este hallazgo en `audit-llm-e2e.md`.

### #2. `__init__.py` filtran detalle en 11 dominios — 🔴 REAL
Auditados los 11 paquetes (`accounting`, `banking`, `billing`, `compliance`,
`crm`, `documents`, `excel`, `hr`, `marketing`, `rag`, `recruitment`).
Exportan `graph`, `workflow`, `<dom>_agent_node`, `<dom>_finalize_node`,
`<DOM>_SYSTEM_PROMPT`, tools individuales y helpers internos.

**Mapa de consumidores reales** (verificado 2026-05-17):
- `from app.agents.<dom> import graph` → 11 dispatchers
- `from app.agents.<dom> import <tool>` → `tool_registry.py` (líneas 30-153)
- `from app.agents.email import run_email_agent` → `dispatchers/misc.py:110`
- `from app.agents.email import send_email_direct` → `services/email_sender.py:27`,
  `routes/messaging.py:173`
- `from app.agents.workflow import run_workflow_agent` → `dispatchers/misc.py:166`
- `from app.agents.<dom>.agent import <node>` → tests internos (no afecta `__init__`)

**Nadie consume**: `*_agent_node`, `*_finalize_node`, `workflow` (sin compilar),
`<DOM>_SYSTEM_PROMPT` (las constantes) desde `__init__.py`. **Esos sí se
pueden quitar sin riesgo.**

### #3. `AgentResult` ausente en 12/14 `agent.py` — 🔴 REAL (parcial)
Confirmado: 12 dominios devuelven
`{"status": "done", "agent_results": [final_result.model_dump()]}` desde
los nodos `finalize`, **no envuelven en `AgentResult(success, output, error)`**.
Solo `email/agent.py` y `workflow/agent.py` lo hacen.

**Mitigación actual ya existente**: los dispatchers capturan excepciones y
construyen `AgentResult(success=False)` en `_dispatch_handlers.py` —
contrato hacia el endpoint está protegido. El refactor cierra el contrato
*dentro* del agente, no resuelve un bug.

---

## Dos opciones de refactor para #2 + #3

### Opción A — Pragmática (esta sesión, ~30-45 min, riesgo bajo)
**Solo #2 parcial: limpiar lo que nadie usa**

Por cada `__init__.py` de los 11 dominios:
- Mantener: `graph`, tools individuales públicas (las que importa
  `tool_registry.py`), `run_email_agent`+`send_email_direct` (email),
  `run_workflow_agent` (workflow).
- Quitar del export público: `workflow` (uncompiled), `<dom>_agent_node`,
  `<dom>_finalize_node`, `<DOM>_SYSTEM_PROMPT`, helpers internos, `tools`
  list (si `tool_registry` ya consume las tools individuales).

**Resultado**: huella de `__init__.py` reducida ~50%, cero código roto,
mensaje "estos símbolos son internos del paquete" queda claro.

### Opción B — Pura (sesión separada, ~5-7h, riesgo medio)
**Combina #2 completo + #3**

1. Añadir `async def run_agent(state, ...) -> AgentResult` a cada `agent.py`
   que envuelva `graph.ainvoke()` + construya `AgentResult(success, output, error)`.
2. Migrar 11 dispatchers de `graph.ainvoke()` a `run_agent()`.
3. Migrar `tool_registry.py` a `from app.agents.<dom>.tools import ...`
   (lugar correcto, no via `__init__`).
4. Limpiar `__init__.py` a `from .agent import run_agent` exclusivamente.

**Resultado**: cumple CLAUDE.md al pie de la letra. Contrato `AgentResult`
end-to-end. Pero toca ~30 archivos y requiere correr toda la suite tras
cada bloque.

---

## Plan recomendado

1. **Ahora**: ejecutar Opción A. Commit `refactor(agents): limpiar __init__.py
   internos`.
2. **Sesión separada**: Opción B con plan dedicado, una vez confirmes la
   prioridad vs el roadmap M1-M2 (numeración correlativa, JWT safeStorage,
   AEAT FNMT) que tiene fechas-tope más cercanas.

## Verificación post-cambio Opción A

- [ ] `py -3.11 -m pytest -m "not slow and not e2e" --tb=line -q` verde
- [ ] `grep -rn "from app.agents.<dom> import" backend` confirma cero imports
      a símbolos removidos
- [ ] `npx gitnexus analyze` re-indexado

## Estado de los hallazgos

- [x] #1 Docstrings tools — ya cumple, cerrar en `audit-llm-e2e.md`
- [ ] #2 `__init__.py` limpieza — opción A pendiente esta sesión
- [ ] #3 `AgentResult` en `agent.py` — opción B, sesión separada con plan
