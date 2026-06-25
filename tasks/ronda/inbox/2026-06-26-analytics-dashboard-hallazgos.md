# Inbox /forja v2 — analítica / dashboard (2026-06-26, lente correctitud+perf)

Flujo: `services/analytics/dashboard.py::get_dashboard`. FIX #3 (ticket medio excluye rectificativas) ya
hecho → PR #52, 13 tests verde. El finder confirmó que NO hay div-by-zero, None sin manejar, off-by-one de
fechas ni fuga de tenant (todo con guards / `coalesce` / `tenant_id`). Quedan:

## Media — N+1 en cashflow de 6 meses
1. **`dashboard.py:214-236`** — el cashflow de 6 meses se calcula con ~12 queries seriales (una por mes ×
   ingresos/gastos) en vez de UN `GROUP BY` por mes. Perf: 12 roundtrips por carga de panel. Fix objetivo
   pero DELICADO de verificar: un `GROUP BY date_trunc('month', date)` debe producir EXACTAMENTE el mismo
   resultado, incluido **devolver 0 para los meses SIN datos** (el bucle actual los rellena a 0; un GROUP BY
   crudo los omite → habría que reconstruir la rejilla de 6 meses en Python tras la query). Por eso no
   auto-fix este turno: requiere equivalencia byte a byte (patrón evaluador, como el N+1 del 347). Recomendado
   para un turno dedicado con test de equivalencia.

## Revisado — NO es bug (diseño intencional)
- ❌ #2 "el dashboard no filtra `Invoice.is_demo` → datos demo inflan KPIs": es INTENCIONAL. El seed de
  onboarding siembra datos demo (`is_demo`) **deliberadamente VISIBLES en analítica** (para que el panel no
  salga vacío en el onboarding) y **EXCLUIDOS de TODO lo fiscal/VeriFactu**. Filtrar `is_demo` del dashboard
  ROMPERÍA esa experiencia. Si en algún momento se decide que el panel "real" no debe mezclar demo, sería una
  decisión de PRODUCTO (p.ej. ocultar demo una vez el usuario tiene datos propios), no un bug a parchear a
  ciegas. Dejar como está salvo decisión explícita.
