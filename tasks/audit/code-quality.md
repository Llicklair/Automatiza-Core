# Code Quality Audit — Automatiza-pyme-main

Branch: `chore/cleanup-stale-reports` (confirmed). Scope: `backend/` (Python ~73k LOC) + `frontend/src` (TS/TSX).
Method: greps/wc run in context-mode sandbox; counts below exclude `.venv`, `node_modules`, `__pycache__`.

---

## 1. Dead code

**`tasks/cleanup-candidates.md` claims verified — they hold up.** The report's headline conclusion is **TRULY_DEAD = 0** for TIER 1 (78 "ALTA" private `_*` helpers), and the methodology (2nd pass over 1617 files via `os.walk`, checking string-dispatch, cross-module refs, library callbacks, Alembic, autouse fixtures) is sound. Spot-checks confirm:
- The 16 `_dispatch_*` flagged are alive — registered in `agents/orchestrator/dispatchers/__init__.py` → `DISPATCHER_MAP`. The graph simply lost the CALLS edges.
- 3 zero-reference test helpers are `@pytest.fixture(autouse=True)` → injected by collection, not dead.

**Already applied (per report's exec-state table, 2026-06-17):** ruff `F401` removed 20 unused imports in 13 test files; `lib/api.ts` dropped `StockMovementResult`; `components/` removed `NodeStatusBadge.tsx`, `Skeletons.tsx`, `API_URL`, `authHeaders`, `GenerativeUI`; 455 KB local cruft (`pytest-of-Marcos/`, `backend/scripts/_runs/`) deleted. `tsc --noEmit` exit 0 after each.

**Outstanding / additional findings:**
- **GitNexus index is stale** (TIER 4) — references files already deleted. Run `npx gitnexus analyze`.
- **No commented-out code blocks** of significance surfaced; codebase is clean here.
- **`lib/api.ts` type bloat**: ts-prune flagged ~68 unused exported `type`/`interface` (e.g. `AnalyticsRRHH`, `QuoteLine`, `InvoiceSuggestion`, `DeliveryNote`, `LlmProviderEntry`). Type-only, low-risk to prune but needs per-type `tsc` verification (ts-prune misses re-exports/JSDoc).

---

## 2. TODO / FIXME / HACK / XXX markers

After stripping Spanish-language "todo/todos" false positives (the bulk of raw grep hits were prose, not markers), only **3 real code markers** exist — the codebase is remarkably marker-free:

| File:line | Marker | Note |
|---|---|---|
| `backend/app/services/reports/modelos_aeat.py:228` | TODO | **Correctness/fiscal**: retenciones IRPF profesionales (Art. 95 LIRPF, 15%) need `Invoice.retencion_irpf` field absent from schema; deferred to v1.1. Worth tracking — affects fiscal accuracy. |
| `backend/app/services/i18n/tenant_locale.py:37` | TODO | Follow-up: `tenants.locale` column or `tenant_preferences` table. Minor. |
| `backend/app/agents/billing/_invoice_query_tools.py:143` | "XXX" | False positive — it is `"IA-XXX"` placeholder text in a docstring, not a marker. |

No FIXME/HACK markers anywhere. No security-flagged TODOs.

---

## 3. God files / complexity (Python > 600 LOC, top 15)

| LOC | File | Notes |
|---|---|---|
| 1466 | `db/migrations/versions/0001_initial_squashed.py` | Squashed migration — expected, don't touch |
| 1410 | `scripts/full_system_test.py` | Test script |
| 1129 | `tests/test_prompt_e2e.py` | Test |
| **1048** | `services/reports/modelos_aeat.py` | **God file** — 17 funcs, fiscal model logic; split candidate |
| **865** | `api/v1/routes/marketing.py` | **Route file too big** — 26 defs; likely business logic leaking into routes (see §4) |
| **841** | `services/hr/queries.py` | 29 funcs |
| **833** | `services/sales/commands.py` | 25 funcs |
| **783** | `services/hr/commands.py` | |
| **727** | `services/analytics/dashboard.py` | |
| **698** | `api/v1/routes/documents.py` | Large route |
| **689** | `services/billing/commands.py` | |
| 640 | `core/llm/claude_code.py` | LLM adapter |
| 631 | `services/pdf_reports/_fiscal_report.py` | |
| 630 | `workers/tasks_scheduler.py` | |
| 614 | `services/banking/service.py` | |

Top split candidates by business value: `modelos_aeat.py` (1048), `marketing.py` route (865 — architecture smell), `hr/queries.py` (841).

---

## 4. Error handling — swallowed exceptions

**~80 `except Exception:` sites in `backend/app`.** Highest concentration (counts):

| Count | File | Risk |
|---|---|---|
| 8 | `core/observability.py` | Likely intentional (telemetry must never break app) — but verify each logs |
| 8 | `core/license.py` | **Concern** — licensing failures silently swallowed could mask enforcement bugs |
| 7 | `services/email/service.py` | Email send failures |
| 5 | `services/integration/service.py` | |
| 4 | `workers/_orchestrator_context.py`, `services/idempotency.py`, `services/hr/commands.py`, `agents/orchestrator/_plan_handlers.py` | |

**`except: pass` / narrow-then-pass blocks** (15 sites) — mostly *defensible* narrow catches (`ImportError`, `asyncio.CancelledError`, `ProcessLookupError`, `OSError`, `(ValueError, IndexError)`). One broad `except Exception:` swallow at `db/migrations/env.py:13` (migration tooling — acceptable).

**22 files use `except Exception` but import no logger** — silent swallow risk. Worst for correctness: `services/migration/bulk_import.py`, `services/migration/wizard.py`, `services/treasury/sepa.py`, `services/tenant/certificates.py`, `services/signing/autofirma.py`, `api/v1/routes/marketing.py`, `api/v1/routes/signing.py`. These touch money/legal flows — exceptions should at minimum be logged.

No bare `except:` (colon) anywhere — good.

---

## 5. Async correctness

**Clean.** No synchronous blocking calls found in `backend/app`:
- Zero `import requests` / `requests.get/post`.
- Zero `time.sleep(`.
- Zero `httpx.Client(` / `requests.Session` (sync clients).

All file reads in async routes use `await file.read()` (FastAPI `UploadFile`) correctly. The sync `f.read()` hits are in non-async helper contexts (`services/email/sender.py`, `agents/documents/tools.py`, `services/hr/queries.py:352` reading a logo for base64) — local file reads, low blocking impact but could move to `anyio.to_thread` if on hot path. No missing-await smells surfaced.

---

## 6. Duplication

**aeat/casillas_* — already refactored, low debt.** `services/aeat/_casilla.py` is the shared home (`Casilla` dataclass + `round2()`), consumed by the newer `casillas_NNN.py` builders (111, 115, 200, 347, 390…). Only `casillas_303.py` (219 LOC) and `casillas_130.py` (121) keep their own dataclasses "por motivos históricos" — a deliberate, documented exception, not copy-paste rot. Total `aeat/` = 2939 LOC across 20+ small focused files. **No action needed.**

**PDF modules — two parallel trees, possible overlap.** `services/pdf/` (transactional docs: invoices, payroll, albaranes) and `services/pdf_reports/` (fiscal/analytical reports). Both reimplement layout helpers (`pdf_base.py` 479 LOC vs `_aeat_layout.py`, `_fiscal_report.py` 631, `_structured.py` 548). Candidate for a shared base, but the split is domain-justified; review `pdf_base.py` vs `_aeat_layout.py` for genuine overlap before merging.

---

## 7. Type safety

- **TS `any`: 261 occurrences** in `frontend/src` (`: any`, `as any`, `any[]`, `<any>`). High — the main TS debt. Worth a focused sweep, especially in `lib/api/*.ts` where response shapes should be typed.
- **`@ts-ignore` / `@ts-expect-error` / `@ts-nocheck`: 0** — excellent, no suppression.
- **`eslint-disable`: 35 files** — moderate; audit which rules are being silenced.
- Python public-API type hints: spot-checks show good coverage (`-> str`, `-> Decimal`, dataclasses); no systematic gap found.

---

## 8. Config / magic numbers / print()

- **`print()` in `backend/app` (non-script/test): 0** — all runtime code uses logging. Clean.
- **`print()` in `backend/scripts/`: 25 files** — acceptable (CLI scripts, intended stdout).
- Magic numbers: fiscal percentages (15% IRPF, IVA rates) appear inline in `modelos_aeat.py` / casillas — these are legally-fixed constants; documented with BOE references in docstrings, so low risk, but centralizing in a `fiscal_constants.py` would aid maintainability when rates change.

---

## Priority recommendations

1. **Add logging to the 22 logger-less `except Exception` files** — prioritize money/legal flows (`migration/bulk_import`, `treasury/sepa`, `tenant/certificates`, `signing/autofirma`, `license.py`). Highest correctness ROI.
2. **TS `any` sweep (261)** — start with `lib/api/*.ts` response types.
3. **Refresh GitNexus index** (`npx gitnexus analyze`) — currently stale, points at deleted files.
4. **Split god files**: `modelos_aeat.py` (1048), `marketing.py` route (865 — move business logic to a service per ARCHITECTURE.md), `hr/queries.py` (841).
5. **Track the fiscal TODO** (`modelos_aeat.py:228`, IRPF retención schema gap) — correctness-relevant for v1.1.
