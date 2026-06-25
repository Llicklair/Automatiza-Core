# Inbox /forja — hallazgos en services/hr (2026-06-25, barrido #4)

El loop arregló #1 (recarga de Payroll sin tenant → PR #50). Estos quedan para tu criterio:

## Para revisar
1. **`_payroll.py:~276` `generate_and_save_payroll_pdf` crea su propia `AsyncSession`** [alta arch].
   Viola la regla "services reciben db como parámetro". Además silencia errores de guardado y
   el path del PDF no lleva `tenant_id` → dos empleados homónimos del mismo periodo en tenants
   distintos pueden pisarse el fichero. Fix: recibir `db` (o tarea background con manejo
   explícito) + prefijo `tenant_id` en el path. Refactor de firma → afecta llamadores.

2. **`queries.py` cuota_solidaridad con `year` ausente en `update_payroll`** [media, FISCAL].
   `update_payroll` llama `calc_payroll(...)` sin `year`, así que se aplican los tipos de cuota
   de solidaridad de 2026 a cualquier año. Para salarios altos (>5101€/mes) la cuota sale mal.
   ⚠️ Es CÁLCULO DE NÓMINA (fiscal) → revisar con cuidado antes de tocar; no lo auto-arreglé a propósito.

3. **`_special_docs.py:27` `db.get(Employee)` puede devolver objeto cacheado** [media].
   La identity map de SQLAlchemy podría devolver un Employee cargado antes con otro tenant; el
   check `emp.tenant_id != tenant_id` lo mitiga, pero el patrón correcto es `select(...).where(
   id, tenant_id)`. Fix limpio y de bajo riesgo (candidato a auto-fix en otro turno).

4. **`commands.py:~590` `clock_out_attendance` sin `db.rollback()` en el except del JornadaRecord** [media].
   Si el segundo commit (JornadaRecord) falla y deja la sesión inválida, las operaciones
   posteriores de la request petan. Fix: `await db.rollback()` en el except antes del log.
   Limpio y pequeño (candidato a auto-fix).
