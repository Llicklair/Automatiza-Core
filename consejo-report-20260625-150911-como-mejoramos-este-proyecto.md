# Consejo de los 7 Sabios — Reporte

**Atasco (ES):** ¿Cómo mejoramos este proyecto?
**Rondas usadas:** 3
**Unánime:** sí

## Resumen ejecutivo

Consenso unánime alcanzado en 3 ronda(s) (21 turnos).

## Plan priorizado

| # | Tarea | Sabios | Discrepó (resuelto) | Blast | Verif. | Auto |
|---|-------|--------|---------------------|-------|--------|------|
| 1 | **PSD2 demo-vs-real visible indicator** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | guardian | `MEDIUM` | — | ⛔ |
| 2 | **Tenant-level LLM cost circuit breaker — hourly hard cap** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ✅ medido | ⛔ |
| 5 | **Extract withAuthRetry interceptor in client.ts** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `MEDIUM` | ⚠️ parcial | ⛔ |
| 6 | **Explicit scope-out: backend/app/api route layer is clean — no items this iteration** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ✅ medido | ⛔ |
| 7 | **Add pool_recycle and pool_timeout to async engine configuration** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ⚠️ parcial | ⛔ |
| 9 | **Explicit scope-out: frontend/src/components — no structural debt this iteration** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ✅ medido | ⛔ |
| 10 | **Explicit scope-out: backend/scripts — operational scripts are demo/CI utilities, not architectural debt** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ✅ medido | ⛔ |
| 11 | **Explicit scope-out: tasks/ — reconcile todo.md with plan decisions post-execution** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ⚠️ parcial | ⛔ |

_Columna **Discrepó**: sabios que bloquearon el item en alguna ronda y luego firmaron tras enmiendas — la textura del debate aunque el resultado final sea unánime._

## ❌ Refutadas por la verificación

_Estas tareas se apoyaban en afirmaciones que NO resistieron el contraste con el código real. Fuera del plan accionable._

- **Design spike: guided first-invoice activation flow** — The core premise — 'has no real-invoice guidance' — is false. usePrimerosPassos.ts already defines a 'factura' step (id='factura') linking to /ventas/facturas/nueva with tips and detail text, rendered in the onboarding checklist UI. The page already guides users toward their first real invoice.
- **Backup/export automático de BD local para cumplimiento fiscal** — The core premise — 'the backup system exists but needs validation of 3 gaps' — collapses: gap (1) run_backup_job is ALREADY auto-scheduled daily at 4:00 via APScheduler, and gap (2) backup UI IS already discoverable in nav-config at /configuracion/backups. The task's central justification (these gaps need a validation spike) is factually false for 2 of 3 stated gaps. Peripheral counts are also wrong: 64 files not 34, 4 test files not 6, desktop/main.js has no backup code.
- **Banking agent tools: validate user-supplied inputs (dates, IBANs, amounts)** — The task's entire premise is fabricated. No tool function accepts date strings, IBANs, or account IDs as parameters. check_balances takes only tenant_id; list_transactions and financial_summary take tenant_id + days_back (int). Account IDs and IBANs come from DB-stored PSD2 credentials, not from LLM tool calls. The proposed validations (ISO 8601 dates, IBAN regex, amount ranges) target parameters that do not exist.

## Verificación de afirmaciones

_Cada cifra del debate recontrastada contra el repo por un verificador con presupuesto de tools SIN límite. '❓' = no comprobable con Read/Glob/Grep (no es un aprobado)._

### — · PSD2 demo-vs-real visible indicator
_verification failed (DriverInvalidResponseError); claims left unchecked — treat the rationale as unconfirmed._

