# Inbox /forja v2 — RRHH empleados/contratos (2026-06-25, lente correctitud+errores)

Flujo: ciclo de vida de empleado/contrato. FIX #4 (validación jornada>0 + orden de fechas de contrato en
`EmployeeCreate`/`EmployeeUpdate`, sin tocar `EmployeeBase`/`Response`) ya hecho → PR #52, 170 tests HR
verde. Quedan tres:

## ✅ RESUELTO (2026-06-26, PR #52 commits f3b0e05+ab529a4) — delete→409 en empleados/clientes/presupuestos/pedidos + test de regresión. El resto de la nota queda como registro.

## ⚠️ Alta — borrar empleado con nóminas = 500 (no 409) [patrón cross-cutting]
2. **`hr/commands.py:121 delete_employee` + ruta `hr_employees.py:90`** — `Payroll`/`Settlement`/
   `JornadaRecord`/`WorkSchedule`/`Attendance`/`Expense`/`LeaveRequest` tienen FK a `employees.id` SIN
   `ondelete`, y el ORM es `lazy="dynamic"` (no cascada). `db.delete(emp)` + commit → `IntegrityError` no
   capturado → el handler global (`main.py:188`) devuelve **500** en vez de **409** con mensaje. VERIFICADO:
   la ruta solo checa el bool→404, NO mapea `ValueError`/`IntegrityError` (la afirmación inicial de que "la
   ruta ya da 409" era falsa). Fix correcto: capturar `IntegrityError` en `delete_employee` y lanzar la
   excepción de DOMINIO del repo (`AppException`, ver `main.py:156`) con status 409 + mensaje "el empleado
   tiene registros asociados". **Es el MISMO patrón que clientes/quotes/orders** (ya en inbox `crm-clientes`
   #2) → merece UN PR dedicado que lo resuelva en todos: helper `raise_conflict_on_fk(...)` o catch común.

## Media — listado mezcla empleados de baja con activos
1. **`hr/queries.py:320 list_employees` no filtra `status`** — devuelve `active`+`inactive`+`leave`
   juntos. Lo consumen 4 sitios: ruta frontend (`hr_employees.py:47`), AI (`ai_employees.py:38`),
   horarios (`hr_time.py:110`), agente (`_employee_tools.py:29`). NO es fuga (RLS activo) pero rompe la
   invariante "listado = activos". Cambiar el default a `status != 'inactive'` afectaría a los 4
   consumidores (alguno puede querer todos) → **decisión de producto**, no auto-fix. Fix sugerido:
   parámetro `include_inactive: bool = False` y que cada caller pida explícitamente lo que necesita.

## Media — fichaje `clock_in` con fecha naive del servidor
3. **`hr/commands.py:539 clock_in` usa `date.today()`** (reloj del servidor) mientras guarda
   `clock_in = utcnow` (tz-aware) → incoherencia. En cloud-UTC un fichaje a las 23:30 hora España queda con
   `date` = día anterior → registro de jornada legal (RD 8/2019) con fecha errónea. En el escritorio (corre
   en TZ del usuario) es correcto. Fix NO trivial (la TZ correcta es la del tenant, no hardcodear Madrid;
   o pasar la fecha desde el cliente) → decisión de diseño. Relacionado con el patrón `utcnow`/naive que ya
   apareció en `treasury/projection.py`.
