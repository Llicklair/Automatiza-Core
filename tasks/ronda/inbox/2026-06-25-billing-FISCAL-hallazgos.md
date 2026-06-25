# Inbox /forja — hallazgos FISCALES en services/billing (2026-06-25, barrido #8)

El loop arregló la numeración no correlativa de recurrentes en AMBAS rutas (commands +
scheduler) → PR #51. Estos quedan para tu criterio (tocan cadena VeriFactu / XML / asientos):

## ⚠️ ALTA — cadena VeriFactu
2. **`backfill_verifactu.py:135` el backfill excluye rectificativas de la cadena hash**
   [alta]. Filtro `Invoice.invoice_type == "issued"`. Las rectificativas históricas (previas a
   activar VeriFactu) no entran en el backfill, pero `maybe_append_verifactu_record` SÍ las
   encadena en tiempo real → un tenant que tenía rectificativas antes de activar VeriFactu queda
   con una cadena INCOMPLETA (la AEAT exige todos los registros, RD 1007/2023 Art. 8). Fix
   propuesto: filtro `invoice_type.in_(("issued","rectificativa"))` + mapear `tipo_factura` igual
   que `verifactu_chain.py`. **NO auto-fixeado: toca la cadena append-only legal → hazlo tú con
   test de integridad de la cadena (orden cronológico F1/R1).**

## Media / baja
3. **`registro_facturacion.py:220-225` fallback de desglose sin líneas** [media]. Si `_detalles`
   no recibe líneas, calcula el tipo como `(cuota/base)*100` sobre totales de cabecera → puede dar
   un `TipoImpositivo` inexistente (p.ej. 15.5% en factura mixta) que la AEAT rechaza. Solo se
   activa sin `selectinload(lines)` (raro en prod). Fix: forzar carga de líneas o excepción
   explícita. Toca XML fiscal → revisión humana.
4. **`auto_accounting.py:61,100` `float(invoice.amount_total)` en el asiento** [baja]. La tolerancia
   del cuadre (≤0.01) lo absorbe, pero el 572/430 puede diferir 1 céntimo del devengo. Higiene.

## Follow-ups del fix de numeración (PR #51)
- DRY: `tasks_scheduler._process_recurring_invoices` reimplementa `commands.run_recurring`
  (dos implementaciones divergentes del mismo concepto). Considerar que el worker delegue en el
  servicio. (Decisión de diseño.)
- Test ausente del path del scheduler: añadir test que verifique REC{year}-0001/0002 (no
  timestamps, no colisiones) en `_process_recurring_invoices`.