### ✅ medido · Tenant-level LLM cost circuit breaker — hourly hard cap
_Core claims (function name, location at line 106, monthly SUM on TokenLedger) all verified exactly. The 'zero paying tenants' remark is unverifiable from code but is peripheral context, not the task's justification._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| check_tenant_budget exists at agent_budget.py:106 | `Read backend/app/services/agent_budget.py` | Line 106: `async def check_tenant_budget(tenant_id: str, db: AsyncSession) -> bool:` — exact match. | ✅ verified |
| check_tenant_budget already runs a monthly SUM on TokenLedger | `Read backend/app/services/agent_budget.py lines 120-129` | Lines 123-128: `select(func.sum(TokenLedger.cost_usd)).where(TokenLedger.tenant_id == ..., TokenLedger.created_at >= first_of_month)` — monthly SUM confirmed. | ✅ verified |
| Adding a 1-hour window check is genuinely useful against runaway loops (with zero paying tenants the blast scenario is theoretical) | `N/A` | Whether the blast scenario is 'theoretical' and whether zero paying tenants exist is a business/operational claim, not measurable from code. | ❓ unverifiable |
| One new setting in config.py (implying config.py is where settings live) | `Glob backend/app/core/config.py + Read agent_budget.py line 114` | config.py exists; line 114 of agent_budget.py imports `from app.core.config import settings` and line 116 reads `settings.TENANT_MONTHLY_LLM_BUDGET_USD` — config.py is the correct target for a new setting. | ✅ verified |

### ❌ refutado · Design spike: guided first-invoice activation flow
_The core premise — 'has no real-invoice guidance' — is false. usePrimerosPassos.ts already defines a 'factura' step (id='factura') linking to /ventas/facturas/nueva with tips and detail text, rendered in the onboarding checklist UI. The page already guides users toward their first real invoice._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| The primeros-pasos page (page.tsx, DemoDataCard.tsx, usePrimerosPassos.ts) seeds demo data | `Read DemoDataCard.tsx — look for seed/demo functionality` | DemoDataCard.tsx calls onboarding.seedDemo() (line 31) and onboarding.clearDemo() (line 47) to seed/clear demo clients, products, invoices. Comment on line 9-12 confirms: 'siembra/borra una pyme demo'. | ✅ verified |
| The primeros-pasos page has no real-invoice guidance | `Read usePrimerosPassos.ts lines 85-98 — step 'factura'` | usePrimerosPassos.ts defines step id='factura' (lines 85-98) with href='/ventas/facturas/nueva', hrefLabel from translations, detail text, and 2 tips. page.tsx renders all steps with expand/collapse UI, a direct 'Play' link to the href, and a mark-done button. This IS real-invoice creation guidance in the onboarding flow. | ❌ refuted |
| Building activation UX without defined metrics, wireframes, or user feedback is speculative (implies no telemetry exists) | `Grep for telemetry/analytics/track/funnel/conversion in primeros-pasos directory` | No telemetry, analytics tracking, or funnel measurement code found in the primeros-pasos files. Only CSS 'tracking-wider' class names matched. No drop-off measurement exists. | ✅ verified |

### ❌ refutado · Backup/export automático de BD local para cumplimiento fiscal
_The core premise — 'the backup system exists but needs validation of 3 gaps' — collapses: gap (1) run_backup_job is ALREADY auto-scheduled daily at 4:00 via APScheduler, and gap (2) backup UI IS already discoverable in nav-config at /configuracion/backups. The task's central justification (these gaps need a validation spike) is factually false for 2 of 3 stated gaps. Peripheral counts are also wrong: 64 files not 34, 4 test files not 6, desktop/main.js has no backup code._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| Grep backup → 34 files | `Grep pattern=backup output_mode=files_with_matches head_limit=0` | Grep returned 64 files matching 'backup', not 34. | ❌ refuted |
| __init__.py exports create_backup, restore_backup, run_backup_job, rotate_backups | `Read backend/app/services/backup/__init__.py` | All four symbols are exported in __all__ and imported from legacy_local.py. Verified. | ✅ verified |
| __init__.py exports encrypt_e2e, decrypt_e2e | `Read backend/app/services/backup/__init__.py` | Both symbols imported from crypto.py and listed in __all__. Verified. | ✅ verified |
| B2 cloud transport exists (b2_client.py) | `Glob backend/app/services/backup/b2_client.py` | File exists. | ✅ verified |
| rolling retention exists (retention.py) | `Read __init__.py lines 25-28` | retention.py exists and exports BackupCandidate, apply_rolling_retention. | ✅ verified |
| 6 test files for backup | `Glob backend/tests/test_backup*` | Only 4 test files: test_backup.py, test_backup_b2.py, test_backup_b2_transport.py, test_backup_local.py. | ❌ refuted |
| migration 0017 exists | `Glob **/0017*` | backend/app/db/migrations/versions/0017_backup_records.py exists. | ✅ verified |
| Gap: run_backup_job may not be triggered automatically (only API endpoint) | `Grep backup in backend/app/services/scheduler.py` | run_backup_job IS scheduled via APScheduler CronTrigger(hour=4, minute=0) as job 'daily_backup'. The gap is already addressed — automatic triggering exists. | ❌ refuted |
| Gap: backup UI may not be discoverable in frontend | `Grep backup in frontend/src/components/layout/nav-config.ts` | Nav config has 'Copias de seguridad' at /configuracion/backups (adminOnly). page.tsx exists at frontend/src/app/(dashboard)/configuracion/backups/page.tsx. UI is discoverable. | ❌ refuted |
| Gap: verify restore_backup actually works E2E on a fresh install | `N/A` | Cannot verify E2E restore functionality with static code analysis tools. | ❓ unverifiable |
| desktop/main.js is a relevant file_touched for backup | `Grep backup in desktop/main.js` | desktop/main.js exists but contains ZERO references to 'backup'. It is not relevant to the backup system. | ❌ refuted |

