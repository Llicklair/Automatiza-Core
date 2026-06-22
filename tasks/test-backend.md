# Backend test run — report

Run date: 2026-06-22 (~19:14–19:40 local)
Command: `poetry run pytest tests/ -q -p no:cacheprovider --tb=line --ignore=tests/test_rls_postgres.py`
Working dir: `backend/`
Duration: 1545.24s (25m45s)

## DB isolation (safeguard)
- `tests/conftest.py` forces **SQLite async in-memory** (`sqlite+aiosqlite://`, `StaticPool`).
- It overrides `os.environ["DATABASE_URL"]` AND monkeypatches `app.db.base.engine`/`AsyncSessionLocal`
  **before importing the app**, so the app can never connect to any Postgres during tests.
- Tables are created/dropped per-test via the `setup_db` autouse fixture.
- **No connection to Postgres 5433 (real user data) is possible** via the normal suite.
- EXCEPTION: `tests/test_rls_postgres.py` builds its OWN asyncpg engine and **defaults to
  `RLS_TEST_PG_PORT=5433`** (real-data port), against test DB `pyme_rls_phase_c_test` /
  creds `pyme_user`. It self-skips on connection failure, but to honor the critical
  safeguard it was **excluded with `--ignore`** (the 41 "deselected"/excluded tests).

## Totals
- passed: **2230**
- failed: **1**
- skipped: **2**
- deselected/excluded (rls_postgres, on purpose): **41**
- warnings: 2 (pydantic v2 config key; an asyncio-marked sync test)

## Failures (grouped)
### test_api_ai_employees.py (1)
- `TestAIEmployees::test_instruct_queues_task`
- Cause (1 line, `--tb=line`):
  `sqlalchemy.exc.StatementError: (builtins.AttributeError) 'str' object has no attribute 'hex'`
  at `sqlalchemy/sql/sqltypes.py:3734`.
- Interpretation: a UUID column receives a **str** instead of a `uuid.UUID` object when
  binding under SQLite (SQLite's UUID binding calls `.hex` on the value). This is a
  test-path / SQLite-binding quirk, NOT a real-data or Postgres issue. Likely a tenant_id
  or task id passed as a plain string somewhere in the instruct→queue-task flow.

## Skipped (2)
- 2 tests skipped via `importorskip`/runtime skip (e.g. semantic-search / optional-dep
  guarded paths). Non-blocking.

## Notes
- No tests were excluded due to lack of Postgres — the suite does not need Postgres.
- The 41 excluded tests are the Postgres-RLS suite, excluded deliberately for the
  5433-safety rule, not for environment limitations.
- Full raw log: `/tmp/pytest_run.log` (Git Bash temp).
