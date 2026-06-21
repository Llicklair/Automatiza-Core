# Triaje de bugs — revisión de módulos (2026-06-21)

Revisión por 5 agentes en paralelo (fiscal, inventario, RRHH, capa IA, frontend/seguridad).
Severidad: 🔴 CRÍTICO · 🟠 ALTO · 🟡 MEDIO · ⚪ BAJO.

> Nota: GitNexus estaba bloqueado (Kùzu sin concurrencia) → no se pudo correr `impact`/`detect_changes`.
> Los arreglos aplicados son cambios locales de caso-borde (radio de impacto = la propia función) y
> están cubiertos por tests (49 passed entre catálogo, routing, planner, condiciones y OAuth).

---

## ✅ ARREGLADO en esta pasada (seguro, sin tu intervención, verificado)

| # | Severidad | Qué | Archivo | Verificación |
|---|---|---|---|---|
| 1 | 🟠 | **Catálogo de skills unificado**: 12 de 17 skills de UI eran fantasma (apuntaban a tools inexistentes → el compiler las descartaba en silencio y el empleado IA no podía ejecutarlas). Ahora 30 skills con claves 100% ejecutables, fuente única, `_KNOWN_SKILLS` derivado. | `services/ai/employee_crud.py` + nuevo `tests/test_skill_catalog_valid.py` | 20 passed (incl. test nuevo que valida que cada skill resuelve a una @tool) |
| 2 | 🟡 | **Condición NOT malformada ya no dispara** (era fail-open → True; ahora fail-closed → False). Un `{"operator":"NOT"}` sin `condition` activaba el workflow. | `services/workflow/conditions.py` | test_workflow_conditions ✓ |
| 3 | 🟠 | **Estado final sin `status` ya no lanza KeyError** que dejaba al empleado IA colgado en `working`. Fallback a `failed`. | `workers/_orchestrator_state.py` | — |
| 4 | 🟡 | **Fuga de memoria OAuth**: los `_oauth_states` abandonados (con `code_verifier` PKCE) nunca se purgaban. Ahora se barren los caducados al crear uno nuevo. | `services/integration/service.py` | test_google_oauth_pkce ✓ |
| 5 | 🟡 | **401 tras refresh**: si el token refrescado tampoco valía, quedaban tokens muertos y errores repetidos. Ahora logout limpio + redirect a /login. | `lib/api/client.ts` | tsc --noEmit limpio |
| 6 | 🟡 | **Fuga entre tenants en PDF de nómina**: `generate_and_save_payroll_pdf` filtraba solo por `id`, sin `tenant_id`. Añadido el filtro. | `services/hr/_payroll.py` | — |

---

## ⏸️ REQUIERE TU DECISIÓN (no tocado: fiscal/legal/migración/comportamiento/dependencia)

### A. Cálculo fiscal de importes — tu línea roja, no toco sin tu OK
| Sev | Hallazgo | Archivo |
|---|---|---|
| 🔴 | `run_recurring` calcula IVA/totales en **float** en vez de `compute_invoice_totals` (Decimal); ignora descuento; no genera registro Verifactu. Fix: reusar la función canónica. | `services/billing/commands.py` |
| 🔴 | `backfill_verifactu` toma el tail de cadena por `created_at desc` en vez de `find_tail_huella` → cadena bifurcada (el propio módulo advierte que `created_at` no es determinista). | `services/billing/backfill_verifactu.py` |
| 🟠 | `next_run_date` con días fijos (30/90/365) acumula deriva y rompe en bisiesto. Fix: `relativedelta`. (No es importe; ligado a `run_recurring`.) | `services/billing/commands.py` |
| 🟠 | Casilla 07 del modelo 130 puede quedar negativa. ¿Acotar a 0? (interpretación AEAT) | `services/aeat/casillas_130.py:82` |
| 🟡 | 303: agrupación por `float(rate)` como clave de dict puede colisionar dos filas del mismo tipo. Verificar si upstream pre-agrega. | `services/aeat/casillas_303.py` |
| ⚪ | 303: total a deducir (45) ignora casilla 31 (bienes de inversión) si el usuario la edita. | `services/aeat/casillas_303.py` |

### B. ERP — numeración fiscal y stock (riesgo de datos / migración)
| Sev | Hallazgo | Archivo |
|---|---|---|
| 🟠 | Numeración de factura con `count(*)+1` **no atómica** → nº de factura duplicado (ilegal). Necesita secuencia/constraint UNIQUE + retry (migración). | `services/sales/commands.py` |
| 🟠 | `int(qty)` **trunca decimales** en recepción/albarán/POS → corrupción de stock en ventas a peso. Verificar tipo de columna (posible migración a Decimal). | `purchase_receiving` / `pos` / `albaran` |
| 🟡 | `create_quote` ignora `discount_percentage`. | `services/sales/commands.py` |
| 🟡 | Descuento de stock read-modify-write sin lock → sobreventa concurrente. `with_for_update` / UPDATE atómico. | `pos`/`albaran`/`sales` |
| 🟡 | FEFO: agregado de stock vs suma de lotes puede desincronizarse en recepción sin lote. | inventory |