### ⚠️ parcial · Extract withAuthRetry interceptor in client.ts
_Core premise (duplication of 401→refresh→retry flow) is verified and actually understated — 4 functions duplicate it, not just 2. Peripheral claims are inaccurate: errorType values are 3 not 5, and importers are 69 not 64._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| client.ts request() and requestUpload() duplicate the entire 401→refresh→retry→clearTokens flow | `Read frontend/src/lib/api/client.ts` | request() has 401→tryRefresh→retry→clearTokens at lines 126-155. requestUpload() has same pattern at lines 184-198. Additionally fetchBlob (219-225) and downloadBlob (243-251) also duplicate it. Duplication is real. | ✅ verified |
| The duplicated flow is ~40 lines | `Read frontend/src/lib/api/client.ts, counted lines of 401 blocks` | request() 401+error block: lines 126-174 = ~48 lines. requestUpload() 401+error block: lines 184-211 = ~28 lines. Neither is exactly ~40; average is ~38. Roughly in the ballpark but not precise. | ✅ verified |
| All 5 ApiError errorType values must be preserved | `Grep for hardcoded errorType strings in client.ts` | Only 3 distinct hardcoded errorType values in client.ts: 'network_error' (line 103), 'session_expired' (lines 138, 154, 196), 'license_required' (line 159). Other occurrences pass through dynamic err.type from backend. There is no set of 5. | ❌ refuted |
| client.ts is the most-imported frontend file with 64 importers | `Grep for import from client.ts across frontend/` | Found 69 files importing from client.ts, not 64. Whether it is the single most-imported file was not exhaustively verified, but 69 importers is plausible for 'most-imported'. | ❌ refuted |
| Blast radius MEDIUM | `Grep importer count` | 69 importers is significant. MEDIUM vs HIGH is a subjective judgment call. | ❓ unverifiable |

### ✅ medido · Explicit scope-out: backend/app/api route layer is clean — no items this iteration
_All claims verified against the repo. 68 route files confirmed, exactly 2 import agents (both lazy/local imports inside handlers at the stated line numbers)._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| 68 route files exist | `Glob backend/app/api/**/routes/**/*.py then exclude __init__.py` | 70 total .py files in routes tree; minus 2 __init__.py = 68 non-init route files. Matches. | ✅ verified |
| Only 2 of 68 route files import agents directly | `Grep 'import.*agents\|from.*agents' in backend/app/api/` | Exactly 2 hits in route files: marketing.py:588 and messaging.py:202. A 3rd hit in schemas/tasks.py is not a route file. Matches claim. | ✅ verified |
| marketing.py imports agent at line 588 | `Read marketing.py lines 583-597` | Line 588: 'from app.agents.marketing import run_agent' — confirmed. | ✅ verified |
| messaging.py imports agent at line 202 | `Read messaging.py lines 197-211` | Line 202: 'from app.agents.email import run_email_agent' — confirmed. | ✅ verified |
| Both are lazy imports inside handlers (not top-level) | `Read surrounding context of both imports` | marketing.py:588 is inside a handler function body (after 'def' at ~line 580, Depends params). messaging.py:202 is inside a handler function body (after 'def' at ~line 195, Depends params). Both are local imports, not module-level. | ✅ verified |
| The route layer delegates correctly to services/agents — no structural debt warrants a 'now' item | `Grep for agent imports in routes + manual review` | Only 2 lazy agent imports found, both following the pattern of calling run_agent() from inside a handler. No top-level agent imports, no business logic leaking into routes. Consistent with CLAUDE.md architecture rules. | ✅ verified |

