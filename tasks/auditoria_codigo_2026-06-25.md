# Auditoría de código — informe consolidado (2026-06-25)

**Alcance:** todo el repo (backend ~75k LOC Python, frontend ~27k LOC TS, desktop Electron).
**Método:** 5 auditores paralelos por dimensión (seguridad backend, correctitud fiscal,
arquitectura/capas, frontend, transversal) + verificación adversarial de los CRITICAL fiscales
contra el código real. **No se tocó código.**

**Relación con auditorías previas:** este informe se apoya en `erp_review_2026-06-24.md`
(síntomas A1–A2 + hallazgos B1–B23) y **no los repite**; aporta hallazgos **nuevos** (prefijo
N para fiscal, SEC para seguridad, ARQ para arquitectura, FE para frontend, X para transversal)
y reverifica algunos B*. Sub-informes completos con archivo:línea y fix en `tasks/audit/`:
`sec-backend-`, `fiscal-nuevo-`, `arquitectura-`, `frontend-`, `cross-cutting-` (todos `-2026-06-25.md`).

---

## Resumen ejecutivo

| Dimensión | CRIT | HIGH | MED | LOW |
|---|---|---|---|---|
| Correctitud fiscal (nuevo) | 2 | 3 | 2 | — |
| Seguridad backend | 0 | 2 | 4 | 3 |
| Arquitectura/capas | — | 3 tipos (34 casos) | 1 tipo (4) | 2 |
| Frontend | — | 1 | 4 | 4 |
| Transversal | 0 | 1 | 5 | 6 |

**Lo que de verdad importa (el miedo de descuadrar a un cliente):** los dos CRITICAL fiscales
(N1, N2) están **verificados en el código** y afectan a modelos AEAT presentables. Son el
trabajo nº1. Lo demás es real pero no te lleva a presentar un 303 incorrecto.

**Lo que está sólido** (verificado, no son problemas): RLS multi-tenant, cadena VeriFactu,
numeración de series (advisory lock + FOR UPDATE, sin race), `func.date()` en el 303,
exclusión de `is_demo` del cálculo fiscal, capa API del frontend (refresh single-flight,
tokens en safeStorage, DOMPurify en todo `dangerouslySetInnerHTML`), `tsc --noEmit` limpio.

---

## 🔴 CRITICAL — corregir antes de que un cliente presente un modelo

> **✅ N1 y N2 RESUELTOS (2026-06-25).** Filtro fiscal unificado: lado emitido incluye
> rectificativas (abono, minoran) y se excluyen las anuladas; los borradores SÍ cuentan
> (las compras nacen 'draft' — excluirlas habría puesto el IVA soportado a cero, por eso NO
> se siguió literalmente el "excluir draft" de la auditoría). El 303 cuadra con el libro
> registro. Helper `_period_invoices_stmt` en `services/reports/fiscal.py` + `_invoices_in_period`
> en `modelos_aeat.py`. Regresión: `tests/test_fiscal_status_rectificativa.py`.

### N1 · El 303/130/347/390 no filtran `Invoice.status` → cuentan borradores y anuladas
**`services/reports/fiscal.py:187+`, `services/reports/modelos_aeat.py`** · *verificado*
El query agrega `invoice_type=="issued"` + `is_demo=False` + rango de fechas, pero **no excluye
`status in ('draft','cancelled')`**. Una factura en borrador o anulada se suma como IVA
repercutido real. Además el libro registro **sí** las excluye → libro y 303 **no cuadran entre sí**.
**Fix:** añadir `Invoice.status.notin_(('draft','cancelled'))` (o `== 'issued'`/`'paid'` según el
ciclo real) a TODOS los builders fiscales, y alinear el criterio con el del libro registro.

### N2 · Las rectificativas quedan fuera del devengo del 303/390 → el cliente ingresa de más
**`services/reports/fiscal.py:189`** · *verificado* · (distinto de B8, que era el dashboard)
El filtro `invoice_type=="issued"` excluye `invoice_type=="rectificativa"`. Las facturas de abono
**no minoran** el IVA repercutido ni la base → se ingresa IVA de más en el modelo presentable.
**Fix:** `Invoice.invoice_type.in_(("issued","rectificativa"))` en el lado emitido del 303/390
(las rectificativas ya llevan importes negados), y reverificar el 347.

---

## 🟠 HIGH

> **✅ N3, N4 y N5 RESUELTOS (2026-06-25).** N3: el asiento de nómina añade la cuota patronal
> 642 (leída de `cuotas_empresa_json`) y la 476 recoge worker+empresa; sigue cuadrando. N4: el
> Modelo 130 (y el snapshot) restan las retenciones IRPF soportadas (suma de `retencion_irpf_amount`
> de emitidas → casilla 06), antes forzadas a 0. N5: el DesgloseIVA del registro VeriFactu resta el
> `discount_percentage` por línea (igual que `compute_invoice_totals`/`vat_breakdown_by_rate`); la
> huella no se ve afectada (usa los totales escalares ya con descuento). Regresión:
> `tests/test_fiscal_n3_n4_n5.py`.