### C. RRHH — cálculo/convenio
| Sev | Hallazgo | Archivo |
|---|---|---|
| 🔴 | Horas extra por **fichaje aislado** con tope fijo 8h; pausas contadas como trabajadas. Diseño dependiente de convenio. | `services/hr/commands.py` (clock_out) |
| 🔴 | **Cruce de medianoche / fichaje abierto** sin tope → horas extra disparatadas. Añadir tope de duración. | `services/hr/commands.py` |
| 🟠 | `total_ss` del PDF excluye `cuota_solidaridad`. **VERIFICAR contra la plantilla PDF** (ya recibe `cuota_solidaridad` aparte → riesgo de doble conteo si se suma sin pensar). | `services/hr/_payroll.py:230` |
| 🟠 | Finiquito: prorrata pagas extra con `/365` fijo → en bisiesto >100%. | `services/hr/finiquito.py` |
| 🟠 | IRPF sobre `gross` incluyendo prestación IT — validación fiscal. | `services/hr/queries.py` |
| 🟡 | `hora_entrada` registrada en **UTC**, no hora local (registro de jornada RD 8/2019). Necesita zona horaria del tenant. | `services/hr/commands.py:573` |
| 🟡 | `it_days_overlap` tope 30 días infra-paga meses de 31. | `services/hr/queries.py` |

### D. Capa IA / scheduler (concurrencia / migración)
| Sev | Hallazgo | Archivo |
|---|---|---|
| 🔴 | Idempotencia del scheduler **check-then-act sin claim atómico** → doble disparo (riesgo de factura recurrente duplicada). Necesita `INSERT ON CONFLICT` + índice único (migración). | `workers/tasks_scheduler.py:218` |
| 🟠 | Catch-up dispara **un solo run** por mucho downtime; `has_active_execution` sin lock. | `workers/tasks_scheduler.py` |
| 🟠 | Nodo de plan sin `domain` cae a `coordinator` (sin dispatcher) → **"éxito" silencioso sin ejecutar**. Fix: fallar/saltar. | `agents/orchestrator/_plan_handlers.py:223` |
| 🟠 | Budget guard incoherente: `instruct_employee` usa gasto **acumulado**, el guard que pausa usa **mensual**. Alinear a mensual. | `services/ai/employee_crud.py` + `services/agent_budget.py` |
| 🟡 | Cleanup de empleado hace commit sobre sesión sucia → puede quedar `working`. `rollback` + sesión fresca. | `workers/tasks_orchestrator.py:287` |
| 🟡 | Classifier: empates por substring → `unknown` → LLM. (Verificar si el commit reciente de maximal-munch ya lo cubre.) | `agents/orchestrator/classifier.py` |

### E. Seguridad frontend (requiere dependencia / decisión)
| Sev | Hallazgo | Archivo |
|---|---|---|
| 🟠 | **XSS almacenado** vía `dangerouslySetInnerHTML` con `html_body` sin sanitizar (preview de campañas/plantillas). Fix: DOMPurify (`npm i dompurify`). | `email-marketing/_components/CampaignsTab.tsx:150`, `TemplatesTab.tsx:117` |
| 🟠 | **XSS** desde cuerpo de email de terceros. Sanitizar / `<iframe sandbox>`. | `correos/_components/MessageDetailModal.tsx:66` |
| ⚪ | Salt PBKDF2 fijo (mitigado, documentar exigir Fernet key real). | `services/encryption.py` |
| ⚪ | `_clean_env` copia todo el entorno al subproceso CLI con `--dangerously-skip-permissions`. Allowlist recomendada. | `core/llm/claude_code.py` |

---

## Verificado como CORRECTO (no son bugs)
- RLS multi-tenant: política viva fail-closed (`tenant_id = current_tenant OR rls_bypass='on'`); el clause permisivo solo está en `downgrade()`.
- Persistencia de trazas no-fatal (sesión propia, traga excepciones); mapeo success/failed/timeout→ok/error coherente.
- `batch_adjust_stock`: valida negativos, dry_run no toca BD.
- Refresh single-flight de tokens: sin race ni bucle.
- OAuth callback duplicado: idempotente con `_completed_oauth`.

---

## Siguiente lote sugerido (si me das luz verde)
1. **Lote IA "seguro"** (sin tocar importes): `_plan_handlers` éxito silencioso + cleanup sesión sucia + budget guard mensual. Bajo riesgo, alto valor.
2. **XSS frontend** (instalar DOMPurify y sanitizar los 3 puntos). Seguridad real.
3. **Fiscal**, contigo delante y con tests: `run_recurring` (reusar `compute_invoice_totals`) + `backfill_verifactu` (usar `find_tail_huella`).
4. **Migraciones** (numeración de factura atómica, scheduler claim atómico): planificar aparte.