### ⚠️ parcial · Add pool_recycle and pool_timeout to async engine configuration
_Core claims (pool_recycle/pool_timeout absent, pool_size=10 and pool_pre_ping=True present) are verified. The importer count is wrong (163 files, not 138) and the GitNexus score is unverifiable, but these are peripheral — the task's premise holds._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| base.py has 138 importers | `Grep 'from app\.db\.base import' in backend/ with output_mode=count` | 163 files contain 'from app.db.base import' (176 total occurrences). The claim of 138 is understated. | ❌ refuted |
| base.py creates the async engine with pool_size=10 and pool_pre_ping=True | `Read backend/app/db/base.py` | Lines 19-21 confirm pool_size=10, pool_pre_ping=True inside _engine_kwargs.update(). | ✅ verified |
| base.py omits pool_recycle and pool_timeout entirely (0 hits) | `Grep 'pool_recycle\|pool_timeout' in backend/` | Zero hits in any backend file (only hits were in the debate JSONL outside backend/). Confirmed absent from base.py and session.py. | ✅ verified |
| score 56 from GitNexus | `N/A — GitNexus-internal metric` | Cannot reproduce a GitNexus centrality score with Read/Glob/Grep. | ❓ unverifiable |
| This is a 3-line addition to _engine_kwargs with zero API surface change | `Read backend/app/db/base.py` | Adding pool_recycle and pool_timeout to the dict on lines 17-23 would indeed be ~2-3 lines inside the existing .update() call with no API change. | ✅ verified |

### ❌ refutado · Banking agent tools: validate user-supplied inputs (dates, IBANs, amounts)
_The task's entire premise is fabricated. No tool function accepts date strings, IBANs, or account IDs as parameters. check_balances takes only tenant_id; list_transactions and financial_summary take tenant_id + days_back (int). Account IDs and IBANs come from DB-stored PSD2 credentials, not from LLM tool calls. The proposed validations (ISO 8601 dates, IBAN regex, amount ranges) target parameters that do not exist._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| _account_tools.py and _transaction_tools.py receive user-controlled parameters: date ranges, account IDs, IBANs | `Read both files + grep for function signatures and parameter names (iban, account_id, date_from, date_str)` | _account_tools.py: check_balances(tenant_id: str) — NO date ranges, NO account IDs, NO IBANs as params. _transaction_tools.py: list_transactions(tenant_id: str, days_back: int=30), financial_summary(tenant_id: str, days_back: int=30) — only tenant_id and days_back (an int). Account IDs come from creds.get('account_ids') (DB-stored PSD2 credentials), NOT from LLM/user input. IBANs are never accepted as parameters anywhere. | ❌ refuted |
| A malformed date string causes an unhandled ValueError | `Read _transaction_tools.py lines 51: date_from = date.today() - timedelta(days=days_back)` | There is no date string parameter. Dates are constructed internally via date.today() - timedelta(days=days_back) where days_back is typed as int. No user-supplied date string parsing exists, so no ValueError from malformed date strings is possible. | ❌ refuted |
| A crafted IBAN could leak into logs or error messages | `Grep for iban/IBAN in both files' function signatures` | No IBAN parameter exists in any tool function signature. IBANs appear only in demo data constants (_DEMO_SALDOS) and in output formatting of data retrieved from the PSD2 API (details.get('iban')), never as user/LLM-supplied input. | ❌ refuted |
| These flow into PSD2 API calls or demo data filters with no schema validation | `Read both files fully` | The only LLM-controlled parameter beyond tenant_id is days_back (int). It flows into timedelta(days=days_back). Python's type annotation provides a basic guard; there is indeed no explicit range validation (e.g. negative days_back). However the rationale frames this as date/IBAN/amount validation, which is a mischaracterization of what actually needs validating. |  weakened |
| Validation needed for: date format (ISO 8601), IBAN format (regex), amount ranges (non-negative) | `Read all tool signatures in both files` | No tool accepts a date string, IBAN string, or amount as a parameter. The only validatable user-facing param is days_back (int). The three proposed validation targets don't correspond to any actual parameters. | ❌ refuted |
| Files exist: backend/app/agents/banking/_account_tools.py and _transaction_tools.py | `Glob for both paths` | Both files exist. | ✅ verified |