> **✅ SEC1, X1 RESUELTOS y SEC2 ENDURECIDO (2026-06-25).** SEC1: `verify_webhook_secret` es
> fail-CLOSED (sin `TELEGRAM_WEBHOOK_SECRET` rechaza el webhook). X1: el email de reset, en
> producción y sin SMTP, ya no finge el envío ni filtra el token en logs (en dev sí muestra el
> enlace). SEC2: el callback de AutoFirma ya tenía token 128-bit + single-use + rate-limit +
> check `has_signature`; se añade **caducidad de la sesión** (1 h). **Pendiente** (tarea mayor, no
> quick-fix): verificación criptográfica completa del payload firmado (cadena de certificados
> CAdES/PAdES). Regresión: `tests/test_security_hardening.py`.

### Fiscal
- **N3 · Asiento de nómina ignora la cuota patronal de SS (cuenta 642)** pese a tener el dato en
  `cuotas_empresa_json` → coste de personal y resultado (P&G / IS) infravalorados.
- **N4 · Modelo 130 ignora la retención IRPF soportada** — `retenciones_soportadas: 0.0`
  hardcodeado (`services/reports/modelos_aeat.py:53`) → casilla 06 siempre 0, pago fraccionado
  sobreestimado para quien factura con retención. *Verificado.*
- **N5 · El desglose VeriFactu XML no resta `discount_percentage`** → la base declarada en el XML
  diverge de la del 303.

### Seguridad
- **SEC1 · Webhook Telegram fail-open** — `services/integration/messaging.py:58`:
  `verify_webhook_secret` acepta si `TELEGRAM_WEBHOOK_SECRET` está vacío (default) → `/telegram/webhook`
  sin auth, cualquiera dispara el orquestador LLM. **Fix:** rechazar si el secreto no está configurado.
- **SEC2 · Callback AutoFirma público sin auth** — `routes/signing.py:110`: identificado solo por
  `session_token`, sin verificar el payload firmado antes de persistir `signed_hash`. **Fix:** validar
  firma + rate-limit.

