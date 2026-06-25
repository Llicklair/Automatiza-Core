# Auditoría fiscal/contable — hallazgos NUEVOS (2026-06-25)

Auditor: correctitud fiscal/contable (AEAT/VeriFactu/IVA/IRPF/PGC).
Base: complementa `tasks/erp_review_2026-06-24.md` (B1–B23). No repite los Bnn salvo nota de confirmación.

Método: lectura estática de `services/{billing,accounting,aeat,banking,analytics,reports}` y `agents/{billing,accounting,hr}`. Sin ejecutar código.

---

## CRITICAL

### N1 — Las facturas en estado `draft` (y `pending`/`sent`) ENTRAN en los modelos 303/130/347/390 y en el snapshot fiscal
- **Archivo:** `services/reports/fiscal.py` (`aggregate_fiscal`, `build_modelo_303_data`) + `services/reports/modelos_aeat.py:_invoices_in_period` (modelos 130/347/390).
- **Qué descuadra:** Los queries filtran `tenant_id`, `invoice_type`, `is_demo` y rango de fecha, pero **NO filtran `Invoice.status`**. El campo nace `default="draft"` (`db/models/billing.py:71`). Una factura en borrador (aún no emitida, importes provisionales) se agrega como IVA devengado/soportado real → el cliente presenta un 303 con cuota que no corresponde. Peor: el **libro registro** sí filtra (`fiscal.py:337 status.notin_(["cancelled"])`), de modo que libro y modelo 303 NO cuadran entre sí para el mismo periodo.
- **Además — `cancelled` tampoco se excluye en 303/130/347/390:** una factura anulada sigue sumando devengo. (El libro la excluye; los modelos no → incoherencia doble.)
- **Fix (1 frase):** añadir `Invoice.status.notin_(["draft","cancelled"])` (o whitelist de estados emitidos) a TODOS los queries de `aggregate_fiscal`, `build_modelo_303_data` y `_invoices_in_period`, igual que ya hace el libro registro.

### N2 — Las rectificativas (abono) se suman como devengo POSITIVO en 303/390/snapshot, inflando el IVA repercutido
- **Archivo:** `services/reports/fiscal.py` (`aggregate_fiscal`, `build_modelo_303_data`); `services/reports/modelos_aeat.py:_invoices_in_period`.
- **Qué descuadra:** El filtro es `invoice_type == "issued"`. Una rectificativa se persiste con `invoice_type == "rectificativa"` e importes NEGADOS (`commands.create_rectificativa`, líneas con `unit_price` negativo). Resultado contradictorio: (a) si NO se incluye 'rectificativa' (caso actual), el abono no minora el IVA devengado del 303 → se ingresa IVA de más; (b) si se incluyera sin tratar el signo, sumaría positivo. Relacionado con **B8** (analítica) pero es un punto NUEVO: B8 era sobre el dashboard; esto es sobre los **modelos AEAT presentables**.
- **Fix:** incluir `invoice_type.in_(("issued","rectificativa"))` en el devengo del 303/390/snapshot; el signo negativo de la rectificativa minora automáticamente la base/cuota.

---

## HIGH

### N3 — El asiento de nómina IGNORA la cuota patronal de Seguridad Social (642) → coste de personal y P&G infravalorados
- **Archivo:** `services/billing/auto_accounting.py` (`create_payroll_journal_entry`).
- **Qué descuadra:** El asiento solo registra `sueldos`(640) debe, `ss_acreedora`(476), `irpf_retenido`(4751) y `remuneraciones_ptes`(465). NO hay línea 642 "Seguridad Social a cargo de la empresa" (la cuota patronal, ~30% del bruto) pese a que el dato existe (`hr.py:122 cuotas_empresa_json`, usado en `modelos_aeat.py:902/1011` y en el PDF de nómina). El asiento cuadra (debe=haber) pero el **coste real de personal queda infravalorado** → P&G, Modelo 200 (IS) y tesorería con cifras falsas. La 476 solo recoge la parte del trabajador, no la patronal.
- **Fix:** añadir línea 640/642 debe + ampliar 476 haber por la cuota patronal leída de `cuotas_empresa_json`.

### N4 — Modelo 130: ingresos/gastos = `amount_base` sin restar la retención IRPF soportada; casilla 06 forzada a 0
- **Archivo:** `services/reports/modelos_aeat.py:build_modelo_130_data` (+ `aggregate_fiscal` IRPF).
- **Qué descuadra:** `retenciones_soportadas` y `pagos_fraccionados_anteriores` se devuelven hardcodeados a `0.0`, pero el modelo Invoice SÍ tiene `retencion_irpf_amount` (`db/models/billing.py:102`) en facturas emitidas a/de profesionales. La casilla 06 (retenciones soportadas, que reducen el pago fraccionado) queda en cero aunque el dato exista → el autónomo paga de más en el 130. Además `aggregate_fiscal` fija `retenciones_facturas=0.0` ignorando ese mismo campo.
- **Fix:** agregar `sum(retencion_irpf_amount)` de las facturas del periodo a la casilla 06 del 130 y a `retenciones_facturas` del snapshot.