### ✅ medido · Explicit scope-out: frontend/src/components — no structural debt this iteration
_Core claim (components are leaf nodes that don't reverse-import into lib/api) verified with zero matches. File count of 76 exactly confirmed. The 'score 1802' and 'withAuthRetry extraction' are unverifiable but peripheral — the task is explicitly a scope-out, so its premise rests on the leaf-node argument, which holds._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| The components directory has 76 files | `Glob: frontend/src/components/**/*.*` | Exactly 76 files returned by glob. | ✅ verified |
| score 1802 | `N/A — no scoring system definition found in repo` | No scoring methodology in the codebase to reproduce this number. | ❓ unverifiable |
| components are leaf nodes — they consume lib/api, not the other way around | `Grep: 'components' in frontend/src/lib (files_with_matches); Grep: 'from.*components\|import.*components' in frontend/src/lib/api (count)` | Zero matches. No file under frontend/src/lib imports from components. | ✅ verified |
| The withAuthRetry extraction in client.ts will transitively improve their reliability | `Grep: 'withAuthRetry' across entire repo (files_with_matches); Grep: 'retry\|authRetry' in client.ts (content)` | withAuthRetry does not exist in any source file (only in debate JSONL). client.ts has inline retry logic (lines 131-149) but no extracted withAuthRetry function. This references a planned extraction from another task, not existing code. | ❓ unverifiable |
| No component-level structural debt was surfaced by any sage | `N/A — refers to debate proceedings, not code` | Cannot verify claims about what sages said; this is a process claim. | ❓ unverifiable |

### ✅ medido · Explicit scope-out: backend/scripts — operational scripts are demo/CI utilities, not architectural debt
_Core claims (no app imports, standalone utilities) fully verified. File count is 36 .py files not 35 — off by 1, immaterial. GitNexus score (420) is unverifiable but peripheral._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| backend/scripts contains 35 files | `Glob backend/scripts/* (count .py files excluding __pycache__)` | 36 .py files found, 50 total files including .log and .json artifacts. Off by 1 on .py count, off by 15 if 'files' means all files. | ❌ refuted |
| Example files exist: seed_demo.py, smoke_demo.py, test_all.py, ci_init_db.py | `Glob backend/scripts/*` | All four files present in glob output. | ✅ verified |
| They don't export symbols consumed by the app | `Grep 'from scripts\.\|import scripts\.' and 'from backend\.scripts\|import backend\.scripts' across all .py files` | Zero matches. No app code imports anything from backend/scripts/. | ✅ verified |
| All are standalone operational utilities for seeding, testing, and CI | `Glob backend/scripts/* — reviewed file names` | File names confirm: seed_*, smoke_*, test_*, ci_init_db, create_*, gen_*, db_drift, db_sync, llm_log_tail, audit_*, update_*, inject_demo_credentials, _camp_* (campaign test scripts). All consistent with operational/CI/demo utilities. | ✅ verified |
| have no import cycles | `Grep for imports from scripts in the whole backend` | No code outside scripts/ imports from scripts/, so import cycles are structurally impossible. Claim verified by absence of any inbound imports. | ✅ verified |
| their score is low (420) | `N/A — GitNexus internal metric` | Cannot reproduce GitNexus complexity score with file-system tools. | ❓ unverifiable |

### ⚠️ parcial · Explicit scope-out: tasks/ — reconcile todo.md with plan decisions post-execution
_All core claims verified (todo.md exists, last reconciled 2026-06-23, references A1-A7 and E2E coverage, is institutional memory per CLAUDE.md). The file count '33 files' is materially wrong — actual count is 55. The 'score 445' is an opaque planner metric, unverifiable._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| tasks/ contains 33 files | `Glob tasks/**/*` | Glob returned 55 files (including subdirectories templates/, audit/, reports/, cuadre/, ronda/, forja/). Even counting only top-level files: 42. No way to reach 33. | ❌ refuted |
| score 445 for tasks/ | `N/A — internal planning metric` | No scoring mechanism found in the repository; this is an opaque planner-internal number. | ❓ unverifiable |
| tasks/ contains todo.md and lessons.md | `Glob tasks/todo.md, Glob tasks/lessons.md` | Both files exist. | ✅ verified |
| todo.md and lessons.md are the project's institutional memory per CLAUDE.md workflow rules | `Grep 'tasks/todo\|tasks/lessons' CLAUDE.md` | CLAUDE.md line 26: 'Plan → tasks/todo.md \| Lessons → tasks/lessons.md \| Track progress as you go.' Line 16: 'After ANY correction → update tasks/lessons.md'. | ✅ verified |
| todo.md was last reconciled 2026-06-23 | `Read tasks/todo.md line 3` | Line 3: 'Última actualización: 2026-06-23 (reconciliado contra el código)' | ✅ verified |
| todo.md references items A1-A7 deuda técnica diferida | `Grep 'A1-A7' tasks/todo.md` | Line 13: 'El resto de "Deuda técnica diferida" (A1-A7) se verificó vivo en código.' | ✅ verified |
| todo.md references E2E coverage | `Grep 'E2E\|e2e\|cobertura' tasks/todo.md` | Multiple hits: line 11 'cobertura E2E', line 307 '## Tests E2E (cobertura)', lines 312-342 with detailed E2E test listings. | ✅ verified |
| Plan references 'backup to next-year' and 'guided first-invoice to next-quarter' as deferred items | `N/A — references plan decisions external to the repository` | These are claims about what the broader plan document decided, not about repository contents. Cannot verify against code. | ❓ unverifiable |


## Puntos de impacto (archivos por tarea)

- **PSD2 demo-vs-real visible indicator** → `backend/app/agents/banking/_psd2_helpers.py`, `backend/app/agents/banking/_account_tools.py`, `backend/app/agents/banking/_transaction_tools.py`, `frontend/src/app/(dashboard)/primeros-pasos/_components/DemoDataCard.tsx`
- **Tenant-level LLM cost circuit breaker — hourly hard cap** → `backend/app/services/agent_budget.py`, `backend/app/core/config.py`, `backend/tests/test_money_path.py`
- **Extract withAuthRetry interceptor in client.ts** → `frontend/src/lib/api/client.ts`
- **Explicit scope-out: backend/app/api route layer is clean — no items this iteration** → `backend/app/api/v1/routes/marketing.py`, `backend/app/api/v1/routes/messaging.py`
- **Add pool_recycle and pool_timeout to async engine configuration** → `backend/app/db/base.py`
- **Explicit scope-out: frontend/src/components — no structural debt this iteration** → `frontend/src/components/ui/button.tsx`
- **Explicit scope-out: backend/scripts — operational scripts are demo/CI utilities, not architectural debt** → `backend/scripts/seed_demo.py`, `backend/scripts/test_all.py`, `backend/scripts/ci_init_db.py`
- **Explicit scope-out: tasks/ — reconcile todo.md with plan decisions post-execution** → `tasks/todo.md`, `tasks/lessons.md`

## 🔭 Visión estratégica

**Harden the trust layer between demo and production so the first paying pyme never sees fake data dressed as real — that is the gate to revenue.**

### Hacia dónde encauzarlo

AutomatizaCore's strategic position is unusually strong on paper: AEAT fiscal compliance (modelos 303/130 with PDF-calcado fidelity), VeriFactu integration, local-first data sovereignty via embedded Postgres, and AI agents that can decompose natural-language business instructions into multi-step workflows. The moat is real — no competing Spanish SME tool combines fiscal compliance, banking PSD2 integration, and LLM-powered automation in a desktop package. But the moat is dry: zero customers are paying. Marcos rejected a 200k acquisition offer betting on 100 pymes × ~180€/month, and that thesis remains unvalidated. The council's debate, stripped of its tactical details, revealed a single strategic failure mode: the product cannot distinguish between demo and production state at the boundaries where trust matters most. The PSD2 banking tools serve hardcoded demo balances with no user-visible indicator. The onboarding seeds demo data but has no telemetry measuring whether users actually cross from demo to real invoicing. The LLM cost controls exist monthly but lack the hourly circuit breaker that prevents a runaway agent from burning through a trial customer's goodwill in minutes. Every tactical item the council agreed on — the is_demo flag propagation, the circuit breaker, the pool_recycle for desktop sleep/wake resilience, the withAuthRetry extraction — serves the same strategic imperative: make the product trustworthy enough that a real asesoría or gestoría can rely on it for a real client's fiscal quarter.

The user persona is a Spanish gestoría or small asesoría fiscal managing 10-50 clients, currently juggling A3, Sage Despachos, or spreadsheets. The distribution channel is direct outbound to this segment — the desktop-first architecture is an advantage here because gestorías handle sensitive fiscal data and distrust cloud-only tools. The moat deepens with each AEAT modelo implemented (303/130 done, 111/115/200 ahead) and with each VeriFactu integration point that competitors must replicate from scratch. But the moat only compounds if customers are using it — and customers won't use it if they can't tell demo data from real bank balances.

The tension the council surfaced between the Conservative and Modernizer axes — belt-and-suspenders reliability (pool_pre_ping + pool_recycle) versus YAGNI minimalism — should default to Conservative for anything touching fiscal data or money, and to Simplificador for everything else. A gestoría that sees a stale bank balance because the desktop woke from sleep and the connection pool rotted will never trust the tool again. Over-engineering the component layer or adding premature caching for an empty TokenLedger table, on the other hand, is wasted motion before the first sale. The verification phase proved this instinct correct: the backup system already works (auto-scheduled, UI discoverable, E2E encryption), the onboarding already guides toward a first invoice, and the banking don't even accept the IBAN/date parameters the council thought needed validation. The real gaps are narrower and more trust-critical than the debate initially assumed.

### Features futuros propuestos

| Horizonte | Feature | Por qué | Sabios |
|-----------|---------|---------|--------|
| `next-quarter` | **Activation telemetry funnel: measure demo-to-real conversion per onboarding step** | The council's item 3 was refuted — invoice guidance already exists in usePrimerosPassos.ts — but the underlying product question is valid: nobody knows if users complete the funnel. Adding lightweight event tracking (step_started, step_completed, demo_seeded, first_real_invoice_created) to the existing onboarding flow gives Marcos the data to decide what to build next, not guesswork. | producto, optimizador |
| `next-quarter` | **AEAT modelo 111/115 PDF-calcado implementation** | 303 and 130 are done. 111 (retenciones IRPF trabajadores) and 115 (retenciones alquileres) are the next most common obligations for the target gestoría persona. Each new modelo deepens the fiscal compliance moat and adds a concrete reason for a prospect to switch from A3/Sage. | producto, guardian |
| `next-quarter` | **Offline-first reconciliation for PSD2 banking data** | The desktop app sleeps, wakes, and loses connectivity. When PSD2 credentials exist but the API is unreachable, the current code silently falls back to demo data — the exact trust gap item 1 addresses tactically. Strategically, the product needs a local transaction cache with explicit sync status (last_synced_at, stale_since) so the user always knows the freshness of their banking view. | modernizador, conservador, guardian |
| `next-year` | **Multi-tenant trial environment with usage-metered billing integration** | The license server exists (Render, Stripe, Ed25519 signatures) but the product has no self-serve trial flow. Before scaling past the first 10 hand-sold customers, Marcos needs a trial-to-paid pipeline where the hourly circuit breaker and monthly budget cap translate directly into metered Stripe charges. | producto, optimizador |

### Hilos de investigación abiertos

- **Does the silent PSD2 demo fallback actually trigger in production when bank APIs fail, or is it dead code that only runs when no credentials are configured?** — Item 1's urgency depends on whether the fallback path is reachable for a real user with real PSD2 credentials. If the fallback only triggers when credentials are absent (i.e., demo-only tenants), the fix is still needed but the risk is cosmetic, not financial. If it triggers on API timeouts or 5xx errors from real banks, it's a data-integrity emergency. The council assumed the latter without verifying the conditional logic in _account_tools.py.
- **What is the actual gestoría workflow for the first fiscal quarter — which screens must work flawlessly end-to-end before Marcos can charge?** — The council optimized individual code seams (client.ts auth retry, pool recycling, banking validation) but never mapped the critical user journey: client onboarding → invoice creation → automatic accounting → modelo 303 generation → AEAT submission. If any step in that chain is broken or missing, the tactical fixes are irrelevant to revenue. This research should produce a single E2E smoke test that validates the paying-customer path.
- **Is the desktop embedded Postgres (port 5433) backup + restore cycle actually tested on a fresh Windows install, or only on dev machines?** — The verification phase confirmed backup is auto-scheduled and has UI, but could not verify E2E restore on a fresh install. For the target persona (non-technical gestoría staff), a backup that creates files but can't restore them is worse than no backup — it creates false confidence. This is the only gap the council identified in the backup system that wasn't already addressed, and it's the one that matters most for a desktop product handling fiscal data.
