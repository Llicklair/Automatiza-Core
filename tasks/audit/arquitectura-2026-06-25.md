# Auditoría de Arquitectura — Backend (FastAPI + LangGraph)

Fecha: 2026-06-25 · Auditor: staff engineer (revisión de capas, sin modificar código)
Reglas: `CLAUDE.md` §Architecture Rules + `ARCHITECTURE.md`

## Resumen de violaciones por tipo y severidad

| # | Regla | Casos | Severidad |
|---|-------|-------|-----------|
| R1 | Routes con lógica de negocio / queries a BD | 24 ficheros de ruta con `db.execute/add/commit/select` (189 ocurrencias). Top: `marketing.py` 56, `email_marketing.py` 33, `client_portal.py` 19, `portal.py` 12, `calendar.py` 12, `search.py` 9 | HIGH |
| R2 | Domain services que crean su propia sesión (`AsyncSessionLocal`) | 5 domain services reales (excluida infra): `ai/employee_provisioning.py`, `alerts/service.py`, `billing/commands.py`, `email/sender.py`+`email/credentials.py`, `hr/_payroll.py`+`hr/commands.py`, `inventory/reorder_service.py`, `email_marketing/sender.py` | HIGH |
| R3 | Agents importan otros agents | 0 reales. Las aristas son imports a `agent_tools`/`shared` (infra permitida) o intra-dominio (`hr/tools`→`hr/_employee_tools`, `banking/tools`→`banking/_*`), que es legítimo | — |
| R4 | Agents lanzan excepciones al orchestrator | 4 reales: `inventory/tools.py:33`, `recruitment/tools.py:26`, `workers/compiler.py:48`, `shared/db.py:42` (raise ValueError dentro de tool en vez de devolver AgentResult/string de error) | MEDIUM |
| R5 | Lógica duplicada agente↔servicio (nómina/asientos/conciliación) | 1 nuevo confirmado: cálculo+persistencia de nómina duplicado en `agents/hr/_payroll_calc.py` y `services/hr/_payroll.py` | HIGH |
| R6 | Models con lógica de negocio | 0 reales (`db/models/common.py:24 utcnow` es helper de timestamp, aceptable) | LOW |
| R7 | Frontend con `fetch()` directo (no `lib/api/*`) | 0 en componentes. Único: `lib/error-reporter.ts:35` (es infra de telemetría, fuera de UI) | LOW |

Total cruces de capa relevantes: **~33** (24 rutas R1 + 9 services R2) + 4 tools (R4) + 1 duplicación (R5).

## Detalle de hallazgos

### R1 — Routes con lógica de negocio (HIGH)
La regla manda: rutas validan input y devuelven HTTP, CERO lógica. Hay 24 ficheros que ejecutan queries y orquestan persistencia inline.

- `marketing.py` (56 ops): `_pick_config`, `_resolve_profile_id`, `zernio_callback` hacen select/add/commit + reglas de negocio (resolución de perfil, upsert de cuenta) en la ruta. Fix: mover a `services/marketing/` (ya existe el paquete; la ruta solo importa funciones sueltas).
- `email_marketing.py` (33 ops): `create_campaign` calcula recipients, crea campaign + N `EmailCampaignRecipient` en bucle, commit — lógica de negocio pura en la ruta. Fix: `services/email_marketing/` solo tiene `sender.py`; crear `campaigns.py` y delegar.
- `client_portal.py:19`, `portal.py:12`, `calendar.py:12`, `search.py:9`, `treasury.py:5` (con `Decimal`, `db.commit`, construcción de remesas): misma clase. Fix: extraer a service del dominio.
- `treasury.py:154/275` instancia `Decimal` y arma órdenes de remesa SEPA dentro de la ruta. Fix: `services/treasury/`.

### R2 — Domain services con sesión propia (HIGH)
`ARCHITECTURE.md §7`: la sesión se inyecta, nunca se crea dentro. Estos abren `AsyncSessionLocal()` (transacción paralela, rompe atomicidad del request):
- `services/billing/commands.py:361-383`
- `services/hr/_payroll.py:281`, `services/hr/commands.py:188`
- `services/ai/employee_provisioning.py:183-284`
- `services/alerts/service.py:44`, `services/email/sender.py:32-67`, `services/email/credentials.py`, `services/email_marketing/sender.py:35`, `services/inventory/reorder_service.py`
- Nota: muchos son invocados desde scheduler/worker (sin request) — ahí es defendible, pero `billing/commands.py` y `hr/commands.py` se llaman también desde agente/ruta → riesgo de doble transacción. Fix: aceptar `db` opcional inyectado; abrir sesión propia solo en path de scheduler.

### R4 — Tools que lanzan en vez de devolver AgentResult (MEDIUM)
`inventory/tools.py:33`, `recruitment/tools.py:26` (`raise ValueError` en validación de id), `workers/compiler.py:48`. La excepción sube al grafo del agente. Fix: devolver string/`AgentResult(success=False)`.

### R5 — Nómina duplicada agente↔servicio (HIGH)
`agents/hr/_payroll_calc.py` (`_create_payroll_async`, `_generate_all_payrolls_async`) reimplementa el mismo flujo que `services/hr/_payroll.py` (`create_payroll_auto`): resuelve `irpf_rate`, llama `calc_payroll_for_employee`, arma el `Payroll` con idénticos campos (`base_cotizacion_cc`, `base_irpf`, `pct_irpf`, `irpf`) y persiste. Dos copias = divergencia fiscal garantizada. Fix: el tool del agente debe llamar a `services/hr/_payroll.create_payroll_auto(...)`.

## Las 3 peores
1. **R1 `marketing.py` / `email_marketing.py`** — 56 y 33 ops de BD + reglas de negocio en la ruta; capa Routes saltada por completo.
2. **R5 nómina duplicada** — `agents/hr/_payroll_calc.py` vs `services/hr/_payroll.py`: cálculo fiscal en dos sitios, riesgo de descuadre al cliente.
3. **R2 `billing/commands.py` / `hr/commands.py`** — abren `AsyncSessionLocal()` propia aun siendo llamados dentro de request → transacciones paralelas.