### Arquitectura
- **ARQ1 — EN PROGRESO (2026-06-25).** ✅ `email_marketing.py` (#2, ~33 ops) extraído por
  completo a `services/email_marketing/{templates,campaigns,recipients}.py`; las rutas delegan;
  el filtro de destinatarios (antes duplicado 3×) centralizado. Regresión:
  `tests/test_service_email_marketing_campaigns.py`. ✅ `treasury.py` verificado **ya cumplía**
  (delega en `services/treasury/`). 🟡 `marketing.py` (#1, ~56 ops) EN PROGRESO: ✅ extraídos
  `disconnect_account`→`services/marketing/social_accounts.py` y `publish_post_now`/`publish_batch`
  →`services/marketing/publishing.py` (con mocks del cliente Zernio/publisher; regresión en
  `tests/test_service_marketing_extractions.py`). ⏳ Quedan los RIESGOSOS: `generate_plan`
  (orquestación LLM, 165 líneas) y `connect_account` (OAuth/cripto-state) — pase cuidadoso aparte;
  `zernio_callback` se QUEDA en la ruta (RLS público). Routers menores
  (client_portal/portal/calendar/search): revisar caso a caso (muchos son lecturas). Texto original ↓
- **ARQ1 · 24 rutas con lógica de negocio + queries a BD** (189 ops) — peores:
  `routes/marketing.py` (56 ops), `email_marketing.py` (33). Viola la regla "Routes = solo HTTP".
- **ARQ2 — ⚠️ MAYORMENTE SOBREDIMENSIONADO (verificado 2026-06-25).** De los ~9 sitios, casi
  todos son DEFENSIBLES: PDFs en `BackgroundTask` (invoice/payroll/provisioning), jobs del
  scheduler que enumeran tenants con `rls_bypass` (alerts, inventory reorder) y **lecturas** en
  sesión aparte (email/credentials/campaña, sin write atómico). El **único caso real** era
  `hr/commands.generate_document`: recibía el `db` de la request pero abría `AsyncSessionLocal`
  aparte para guardar el HRDocument. ✅ **ARREGLADO**: usa el `db` inyectado (`add→commit→refresh`,
  patrón del resto de comandos). Regresión: `tests/test_service_hr_generate_document.py`. Texto original ↓
- **ARQ2 · 9 services abren su propia `AsyncSessionLocal()`** dentro de un request
  (`services/billing/commands.py:361`, `services/hr/commands.py:188`) → transacciones paralelas a la
  de la request, riesgo de inconsistencia. **Fix:** recibir `db: AsyncSession` por parámetro.
- **ARQ3 · Cálculo de nómina duplicado** `agents/hr/_payroll_calc.py` ↔ `services/hr/_payroll.py`
  → riesgo de descuadre fiscal por divergencia (relacionado con B14/B15).

### Frontend / Transversal
- **FE1 · ~71 `.then()` vs 15 `.catch`** — `useNuevaFactura.tsx:46` carga clientes/productos sin catch
  → formulario de factura con selects vacíos y sin feedback ante fallo de red.
- **X1 · Reset de contraseña fail-open + token en logs** — `auth/email_reset.py:66-72`: sin SMTP,
  loguea el `reset_url` con token en INFO y devuelve `True` como si lo hubiera enviado.

---

## 🟡 MEDIUM (resumen — detalle en sub-informes)

> **✅ N6, N7 RESUELTOS (2026-06-25).** N6: el cuadre de `create_journal_entry` se evalúa en
> Decimal (no float); se mantiene la tolerancia de 1 céntimo a propósito (el redondeo
> independiente de base/IVA/total deja descuadres legítimos de 0,01 €; el cuadre exacto exigiría
> una línea de ajuste 669/769, fuera de alcance). N7: `delete_invoice` ya no borra facturas
> **emitidas** (pending/sent/paid) no-demo — rompería la serie correlativa (RD 1619/2012); se
> anulan con rectificativa. **Cambio de comportamiento**: los borradores, recibidas y demo SÍ se
> siguen borrando. Regresión: `tests/test_billing_commands.py`.

> **✅ M1, M2, M3, M4 RESUELTOS (2026-06-25, sub-informe `sec-backend-`).** M1 (=SEC3): el JWT
> del portal exige que el `ClientPortalToken` siga activo (revocación en BD efectiva) + TTL 7d→24h.
> M2: 3 callbacks OAuth (google/microsoft/marketing) usan `frontend_origin()` como targetOrigin de
> postMessage en vez de `'*'`. M3: `/documents/import-db` rechaza ficheros >50 MB antes de leerlos
> (anti-DoS), sin abortar el lote. M4: el restore de BD ya no devuelve el stderr de psql al cliente
> (se loguea server-side, mensaje genérico). Regresión: `tests/test_security_hardening_medium.py`.

- **N6** Cuadre de asiento con `float` y tolerancia `>0.01` deja pasar descuadres de 1 céntimo.
- **N7** Borrar una factura emitida (sin huella VeriFactu) deja **hueco en la serie**.
- **SEC3** JWT de portal de cliente (7 días) **no revocable**: revocar en BD no invalida los ya emitidos.
- **SEC4–6** (ver `sec-backend-`): detalle de validación/exposición de severidad media.
- **ARQ4** ~~4 tools de agente lanzan excepción en vez de devolver `AgentResult(success=False)`.~~
  **❌ FALSO POSITIVO (verificado 2026-06-25).** inventory/recruitment envuelven cada `_parse_uuid`
  en `try/except ValueError → return "Error: …"`; `shared/db.tool_session` es un guard fail-fast
  (atrapado por los tools); `workers/compiler.compile_dynamic_agent` NO es un tool (compilador del
  grafo, `Raises:` documentado). Las excepciones no llegan al orquestador → no hay cambio que hacer.
- **FE2** `InvoiceTotals.tsx`/`calcLine`: base/IVA/total en float sin redondear por línea (display;
  backend recalcula, mitigado).
- **FE3** `ModelosPanel.tsx:298,464,499`: vistas de 130/303 con `data: any` → un cambio de forma del
  backend rompe en runtime sin que `tsc` avise.
- **X2** 7 clientes `httpx.AsyncClient` persistentes nunca cerrados (`integrations/*.py`): definen
  `aclose()` pero nadie lo llama, sin `lifespan`/shutdown → posible leak de sockets.
- **X3** 117 `except Exception` que devuelven `{e}` crudo sin loguear; en
  `billing/_invoice_create_async.py:183-215` un fallo del asiento contable se traga como warning
  (la factura se crea aunque el asiento falle).

## ⚪ LOW / higiene

- **X4** Drift de deps: `langfuse` importado pero ausente de `requirements.txt` → trazas LLM mudas en
  desktop. `AP_DEVMODE=1` en `.env` es un flag muerto (0 referencias en código).
- Frontend: 4 LOW de type-safety/UX; Seguridad: 3 LOW (headers/CORS). Ver sub-informes.

---

## Plan de ataque sugerido (orden de valor)

1. **N1 + N2** (medio día): un solo cambio de filtro por builder fiscal, con un test de regresión
   que monte borrador+anulada+rectificativa y verifique el cuadre 303↔libro registro. **Esto elimina
   el riesgo de presentar un modelo incorrecto.**
2. **N3, N4, N5** (fiscal restante): completan la exactitud de nómina/130/VeriFactu.
3. **SEC1, SEC2, X1** (seguridad rápida): tres fail-open/sin-auth concretos, fix de pocas líneas.
4. **ARQ2, X3** (robustez): sesiones propias + asientos que se tragan errores — causan inconsistencias
   silenciosas difíciles de diagnosticar luego.
5. El resto (ARQ1 deuda de capas, FE, LOW) es backlog ordinario, no bloquea a un cliente.

> Para aplicar fixes: pídelo y arranco en plan mode por bloque (empezando por N1/N2), con
> `gitnexus_impact` antes de cada edición y test de regresión como exige el flujo del proyecto.
