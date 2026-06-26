# Inbox /forja v2 — asientos contables / partida doble (2026-06-26, lente correctitud)

Flujo: creación de asiento (journal entry). FIX #1+#2+#3 (validar líneas: no negativos / no debe+haber juntos
/ no línea hueca, en `JournalLineCreate`) ya hecho → PR #52, 62 tests + regresión. El finder confirmó que el
NÚCLEO está bien: cuadre debe=haber con `Decimal` (no float), bloqueo de periodo cerrado en ambas rutas,
tolerancia 0.01€ justificada, sin doble-registro, sin asiento sin tenant. Quedan dos:

## Media — la validación de línea solo cubre la ruta HTTP, no el tool del agente ni el servicio
- El `model_validator` añadido vive en `JournalLineCreate` (schema HTTP). El **agente** (`agents/accounting/
  tools.py`) construye las líneas como dicts y llama al SERVICIO `create_journal_entry`
  (`services/billing/commands.py`) directamente, SIN pasar por el schema → un LLM podría crear un asiento con
  una línea negativa/mixta/hueca que el schema rechazaría. Fix robusto (delicado, fiscal): replicar las 3
  comprobaciones a nivel de SERVICIO (junto al cuadre global ya existente en `commands.py:449-455`), así cubre
  HTTP + tool + cualquier caller. Revisión humana (toca la función canónica de asientos).

## Baja — ruido de conversión float en `norm_lines` del tool
4. **`agents/accounting/tools.py:67`** — `norm_lines` convierte los importes a `float` antes de llamar al
   servicio (que ya acepta `str`/`Decimal`). Para importes con muchos decimales (p.ej. nóminas a 4 decimales)
   la ida y vuelta `Decimal→float→str→Decimal` puede acumular error binario por debajo del umbral de 0.01€.
   Hoy no produce rechazo falso (tolerancia consistente), pero es ruido innecesario. Fix: pasar los importes
   como `str` en `norm_lines` (el servicio los acepta). Delicado (toca flujo fiscal) → revisión.

---
(Recordatorio: pendientes previos del mismo módulo en `2026-06-26-agentes-tools-hallazgos.md`: #3 accounting
usa `AsyncSessionLocal` en vez de `tool_session`; #4 `lines` como string JSON sin coerción.)
