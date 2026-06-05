# Pruebas de iteración del ERP — fallos encontrados (2026-06-03)

**Motor IA:** `claude_code` (CLI, sin API key) · **Tenant:** `9cd49fbb…` · **Batería:** 29 prompts en lenguaje natural sobre todos los dominios.
**Veredicto global: 24 PASS / 5 FAIL.** Reporte crudo: `tasks/smoke_orchestrator_2026-06-03.md`.

Los 5 fallos se agrupan en **3 causas raíz** (no 5 bugs independientes).

---

## Causa raíz A — El adaptador `claude_code` rehúsa usar tools (probabilístico) ★ dominante

**Fallos:** `hr_simple` (recruitment), `iter13_uploads` (billing). Instancias "suaves" también en `ambiguous`.

**Qué pasa:** el adaptador inyecta las tools como **texto en el system prompt** y pide al modelo que emita un formato especial de tool-call ([claude_code.py:380-412](backend/app/core/llm/claude_code.py#L380-L412)). Pero el LLM corre como otra instancia de `claude -p`, y **a veces "se da cuenta"** de que esas tools no son MCP reales y lo dice literalmente:
> "The tools listed in the system prompt appear to be injected as context-level tool definitions but are not registered as callable MCP tools in this Claude Code session."

La frase contiene "claude code" → salta `LLMRefusedToolUseError` y el agente devuelve `success=false`.

**Por qué es la causa dominante:** es **no determinista**. `billing` y `crm` PASARON en unos prompts y FALLARON en otros con entrada equivalente. Cualquier agente con tools es frágil bajo `claude_code`. El código de los agentes es idéntico en estructura (`get_llm().bind_tools(tools)` + `ToolNode`); el fallo no está en el agente, está en el provider.

**Recomendación:** endurecer el prompt de tools (instrucción explícita "estas tools SÍ están disponibles, invócalas en el formato X, NO expliques que no tienes acceso") y/o reintento automático en `_process_response` cuando se detecta la rehúsa, en vez de propagar excepción al primer intento. Considerar que para el piloto el provider real es BYOK `anthropic` (tool-calling nativo), donde este problema **no existe** — conviene medir la batería también con `anthropic` antes de invertir en mitigar `claude_code`.

---

## Causa raíz B — Timeout de agente (180s) aborta la cadena entera

**Fallo:** `e2e4_quarterly_close` (cadena de 7 pasos).

**Qué pasa:** `Timeout: el agente 'billing' no respondió en 180s (2 intentos)`. El plan era `banking → billing → compliance → excel → documents → custom → email`. `banking` completó, `billing` agotó 180s dos veces, y **toda la cadena murió** (`compliance/excel/documents/custom/email` quedaron `pending`, nunca se ejecutaron).

**Dos problemas:** (1) 180s es ajustado para llamadas `claude_code` en pasos complejos (el CLI es lento: prompts E2E individuales tardaron 320-630s). (2) Un solo paso que falla **aborta el resto sin degradación elegante** — no hay continuación parcial ni resumen de lo que sí se hizo.

**Recomendación:** subir el timeout para el provider `claude_code`, y/o permitir que la cadena continúe con los pasos independientes y reporte el paso fallido en lugar de abortar todo.

---

## Causa raíz C — Manejo débil de entradas ambiguas / entidad inexistente

**Fallos:** `ambiguous` ("Haz lo de siempre con Acme"), `e2e5_lead_to_campaign` (lead "Mercados S.L.").

- **`ambiguous`**: en vez de **pedir aclaración**, el Coordinador alucinó un plan de 4 pasos (rag→crm→billing→email) y lo ejecutó. El propio agente de resumen acabó diciendo "no se pudo completar". El Coordinador debería detectar intención no resoluble y preguntar, no inventar un workflow.
- **`e2e5`**: el lead "Mercados S.L." **no existe en CRM** (NIF/email "No registrado"). `qualify_leads` no encontró datos reales y devolvió `success=false`, pero emitió un informe markdown como si fuera válido. Falta distinguir "entidad no encontrada → pedir datos" de "fallo del agente".

**Recomendación:** reforzar el nodo `classify`/`validate` del Coordinador para marcar `requires_human_approval`/clarificación cuando la intención es ambigua o la entidad referida no existe, antes de dispatchar.

---

## Hallazgos secundarios

1. **Datos de prueba duplicados:** el CRM devolvió "6 registros duplicados" de "Acme" — cada corrida del smoke crea entidades nuevas. Conviene limpiar el tenant de smoke o usar nombres únicos por corrida.
2. **Gap arquitectónico (no bug):** el flujo nuevo de escáner / Excel·CSV→ERP **no expone ningún `@tool` al LLM** ([scanner.py](backend/app/api/v1/routes/scanner.py), [erp_import.py](backend/app/services/documents/erp_import.py)) — se dispara por endpoints HTTP/upload. Por eso `iter13_uploads` ("procesa el lote que subí hoy") no puede funcionar vía prompt: el Coordinador no tiene forma de alcanzar ese flujo. Es esperado, pero el clasificador no debería aceptar esos prompts como si fueran ejecutables.

---

## Próximos pasos sugeridos (elige)

- **Medir flakiness:** re-correr la batería 2-3 veces para cuantificar la tasa de rehúsa de `claude_code`.
- **Comparar provider:** correr la batería con `DEFAULT_LLM_PROVIDER=anthropic` (BYOK real del piloto) para aislar cuántos fallos son solo de `claude_code`.
- **Ampliar batería:** casos límite de validación (importe negativo, IVA fuera de rango, mes 13, nómina duplicada, NIF inválido) — ya diseñados, pendientes de añadir.
- **Arreglar la causa A** (la de mayor impacto en fiabilidad).
