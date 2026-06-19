# Security Audit — AutomatizaCore

Date: 2026-06-19. Scope: backend/app, frontend/src. Multi-tenant FastAPI SaaS.

Overall: the codebase is notably security-conscious — Postgres RLS as a hard
tenant barrier, AES-256-GCM E2E backup crypto with 1M-iteration PBKDF2, bcrypt
hashing, startup validators that refuse default secrets, `create_subprocess_exec`
(no shell), DOMPurify, rate limiting. Findings below are mostly hardening gaps,
not gaping holes. Each is evidence-based with exploitability assessed.

---

## CRITICAL

### C1 — RLS policy is fail-OPEN when tenant GUC is unset
`backend/app/db/migrations/versions/0016_sec_rls.py:43-56`

```sql
CREATE POLICY rls_tenant_isolation ON {table}
    USING (
        tenant_id::text = current_setting('app.current_tenant', true)
        OR current_setting('app.current_tenant', true) IS NULL
        OR current_setting('app.current_tenant', true) = ''
    )
```

The policy returns ALL rows of ALL tenants when `app.current_tenant` is NULL or
`''`. The entire defense therefore depends on `app.current_tenant` ALWAYS being
set to a valid UUID on every connection that touches tenant data. The RLS
listener (`db/rls.py`) explicitly maps invalid/missing tenant to `''`
(documented "fail-open"). So any code path that reaches the DB without a tenant
in the ContextVar — a bug, a forgotten `set_current_tenant`, a background job,
an exception that clears context mid-request — silently leaks cross-tenant data
instead of failing closed.

Why it matters: this converts the "strong barrier" into a barrier that is only
as strong as the weakest application code path. The whole point of RLS (per the
file's own docstring: "defense against agent passing wrong tenant_id") is
undermined by the permissive fallback.

Fix: make RLS fail-CLOSED. Drop the NULL/`''` branches from `USING`. For the
few legitimately tenant-less operations (login user lookup, registration,
migrations), use a dedicated bypass: either run them under the privileged
bootstrap role, or set a sentinel and add an explicit narrow policy. Concretely:

```sql
USING ( tenant_id::text = current_setting('app.current_tenant', true) )
```

and ensure `get_current_user`'s pre-auth `SELECT User WHERE email/id` (which has
no tenant yet) runs before RLS-protected tables are touched, or on a connection
intentionally exempt. Verify with a test: open a session with no tenant set,
`SELECT count(*) FROM invoices` must return 0, not all rows.

---

## HIGH

### H1 — Scanner JWT scope is advisory, not enforced at the data layer
`backend/app/middleware/scanner_auth.py` + `backend/app/api/v1/routes/scanner.py`

Scanner endpoints depend on `get_scanner_user`, which validates the token and
checks the request path against `_BLOCKED_PREFIXES`. But the route handlers call
services with `UUID(scanner["tenant_id"])` taken from the token and DO NOT call
`set_current_tenant(...)`. Two consequences:

1. RLS GUC is never set on these requests → combined with C1's fail-open policy,
   the scanner DB session runs with `app.current_tenant=''` → RLS is fully
   permissive. The only thing keeping scanner queries tenant-scoped is the
   service passing `tenant_id` as a WHERE param. If any scanner service method
   forgets that filter, it reads every tenant. This is exactly the class of bug
   RLS is supposed to backstop, and here the backstop is disabled.
2. The `scope` claim (`inventory:read,...`) in the token is never actually
   checked — only the URL prefix is. The scope string is decorative.

Fix: in `get_scanner_user`, call `set_current_tenant(payload["tenant_id"])`
after validating, so RLS applies to scanner sessions too. Independently of C1
this makes scanner traffic fail-closed. Optionally enforce `scope` per route.

### H2 — `/auth/refresh` issues fresh tokens from stale claims with no revocation
`backend/app/services/auth/service.py:128-141`, `routes/auth.py` (`/refresh` has
NO `@limiter.limit`)

`refresh()` decodes the refresh token and rebuilds an access token purely from
the JWT payload (`role`, `tenant_id`, `email`) WITHOUT re-loading the user from
the DB. Implications:
- A user disabled (`is_active=False`), role-downgraded, or deleted keeps minting
  valid 60-min access tokens for up to 30 days (refresh TTL). Deactivation does
  not take effect until the refresh token expires.
- There is no refresh-token rotation/blacklist; a leaked refresh token is valid
  for 30 days with no way to revoke short of rotating `SECRET_KEY` (which kills
  every session).
- `/refresh` is the only auth route with no rate limit (`/login` 5/5min,
  `/register` 3/hour) → unthrottled token-minting / brute-force surface.

Fix: re-fetch the user in `refresh()`, verify `is_active` and current `role`,
and rebuild claims from the DB row. Add `@limiter.limit("10/minute")`. Consider
rotating refresh tokens (issue new, invalidate old via a stored jti/version).

---

## MEDIUM

### M1 — Stored XSS via Outlook email body rendered without sanitization
`frontend/src/app/(dashboard)/correos/_components/MessageDetailModal.tsx:66`

```tsx
selectedMsg.provider === "outlook" && /<[a-z][^>]*>/i.test(selectedMsg.body)
  ? <div ... dangerouslySetInnerHTML={{ __html: selectedMsg.body }} />
```

