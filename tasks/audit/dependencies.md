# Dependency / Build / Release-Health Audit

Date: 2026-06-19 · Branch: chore/cleanup-stale-reports

## 1. Dependency versions & supply-chain

### Backend (`backend/requirements.txt`) — HIGH severity
Every dependency uses unpinned `>=` minimums and **there is NO Python lockfile**
(no `poetry.lock`, `requirements.lock`, `uv.lock`; `pyproject.toml` present but no
lock committed). A fresh `pip install` resolves to whatever is latest on PyPI →
non-reproducible builds and a supply-chain blast radius equal to the entire
transitive tree. The desktop installer bundles `../backend` verbatim, so each
build pins a different set at package time.

Lower-bound CVE exposure (the `>=` floor is installable and vulnerable):
- `cryptography>=43.0.0` — floor predates fixes for OpenSSL advisories shipped in 44.x. **MEDIUM**
- `lxml>=4.9.0` — 4.9.0 is years old; XML parsing surface (VeriFactu XAdES path uses lxml). Bump floor to a current 5.x. **MEDIUM**
- `python-jose[cryptography]>=3.3.0` — 3.3.0 has known algorithm-confusion / DoS advisories (GHSA). Consider migrating to `PyJWT` (already a dep) and dropping python-jose. **MEDIUM**
- `reportlab>=4.2.0`, `pypdf>=5.0.0` — older floors have parsing DoS history; PDFs are generated from fiscal data. **LOW–MEDIUM**
- `langgraph>=0.2.0`, `langchain-*>=0.3.0`, `anthropic>=0.40.0` — pre-1.0 / fast-moving; `>=` invites breaking API drift, not just CVEs. **MEDIUM** (stability)

Recommendation: pin with `==` or compatible-release `~=` and commit a lockfile;
raise the floors above to current patched releases.

### Frontend (`frontend/package.json`) — lockfile committed (`package-lock.json`), good.
- `next 16.2` exact, `react ^19.2.6` — current majors, no known risky pins. **LOW**
- `next-intl ^4.13`, `tailwindcss ^4.3`, `eslint ^9`, `vitest ^4` — all on current majors; caret ranges are fine with the lockfile present.
- `overrides: { "@swc/helpers": ">=0.5.17" }` — single override, benign.
- No obvious duplicate/conflicting deps; `@types/dompurify` kept alongside `dompurify` (dompurify ships its own types in 3.x — `@types/dompurify` is now a deprecated stub, **LOW** cleanup).

### Desktop (`desktop/package.json`) — lockfile committed (`package-lock.json`), good.
- `electron ^42.3.0` (current), `electron-builder ^26.8.1`, `electron-updater ^6.3.9`, `electron-store ^11`. All current. **LOW**

## 2. Frontend build / typecheck
- `npx tsc --noEmit` → **0 errors** (PASS). CLAUDE.md pre-commit gate is satisfiable.
- `npm run lint` (`eslint src/ --max-warnings 20`) → **0 errors, 24 warnings → exit 1** (FAILS the 20-warning ceiling). **MEDIUM**
  - All 24 are `react-hooks/exhaustive-deps`: ~16 missing-dependency (mostly `t`/`load`/`loadData`) + ~5 *unused* `eslint-disable` directives (LotsPanel, WarehouseStockPanel, useTaskPanel, useEmpleadosCRUD, usePayrolls). 8 are auto-fixable with `--fix`.
  - The 5 stale disable directives + `--fix` would drop the count under 20 and make lint green again.

