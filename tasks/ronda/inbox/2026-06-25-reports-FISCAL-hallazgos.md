# Inbox /forja — hallazgos FISCALES en services/reports (2026-06-25, barrido #10)

El loop arregló el Modelo 200 (no restaba retenciones soportadas → PR #51). Estos quedan:

## Media — tiene caveat
2. **`fiscal.py:152-153` vs `modelos_aeat.py:232-237` filtro de nóminas inconsistente** [media].
   `aggregate_fiscal` (snapshot del dashboard) filtra nóminas por `period_start>=start AND
   period_END<=end`; `_payrolls_in_period` (111/190/100/200) filtra por `period_START<=end`. Una
   nómina a caballo (dic→ene) entra en el 111 del Q4 pero NO en el snapshot fiscal del Q4 → cifras
   de retenciones distintas entre el widget y el 111 sin motivo legal. El criterio correcto del 111
   es la fecha de inicio (devengo). Fix: uniformar `aggregate_fiscal` a `period_start <= end`.
   ⚠️ Caveat: puede alterar el histórico de snapshots → confirma que el caso multi-mes existe antes
   de tocar.

## Baja — no afecta declarado
3. **`fiscal.py:373-380` el CSV del libro registro usa `float` en la aritmética de línea** [baja].
   Los modelos (303/390) usan Decimal; el CSV usa float → error sub-céntimo (~1e-14), no descuadra
   declaraciones pero introduce inconsistencia entre el CSV exportado (que el usuario compara línea a
   línea contra el 303) y los modelos. Fix mecánico: usar `_d()` (ya definido en el módulo) en las
   operaciones de línea del CSV.