Raw HTML from an inbound email is injected with `dangerouslySetInnerHTML` and NO
DOMPurify. The project HAS `sanitizeHTML` (used in ContratosTab) but it is not
applied here. An attacker emails the tenant an HTML message with
`<img onerror>` / `<script>`-equivalent payload → executes in the user's
authenticated session when they open it. Same pattern, unsanitized, at
`rrhh/documentos/_components/DocumentCard.tsx:150` (`doc.content_html`) — lower
risk if content is system-generated, but verify its provenance.

Fix: wrap both in `sanitizeHTML(...)`. Email bodies are attacker-controlled by
definition; never render them raw.

### M2 — JWT tokens stored in localStorage (XSS → full account takeover)
`frontend/src/app/(dashboard)/layout.tsx:40`, `login.test.tsx`, `ProfileMenu.tsx:65`

Access AND refresh tokens live in `localStorage`. Any XSS (e.g. M1) exfiltrates
both, including the 30-day refresh token. Note: the comment says tokens hydrate
from Electron `safeStorage` OR localStorage — in the packaged desktop app this
is acceptable; in the dev/web path it is the standard XSS-amplification risk.
Fix: prefer httpOnly cookies for web deployment, or document that web exposure
is out of scope and the product is desktop-only. At minimum, fixing M1 removes
the most direct XSS vector.

### M3 — DB restore shells out with attacker-influenced env, admin-only
`backend/app/api/v1/routes/admin.py` `/restore` (and `import-db`)

`psql` is invoked via `create_subprocess_exec` (good — no shell) with
`PGPASSWORD` from `settings.DATABASE_URL`. Args are fixed, content piped via
stdin, 100MB cap, `.sql` extension + magic-byte check, `require_role("admin")`,
rate-limited. This is reasonably hardened. Residual risk: the uploaded `.sql` is
fed to `psql` which will execute arbitrary SQL (by design of restore) — an admin
can run any SQL as the DB user, and the restore connects with DATABASE_URL's
role. Confirm that role is `pyme_app` (NOBYPASSRLS), NOT the bootstrap
superuser, or a malicious/compromised admin restore can disable RLS for all
tenants. Document the trust boundary; restore is inherently admin-privileged.

### M4 — `register` blocks remote by IP, but relies solely on `is_local_request`
`backend/app/api/v1/routes/auth.py:register`

Tenant+admin creation is gated by `is_local_request(request)` returning 404 for
non-local. If the app sits behind Cloudflare Tunnel / reverse proxy (as the
.env.example explicitly anticipates), `request.client.host` may be the proxy IP
(127.0.0.1 / private), making remote requests look local → anyone on the
internet could register tenants. Verify `is_local_request` accounts for
`X-Forwarded-For` correctly and that proxy headers are not trustable from the
public side.

---

## LOW / INFORMATIONAL

### L1 — Migration f-string SQL (not exploitable)
`0016_sec_rls.py`, `0025_pos_sessions.py`, `security_bootstrap.py`, `rls.py:76`
interpolate table/role names into DDL via f-strings. Values come from
`information_schema` / hardcoded constants / UUID-validated tenant — not user
input. No injection. Leave as-is; noted for completeness.

### L2 — CORS uses explicit allowlist (good)
`main.py:133-139` — `allow_origins` from `FRONTEND_URL.split(",")`,
`allow_credentials=True`, scoped methods/headers. No wildcard. Correct. Just
ensure `FRONTEND_URL` is never set to `*` in any deployment (with credentials,
that's a known footgun — but config doesn't default to it).

### L3 — `claude -p --dangerously-skip-permissions` subprocess
`backend/app/core/llm/claude_code.py` — prompt passed via stdin (not argv), uses
`create_subprocess_exec`, `_clean_env`, `_neutral_cwd`. No shell/arg injection.
The `--dangerously-skip-permissions` flag means the spawned Claude CLI can
freely touch the filesystem at `_neutral_cwd`; confirm that cwd is an isolated
sandbox dir, since prompt content is tenant/LLM-controlled. Hardening item only.

### L4 — Crypto reviewed, correct
`backup/crypto.py`: AES-256-GCM, fresh 12-byte nonce per encrypt
(`secrets.token_bytes`), 16-byte salt, PBKDF2-HMAC-SHA256 1M iterations, GCM tag
verified on decrypt. `certificate_storage.py`: Fernet for PFX+password, never
returns secret material via API, 200KB cap, password mandatory. Both sound. No
nonce reuse, no ECB, no static IV. Good.

### L5 — Password reset enumeration-safe
`forgot_password` always returns the same message regardless of user existence.
Good. Verify the reset-token table uses hashed tokens with short TTL (token
created via `secrets`, hashed with `hashlib` per imports — looks correct).

---

## Summary table

| ID | Sev | Issue | Exploitable now? |
|----|-----|-------|------------------|
| C1 | CRITICAL | RLS fail-open on unset tenant GUC | Yes, on any tenant-less DB path |
| H1 | HIGH | Scanner routes never set tenant GUC → RLS permissive + scope unenforced | Yes, if any scanner svc omits tenant filter |
| H2 | HIGH | `/refresh` rebuilds tokens from stale claims, no revocation, no rate limit | Yes (disabled users, leaked refresh) |
| M1 | MED | Stored XSS: Outlook email body rendered unsanitized | Yes |
| M2 | MED | JWT in localStorage amplifies any XSS | Conditional (web path) |
| M3 | MED | Admin restore runs arbitrary SQL; verify non-superuser role | Admin-only |
| M4 | MED | `register` local-only check may fail behind proxy | Conditional (proxy config) |
| L1-L5 | LOW | Migration f-strings, CORS, claude cwd, crypto OK, reset OK | No |
