# Inbox /forja v2 — cálculo de nómina (2026-06-25, lente correctitud)

El bug grave (#1, doble-neto al editar jornada parcial/14 pagas/IT) está ARREGLADO + test verde → PR #52.
Estos quedan para tu criterio (cambian importes de nómina):

## Para revisar
2. **`_payroll.py:162-179` `update_payroll`: `other_deductions` desincronizado** [media] — si en la MISMA
   llamada se envían `base_salary` Y `other_deductions`, la rama de `base_salary` se ejecuta y la de
   `other_deductions` se salta (`and "base_salary" not in data`); el nuevo `other_deductions` del payload
   no re-entra en `deductions` (que usa el valor almacenado). Resultado: `net_salary` usa el valor nuevo
   pero `deductions` refleja el viejo. NOTA: el fix de #1 reescribió esta zona — verificar si este caso
   sigue vivo tras el cambio (puede haberse resuelto al unificar en `calc_payroll_for_employee`).

3. **`queries.py:103` `cuota_solidaridad_trabajador`: año futuro → 0** [media] — el tope SS usa
   `_BASE_MAX_DEFAULT_YEAR` (=2026) pero los TIPOS de cuota de solidaridad solo están indexados 2025/2026.
   Para `year=2027` (cuando llegue) `.get(2027)` → None → cuota 0 sobre salarios >5101,20€. Recálculo:
   salario 6000€/2027 → correcto ≈1,72€/mes, código devuelve 0. Bajo impacto/año pero importe de nómina.
   Fix: extender `_CUOTA_SOLIDARIDAD_TIPOS` cada año / fallback al último año conocido. (Relacionado con el
   inbox hr previo del `year` ausente.)

4. **`queries.py:235-242` doble redondeo en `total_ss`** [baja] — cada componente SS se redondea a 2
   decimales y luego se redondea la suma → ±0.01-0.02€ de discrepancia entre la suma manual del PDF y el
   total impreso. No cambia el `deductions` almacenado. Fix: sumar en crudo y redondear solo el total.
