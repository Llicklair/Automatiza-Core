# Architecture Compliance Audit

Audited against `ARCHITECTURE.md` + `CLAUDE.md`. Backend: `backend/app`. Frontend: `frontend/src`.
Date: 2026-06-19.

---

## Summary scorecard

| Rule | Status | Severity |
|------|--------|----------|
| 1. Routes: no business logic | PARTIAL — several routes hold queries + logic | MEDIUM |
| 2. Services receive `db` param (not global) | PARTIAL — domain services open own sessions | MEDIUM |
| 3. Agents isolation / structure / AgentResult | PASS (minor) | LOW |
| 4. Frontend: no direct fetch in components | PASS | — |
| 5. Layering: models w/ logic, god files | PARTIAL — god files exist; models clean | MEDIUM |
| 6. Naming orchestrator vs coordinator | PASS (documented debt) | LOW |

---

## Rule 1 — Routes must validate + return HTTP only (ZERO business logic)

Routes are expected to delegate to services/agents. Most route files only import `User`
(auth dependency — legitimate). But several embed real query + branching/aggregation logic
inline instead of delegating to a service.

**Violations (file:line — evidence — fix):**

- `backend/app/api/v1/routes/marketing.py:600-680` — **MEDIUM**. The POST handler runs
  `run_agent`, then a "deterministic fallback" that itself queries `Product`, `SocialAccount`,
  calls `evaluate_autonomy`, and builds a marketing plan inline (16 `select(` in the file, 40
  `db.execute/add/commit` calls). This is business logic (orchestration + autonomy gating +
  plan generation) living in a route.
  *Fix:* move the fallback-plan generation into `services/marketing/` (e.g.
  `generate_fallback_plan(db, tenant_id)`); route should only call agent + service and map to HTTP.

- `backend/app/api/v1/routes/calendar.py:22-115` — **MEDIUM**. `unified_calendar` issues 4
  separate `select(Event/Reservation/Invoice/Payroll)` queries and merges/derives display items
  (overdue calc `inv.due_date < now`, color logic, subtitle formatting) inline. This is a
  cross-domain aggregation = business logic.
  *Fix:* extract to `services/calendar/unified.py: build_unified_calendar(db, tenant_id) -> list[dict]`.

- `backend/app/api/v1/routes/client_portal.py:40-220` — **LOW/MEDIUM**. 7 `select(` + 2
  `commit()`. Token issue/revoke/auth and portal payload assembly (invoices+quotes) done inline.
  Token lifecycle is reusable business logic.
  *Fix:* `services/portal/client_tokens.py` for issue/revoke/authenticate; route stays thin.

- `backend/app/api/v1/routes/portal.py:32-220` — **LOW/MEDIUM**. 5 `select(`; private helpers
  `_get_my_employee`, `_get_active_attendance`, `_build_portal_payload` (HR queries + payload
  build) live in the route module. These belong in `services/hr/` or `services/portal/`.

- `backend/app/api/v1/routes/email_marketing.py` — **LOW/MEDIUM**. 10 `select(` against
  `EmailCampaign/Recipient/Template/Client`. Verify CRUD is delegated, not inline.

- `backend/app/api/v1/routes/tenant.py` (5), `search.py` (3) — review; likely thin but flagged
  by query density.

*Note:* `from app.db.models... import User` in ~40 routes is NOT a violation — it's the typed
auth dependency. ORM-model imports for actual querying (calendar, client_portal, marketing,
email_marketing) are the real layering smell.

---

## Rule 2 — Services receive `db: AsyncSession` as a param (no global session)

ARCHITECTURE.md §1.1 explicitly allows **infra services** (cache, scheduler, idempotency,
ws_relay) to NOT receive `db`. Those uses of `AsyncSessionLocal()` are legitimate.

**Legit (infra / background, allowed):** `services/idempotency.py:85/105/121`,
`services/alerts/service.py:36`, `services/autonomy_gate.py:243`, `services/banking/psd2.py:22`.

**Questionable — DOMAIN services opening their own session (MEDIUM):**

- `backend/app/services/billing/commands.py:361-383` — opens `AsyncSessionLocal()` inside a
  command. Billing is a **domain service** that should receive the request `db`. Opening a new
  session breaks the "one transaction per request" invariant (§7).
