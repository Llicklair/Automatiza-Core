# Inbox /forja v2 — flujo emisión + cadena VeriFactu (2026-06-25)

Barrido por flujo (GitNexus) sobre `services/billing/verifactu_chain.py` + registro. Todo fiscal →
revisión humana (no auto-fix). El #1 era falso positivo (verificado con test → PR #52).

## Descartado (falso positivo, ya verificado)
- ❌ `verifactu_chain.py:231` "`db.bind` es None → advisory lock muerto": FALSO. En SA 2.0.51 `bind`
  está poblado; el `pg_advisory_xact_lock` SÍ se adquiere. PR #52 deja 3 tests-guard del contrato.

## Para revisar (reales, fiscal)
1. **⚠️ Anulaciones no se persisten en la cadena** [media-alta, legal] — `registro_facturacion.py:310`
   (lo reconoce un comentario del propio código: "la anulación no se persiste como VerifactuRecord
   todavía"). El siguiente alta encadena sobre el último alta, saltándose la anulación → posible HUECO
   en la cadena vs RD 1007/2023 Art. 8. Fix: persistir `RegistroAnulacion` en `verifactu_chain` y ajustar
   `find_tail_huella`. Confirmar contra el WSDL de preproducción. **Lo más serio de este barrido.**

2. **TOCTOU idempotencia antes del lock** [media] — `verifactu_chain.py:224-236`: el SELECT de
   idempotencia (¿ya existe registro para este invoice?) ocurre ANTES del `pg_advisory_xact_lock`. Dos
   sesiones concurrentes pueden pasar ambas el check; el `UNIQUE(invoice_id)` lo captura como
   IntegrityError (rollback de la factura). Fix objetivo: mover el bloque de idempotencia a DESPUÉS del
   lock (línea ~236). Bajo riesgo pero toca contrato transaccional → revisión humana.

4. **Estados de envío AEAT no diferenciados / `verifactu_status` nunca se escribe** [media, cuando se active]
   — `verifactu_submit.py:217`: un rechazo de negocio (HTTP 4xx: NIF no dado de alta, serie no
   registrada, XML inválido) y un error transitorio (5xx/timeout) lanzan el MISMO `VerifactuSubmitError`;
   y el campo `Invoice.verifactu_status` (`billing.py:91`) existe pero NUNCA se escribe tras el envío.
   Hoy no está wired a producción (modo voluntario off). Al activarlo: un 4xx permanente se reintentaría
   en bucle indistinguible de un transitorio. Fix (decisión humana): definir estados (`aceptado`/
   `rechazado_permanente`/`error_transitorio`/`pendiente`) y escribirlos por rama en el submitter.

3. **Redondeo divergente** [baja] — `_fmt_importe` (`verifactu_chain.py:30`, HALF_EVEN del contexto
   Decimal) vs `_round2` (`queries.py:41`, HALF_UP) + el path `float→Decimal` del `importe_total`.
   Caso: `float(33.335)`→`Decimal("33.3349…")`→`"33.33"` vs `_round2`→`"33.34"`. Hoy payload y XML son
   consistentes entre sí, pero el importe encadenado puede no coincidir con `amount_total`. Verificar
   con un test del valor frontera antes de tocar (es importe en cadena fiscal).
