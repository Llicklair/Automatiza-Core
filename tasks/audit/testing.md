# Testing & CI Audit — 2026-06-19

## Test counts
- **Backend**: 237 test files; **2193 tests collected, 0 collection errors** (41 deselected, ~1.3s collect). pytest 9.0.3, Python 3.11.9.
- **Frontend**: 18 test files (vitest + jsdom). `npx vitest list` enumerates cleanly (PageHeader, toast store, navigationGuard, update-channel, etc.).
- Conftest uses **in-memory SQLite (async)** with JSONB→JSON / BigInteger→INTEGER monkeypatches, so tests run without Postgres locally. CI uses real Postgres 16.

## Run results (local subset, SQLite)
- Fiscal + auth + crypto subset: `test_casillas_130, test_casillas_modelos, test_casillas_347, test_api_auth, test_aeat_certificate_key, test_encryption, test_backup_local` → **52 passed, 0 failed (24.9s)**.
- Casillas files are named `test_casillas_{100,130,190,200,347,modelos}.py` (no `test_casillas_303`).
- Backend test suite is healthy and runnable locally.

## Coverage map (test files referencing each critical service)
| Service | Test files | Status |
|---|---|---|
| billing | 50 | Strong |
| aeat/fiscal | 32 | Strong (casillas 100/130/190/200/347 + verifactu x7) |
| backup/crypto | 12 (`test_backup*`, `test_encryption`) | Good |
| banking | 9 | OK |
| auth | 6 | Adequate |
| tenant/multi-tenancy | 6 | Adequate |
| treasury (incl. SEPA) | 6 | Thin — only 1 SEPA e2e (`test_e2e_treasury_sepa.py`) |
| collections | 3 | Thin |
| signing | 3 | Thin |
| accounting | 3 | Thin |

### Gaps / thin critical paths
- **SEPA/payments**: single e2e file (`test_e2e_treasury_sepa.py`). No unit-level tests for remesa generation/XML. Highest-value gap given fiscal risk profile.
- **RLS / multi-tenancy**: no dedicated row-level-security test; tenant isolation covered only indirectly (e.g. `test_clients_unique_constraint.py` checks `UNIQUE(tenant_id,nif)` + cross-tenant NIF reuse). SQLite conftest cannot exercise Postgres RLS policies — **RLS is effectively untested**.
- **signing / collections / accounting**: 3 files each, light for their criticality.
- Many `app/services/*` modules have no 1:1 test file (mapped by usage, not direct unit tests).

## Test quality
- **Skips**: 18 skip/xfail markers, all conditional `skipif` with legit reasons (redis not installed, no LLM key, XSD missing) — none are dead `@pytest.mark.skip`.
- **Assertless**: `test_clients_unique_constraint.py` flagged by grep but legitimately uses `pytest.raises(IntegrityError)` + "no debe lanzar" commits. Not a real gap.
- **Over-mocked** (>8 mocks/file): `test_backup_b2_transport.py`(9), `test_health_checks.py`(10), `test_inventory_agent.py`(9), `test_scanner_auth.py`(11). Transport/health mocking is reasonable; `test_inventory_agent`/`test_scanner_auth` worth reviewing for real-behavior coverage.
- `test_invoice_numbering.py` contains a TODO/placeholder marker — review.
- No `assert True` placeholder suites found.

## CI assessment (`.github/workflows/ci.yml`)
**Gated (blocking):**
- `backend-lint`: Ruff lint `--select E,W,F,I` (BLOCKING). 
- `backend-test`: real Postgres 16 service; schema via `scripts/ci_init_db.py` (create_all + stamp, NOT `alembic upgrade head` — migration chain not self-consistent from empty DB). Runs `pytest tests/ -v --cov=app --cov-fail-under=57` → **coverage gate 57% (ratchet floor, target 70%)**. This is the strongest gate.

**Advisory (continue-on-error — NOT enforced):**
- Ruff format check, mypy strict (agents/services), mypy rest-of-backend. ~1500 type gaps acknowledged.
- Codecov upload (continue-on-error).

**Frontend CI:** runs in separate job (lint `--max-warnings 20`, vitest). Coverage thresholds in `vitest.config.ts` are **lines:2 / functions:2 / branches:1 / statements:2** — i.e. ~2.7% real coverage, gate set to a near-zero anti-regression floor. Frontend is essentially untested by coverage standards.

**Findings:**
- Backend gate solid (57% line coverage enforced + Postgres). 
- Frontend coverage gate is cosmetic (2%); large UI surface untested.
- Type checking (mypy) and `ruff format` are non-blocking — type regressions can merge.
- `release.yml` exists (not deeply audited here); build/sign pipeline.
- No broken/disabled test steps detected; CI design is intentional and documented in-line.