### N5 — `compute_invoice_totals` redondea por línea pero el desglose del 303 reagrupa con criterio distinto → micro-descuadres base vs cuota
- **Archivo:** `services/reports/fiscal.py:vat_breakdown_by_rate` vs `services/aeat/_aeat_layout.py:_detalles` (Verifactu XML) y `casillas_303`.
- **Qué descuadra:** `vat_breakdown_by_rate` acumula base y cuota EXACTAS (sin redondear) y redondea al final (correcto). Pero el desglose del XML Verifactu (`_detalles`) calcula `cuota = base_sum * rate/100` sobre `qty*unit` SIN aplicar `discount_percentage` (la rama con líneas ignora el descuento, mientras `vat_breakdown_by_rate` sí lo resta). En facturas con descuento de línea, la base/cuota del Verifactu XML diverge de la base del 303 y del total de la factura. NUEVO (no es B2).
- **Fix:** en `_detalles` restar `discount_percentage` igual que `vat_breakdown_by_rate`, o reutilizar esa función como única fuente de desglose.

---

## MEDIUM

### N6 — `create_journal_entry` valida cuadre con tolerancia `> 0.01` sobre floats → asientos con descuadre de 1 céntimo pasan
- **Archivo:** `services/billing/auto_accounting.py` / `commands.py:419` (`abs(total_debit-total_credit) > 0.01`).
- **Qué descuadra:** los importes son `float`; varias líneas (nómina con SS+IRPF+neto) pueden acumular error binario y un descuadre de exactamente 0.01 NO se rechaza (es `>`, no `>=`). El libro diario puede quedar con suma debe≠haber por céntimos. Menor pero real en libros oficiales.
- **Fix:** trabajar en `Decimal` y exigir cuadre exacto (`!= 0`), o `>= Decimal("0.01")` con redondeo previo.

### N7 — `delete_invoice` permite borrar una factura emitida SIN registro Verifactu, dejando hueco en la numeración correlativa
- **Archivo:** `services/billing/commands.py:delete_invoice`.
- **Qué descuadra:** solo bloquea el borrado si hay `VerifactuRecord`. En modo `no_remission` (Verifactu desactivado) una factura emitida con número correlativo asignado (`A2026-0007`) se borra → hueco en la serie, violando RD 1619/2012 Art. 6.1 (numeración sin saltos). El contador `InvoiceSeries.last_number` no retrocede.
- **Fix:** prohibir borrar facturas `issued` ya numeradas (solo permitir anular vía rectificativa) independientemente del modo Verifactu.

---

## Confirmaciones / refutaciones de Bnn

- **B1/B5 — RESUELTO (confirmado fix):** `create_invoice_payment_entry` y `create_payroll_payment_entry` ahora deduplican por `reference_id=PAY-INV-{id}` / `PAY-NOM-{id}`. Idempotencia correcta.
- **B17 (fechas inclusivas) — RESUELTO en fiscal:** todos los queries de `fiscal.py`/`modelos_aeat.py` usan `func.date(Invoice.date)` con `>= start` y `<= end`. Correcto. (El B17 original apuntaba a `analytics/dashboard.py`; revisar allí aparte.)
- **VeriFactu cadena — ROBUSTO (confirma nota del informe):** `order_verifactu_chain`/`find_tail_huella` ordenan por enlace hash (no `created_at`), advisory lock por tenant, idempotencia por `invoice_id`, append-only sin edit/delete. No se rompe la cadena. La rectificativa añade su PROPIO eslabón (R1), correcto.
- **Numeración (race) — ROBUSTO:** `next_invoice_number` usa `pg_advisory_xact_lock` + `SELECT FOR UPDATE`. Sin huecos por concurrencia (salvo N7, que es por borrado).
- **303 recargo de equivalencia — correcto:** `_RECARGO_BY_RATE` mapea 21→5.2/10→1.4/4→0.5 y solo aplica a facturas con `fiscal_regime=="recargo_equivalencia"`.

---

## Resumen
- **NUEVOS:** 7 (2 CRITICAL, 3 HIGH, 2 MEDIUM).
- **Causa raíz transversal:** los queries fiscales filtran `is_demo` pero olvidan `status` e `invoice_type` rectificativa (N1/N2); y el puente nómina→PGC ignora la cuota patronal y la retención soportada (N3/N4).
