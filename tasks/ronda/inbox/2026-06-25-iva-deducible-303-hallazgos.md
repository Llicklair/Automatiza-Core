# Inbox /forja v2 — IVA soportado deducible / 303 (2026-06-25, lente correctitud)

Flujo: facturas recibidas → `reports/fiscal.py` (`vat_breakdown_by_rate`, `_period_invoices_stmt`) →
`aeat/casillas_303.py` (casillas de deducible). VERIFICADO en código. Todo fiscal → **revisión humana,
no auto-fix; línea roja: no falsificar nada de la AEAT**.

## ⚠️ Confirmado — casilla 45 omite bienes de inversión (31)
1. **`casillas_303.py:226` `total_deducir = cuota_29 + cuota_37`** — la casilla 45 (Total a deducir) suma
   solo deducible corriente (29) + intracomunitario (37). El modelo 303 oficial define 45 = 29+31+33+35+37+
   39+41+43+44. Las casillas 30/31 (base/cuota de bienes de inversión) se emiten como `0` `editable=True`
   (líneas 206-215) pero **no se incorporan al total**. Caso: pyme compra maquinaria 10.000€+2.100€ IVA, el
   usuario rellena la 31=2.100 en el frontend → si el total 45/46 se recalcula desde este Python (p.ej. al
   regenerar el PDF), la deducción de los 2.100€ se pierde → paga de más. **Severidad media-alta** (solo
   afecta a quien compra bienes de inversión). Verificar PRIMERO si el frontend recalcula 45/46 desde las
   casillas editables o usa el valor del backend; el fix correcto depende de eso (o `total_deducir` incluye
   `cuota_31` editado, o el frontend es la fuente de verdad del total). Toca liquidación → tu decisión.

## Confirmado en código pero CONDICIONAL — None→21% en deducible
4. **`fiscal.py:87` `rate = _d(line.tax_percentage if line.tax_percentage is not None else 21)`** — una
   línea de factura recibida EXENTA (art. 20 LIVA: alquiler vivienda, seguros, sanitario) con
   `tax_percentage = None` se trata como 21% → fabrica IVA soportado ficticio (base 500€ → 105€ inventados
   en casilla 29). `vat_breakdown_by_rate` está centralizada para emitido y recibido; el default 21 es
   defendible en emitido (tipo general español) pero NO en deducible. **Severidad media, CONDICIONAL**:
   solo dispara si la columna `tax_percentage` es nullable y la UI deja exentos a None en vez de 0.
   Verificar nullability + si la UI obliga 0 en exentos. Fix posible: en el lado recibido tratar None como
   0/exento, o NOT NULL con default explícito por el usuario.

## Confirmado estructural — sin deducibilidad parcial (limitación de diseño)
2. **No existe campo `pct_deducible`/`deduction_pct` en `Invoice` (`billing.py`)** — todo el IVA soportado
   se deduce al 100%; no hay forma de expresar afectación parcial: vehículo turismo (art. 95 LIVA: 50% máx),
   suministros de local mixto (art. 95.Tres), atenciones a clientes (art. 96: 0% deducible). Caso: vehículo
   base 20.000€ cuota 4.200€ → deducible 2.100€, el sistema deduce 4.200€. **Riesgo fiscal alto** pero es
   una **limitación de diseño de producto** (requiere migración de esquema + UI + decisión), no un bug
   puntual. Apuntar al roadmap fiscal.

## Revisado — NO es bug (intencional)
- ✅ #3 borradores en deducible: `fiscal.py:48-49` lo documenta como intencional ("las compras nacen
  'draft' y el 303 ya las declara") y `preventive_check` avisa. Decisión de diseño consciente, no defecto.
