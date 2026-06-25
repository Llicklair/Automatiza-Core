# Inbox /forja v2 — tesorería / banking (2026-06-25, lente idempotencia/correctitud)

El #2 (unreconcile sin tenant) ya arreglado → PR #52. Estos quedan (tocan dinero/contable):

## ⚠️ ALTA — doble asiento contable
1. **`banking/service.py:182-193` `reconcile_transaction` sin guard de idempotencia** — doble clic /
   reintento de red puede conciliar dos veces y generar un **2º asiento contable de cobro** para la
   misma factura (no hay `UNIQUE(tenant_id, invoice_id)` en `BankTransaction`; la 2ª pasada cae en el
   `pass` de `can_transition` y re-llama `_apply_payment_entry`). Fix: (a) guard al inicio
   `if tx.status == "reconciled": return <ya conciliado>`, y/o (b) UPDATE condicional `WHERE status != 'reconciled'`,
   y/o (c) `UNIQUE` en BankTransaction (migración). Toca contabilidad → tu diseño.

## Media — conciliación equivocada
3. **`banking/service.py:460-461` `auto_reconcile` casa candidato único por SOLO importe (score 50)** —
   si hay una sola factura pendiente de ese importe pero es de OTRO cliente (p.ej. cuota recurrente 99€),
   se concilia mal y se marca pagada la factura equivocada. Fix: exigir score mínimo (≥60: importe +
   fecha/cliente/nº) para auto-casar el candidato único. Cambia semántica de matching → tu criterio.

## Baja — proyección de liquidez
4. **`treasury/projection.py:100-107` saldo de fallback suma TODAS las cuentas del tenant** (sin filtrar
   `account_id`) → si hay 2 cuentas (corriente+ahorro) la proyección parte de un saldo inflado. Además usa
   `datetime.utcnow()` (deprecado 3.12+). Fix: filtrar por cuenta + `datetime.now(timezone.utc)`.