- `backend/app/services/hr/commands.py:188-190` — same pattern (`save_db`).
- `backend/app/services/hr/_payroll.py:281` — domain payroll logic opening its own session.
- `backend/app/services/ai/employee_provisioning.py:221/284` — borderline (provisioning may be
  background; confirm lifecycle).

*Fix:* thread the caller's `db` through these functions. If the work is genuinely a detached
background job, document it as such (like idempotency) so the exception is explicit.

---

## Rule 3 — Agents: isolation, structure, AgentResult

**PASS overall.** No domain agent imports another domain agent. All `from app.agents.<x>._*`
imports are intra-domain (banking→banking, hr→hr, orchestrator→orchestrator) which is allowed.
`__init__.py` exports are clean: domains export `graph` (+ their `@tool`s); documented
exceptions `email` (`run_email_agent`), `workflow` (`run_workflow_agent`), `marketing`
(`graph, run_agent`) match ARCHITECTURE.md §2 exactly.

**Minor (LOW):**
- `backend/app/agents/inventory/tools.py:33,39` and `recruitment/tools.py:26` —
  `raise ValueError(...)` inside tools. ARCHITECTURE.md forbids throwing to the orchestrator
  (use `AgentResult(success=False)`). These are input-validation raises inside `@tool` bodies;
  acceptable IF the graph node catches them, but they technically violate the "never throw"
  rule. Verify the dispatcher wraps them. `orchestrator/_plan_handlers.py:366` raises inside the
  coordinator (acceptable — it's the coordinator, not a domain tool).
- No `except Exception: pass` found in agents/services — good.

---

## Rule 4 — Frontend: no direct `fetch()` in components

**PASS.** Only `fetch(` occurrence outside `lib/api/` is `frontend/src/lib/error-reporter.ts:35`
(an infra reporter, not a component). Zero `fetch(` in `app/` or `components/`. Components route
through `lib/api/*`. Compliant.

---

## Rule 5 — Layering: models with business logic, god files

**Models:** clean — no calc/compute/process/send methods found in `db/models/`. PASS.

**God files (>500 LOC; >800 = hard violation):**
- `services/reports/modelos_aeat.py` — **1048 LOC** (excl. the 1466-line squashed migration,
  which is generated and exempt). **MEDIUM** — split per modelo.
- `api/v1/routes/marketing.py` — **865 LOC**. **MEDIUM** — oversized route, compounded by Rule 1
  inline logic. Split + extract service.
- `services/hr/queries.py` (841), `services/sales/commands.py` (833), `services/hr/commands.py`
  (783), `services/analytics/dashboard.py` (727), `api/v1/routes/documents.py` (698),
  `services/billing/commands.py` (689) — LOW/MEDIUM; large but in correct layer. Candidates for
  cohesion-driven splits.

---

## Rule 6 — Naming orchestrator vs coordinator

**PASS (documented debt).** `agents/orchestrator/` = the Coordinador; `services/workflow/` = the
Orquestador. Matches ARCHITECTURE.md §0. The directory-name mismatch is acknowledged tech debt
(200+ usages), not a new violation.

---

## Cross-cutting: module count vs cohesion, duplication, dead code

- **65 route files** for 14 agent domains → high route fragmentation (hr split into
  hr/hr_documents/hr_employees/hr_expenses/hr_payrolls/hr_time = 6 files). Cohesive but verify
  shared HR logic isn't duplicated across them.
- **Duplication risk:** `email/sender.py` and `email_marketing/sender.py` both open sessions and
  send — check for shared send primitive.
- **Dead code:** not exhaustively scanned; recommend `vulture`/`ruff --select F401` pass.

---

## Top priorities (fix order)

1. Extract inline business logic from `marketing.py` (600-680) and `calendar.py` (22-115) into
   services. (Rule 1, MEDIUM)
2. Thread request `db` into `billing/commands.py` + `hr/commands.py` instead of
   `AsyncSessionLocal()`. (Rule 2, MEDIUM)
3. Split `services/reports/modelos_aeat.py` (1048 LOC) and `routes/marketing.py` (865 LOC).
   (Rule 5, MEDIUM)
4. Convert tool-level `raise ValueError` to `AgentResult(success=False)` or confirm node-level
   catch. (Rule 3, LOW)