## 3. Electron desktop security posture
File: `desktop/main.js`, `desktop/service-manager.js`
- **mainWindow**: `nodeIntegration:false`, `contextIsolation:true` — CORRECT. **LOW**
- **splashWindow** (`main.js:157-158`): `nodeIntegration:true`, `contextIsolation:false` — insecure, but loads only the local bundled `splash.html` (no remote content), so practical risk is low. Still, flip it to safe defaults. **LOW**
- `will-navigate` + `setWindowOpenHandler` are wired (navigation lock-down present). `requestSingleInstanceLock` used. Good.
- mainWindow `loadURL("http://localhost:3000")` — local dev/prod server over plain HTTP on loopback; acceptable for a bundled local app.
- **Auto-update**: `electron-updater` from GitHub provider (`Llicklair/Automatiza-Core`), `autoDownload:true`, `autoInstallOnAppQuit:true`, `checkForUpdates` at boot.
- **Code signing: `forceCodeSigning:false` and no signing config.** Unsigned NSIS installer + auto-update from GitHub releases = updates are **not signature-verified by a publisher cert** (electron-updater still checks the blockmap/sha512 from latest.yml, but anyone who can publish to the release channel can push code). Windows SmartScreen will also warn users on every install. **HIGH** for a fiscal/ERP product handling client tax data.
- `service-manager.js` uses `spawn`/`execSync`/`exec` from child_process to orchestrate Postgres/Python/Next. Inputs are internal (ports, app paths) not user-supplied; `exec`/`execSync` with string commands is a latent injection vector if any path/env becomes attacker-influenced — keep args arrayized. **LOW–MEDIUM**
- Secrets: SECRET_KEY / TENANT_ENCRYPTION_KEY generated on first boot and stored via Electron `safeStorage` (DPAPI), with plaintext `secrets.json` fallback in dev. Reasonable.

## 4. Committed build artifacts
- `desktop/dist/` is **572 MB** and contains `win-unpacked/resources/project/backend/requirements.txt` (a full unpacked build). It IS gitignored (`git check-ignore` matches), so not in the repo — but it bloats the working tree and is a duplicate dependency source. Confirm it's never force-added. **LOW**

## 5. Config hygiene — `.env.example` completeness
`.env.example` documents auth, LLM providers, OAuth (Google/MS), SMTP, Postgres.
**Env vars referenced in backend code but NOT documented in `.env.example`** (excluding OS vars PATH/TEMP/APPDATA/TMP/etc. and pydantic-settings defaults):
- Integrations/observability: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_WEBHOOK_URL`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `POSTHOG_API_KEY`, `UNSPLASH_ACCESS_KEY`, `ZERNIO_API_BASE`, `REDIS_URL`
- Backups: `BACKUP_DIR`, `BACKUP_ENABLED`, `BACKUP_RETENTION_DAYS`
- Models/limits: `OPENAI_MODEL`, `OPENAI_IMAGE_MODEL`, `GROQ_MODEL`, `TENANT_MONTHLY_LLM_BUDGET_USD`, `OAUTH_PROXY_URL`, `OAUTH_REDIRECT_URI`, `TELEMETRY_SALT`, `SCANNER_ALLOWED_SCOPES`, `SCANNER_TOKEN_EXPIRE_MINUTES`
Most have safe defaults, but Telegram/Langfuse/Posthog/Redis/Backup vars are operationally relevant and undocumented. **MEDIUM** (operability, not security).
- No `Dockerfile` / `docker-compose` present (native service-manager replaced Docker — consistent with code comments).

## 6. i18n parity — CRITICAL finding
- `node scripts/check_i18n_parity.mjs` → "OK — 4817 claves en paridad es/en". **But the script only compares es vs en.**
- Actual leaf-key counts: **es=4817, en=4817, ca=429, eu=429, gl=429.**
- Catalan/Basque/Galician are **~91% incomplete** (429/4817). The 5 locale files are advertised as supported but ca/eu/gl are effectively stubs. The parity script gives false confidence because it ignores ca/eu/gl. **HIGH** (shipping 3 broken locales + a check that can't catch it).
- Recommendation: extend `check_i18n_parity.mjs` to validate all 5 locales against es, and either backfill ca/eu/gl or remove them from the advertised locale set.

## Severity summary
| Area | Finding | Severity |
|------|---------|----------|
| Backend deps | Unpinned `>=` + no lockfile | HIGH |
| Backend deps | Old lxml/cryptography/python-jose floors | MEDIUM |
| Desktop | Unsigned installer + auto-update (`forceCodeSigning:false`) | HIGH |
| i18n | ca/eu/gl 91% missing; parity script blind to them | HIGH |
| Frontend lint | 24 warnings > 20 ceiling (lint fails) | MEDIUM |
| Config | ~20 env vars used but undocumented | MEDIUM |
| Desktop | splash window nodeIntegration:true | LOW |
| Repo | 572MB dist/ (gitignored) | LOW |
