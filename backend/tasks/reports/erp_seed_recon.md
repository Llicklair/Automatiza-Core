# ERP Seed / Function-Test Recon

Read-only reconnaissance for a mass DB-population + function-testing task.
Tenant id (single existing): `c5857aad-357d-471f-b0c0-64009dac0a5e`.
Python: `py -3.11` (the bare `python` alias is broken on this box; use `py -3.11`).
DB session: `from app.db.base import AsyncSessionLocal`.

---

## 1. EXISTING SEEDERS

| Script | Entities / tables created | Scale | Tenant target | DB role | Idempotent? | Run command |
|---|---|---|---|---|---|---|
| `scripts/seed_demo.py` | Client, Product, Invoice + InvoiceLine (issued+received), Employee, Payroll, Opportunity, Activity, BankTransaction | 7 clients, 8 products, ~13 issued + ~6 received invoices, 5 employees, 4×3=12 payrolls, 5 opportunities, ~6 activities, ~10 bank tx | Looks up `User.email == demo@automatizacore.com`, uses `user.tenant_id` (NOT the c585… tenant unless demo user maps there) | **runtime** (`settings.DATABASE_URL`, builds its own engine) | **NO** — appends on every run. Has `--reset` flag that deletes via `reset_tenant_data()` first. | `py -3.11 scripts/seed_demo.py` / `py -3.11 scripts/seed_demo.py --reset` |
| `scripts/seed_user_data.py` | All sections **via HTTP API** (not ORM) | — | Whichever user you log in as (`--email/--password`) | API/JWT (server's role) | Depends on API; mostly duplicates | `py -3.11 scripts/seed_user_data.py --email USER --password PASS [--base http://localhost:8080]` |
| `scripts/seed_advanced_workflow.py` | 1 `Workflow` (complex graph: trigger→skill→conditional→delay→approval→email) with ui_nodes/ui_edges | 1 workflow | `select(Tenant).limit(1)` (first tenant) | runtime (`AsyncSessionLocal`) | **NO** — adds a new workflow each run | `cd backend && py -3.11 -m scripts.seed_advanced_workflow` |
| `scripts/create_demo_workflows.py` | 3 `Workflow` rows (reasoning / deterministic / parallel) | 3 workflows | `select(Tenant).limit(1)` (first tenant) | runtime (`AsyncSessionLocal`) | **NO** — adds 3 more each run | `py -3.11 scripts/create_demo_workflows.py` |
| `scripts/inject_demo_credentials.py` | `TenantIntegration` (psd2/Nordigen mock, encrypted) | 1–few | Looks up `demo@automatizacore.com` user → tenant | runtime (`AsyncSessionLocal`) | **YES** — upserts (updates existing psd2 row, else inserts) | `py -3.11 scripts/inject_demo_credentials.py` |

Notes:
- `seed_demo.py` and the workflow seeders are **NOT idempotent** — re-running multiplies rows. Use `--reset` on seed_demo or pre-truncate.
- `seed_demo.py` keys off the **demo user**, not the c585… tenant. Confirm the demo user's tenant_id == c585… or the data lands in a different tenant.

---

## 2. TEST / SMOKE SCRIPTS

| Script | What it tests | Needs LLM? | Run command | Best for "test all domain functions"? |
|---|---|---|---|---|
| `scripts/full_system_test.py` | **DEPRECATED** (1394 LoC). HTTP sweep of ALL endpoints w/ inline fixtures. Auth + every domain CRUD. | Needs running server; LLM only if endpoints invoke agents | `py -3.11 scripts/full_system_test.py` (server on :8000) | **YES — broadest single-script coverage** of all domain HTTP functions, but deprecated/unmaintained |
| `scripts/test_all.py` | **DEPRECATED**. HTTP smoke w/ MockLLM: auth, AI tasks (billing/hr/crm/compliance/documents), workflows+executions, approvals, audit, scanner | MockLLM (no real LLM) but needs server on :8080 | `py -X utf8 scripts/test_all.py [--url http://localhost:8080]` | Broad, MockLLM-based; second choice |
| `scripts/test_agents.py` | **DEPRECATED**. Invokes each agent's compiled LangGraph directly (billing/hr/crm/banking/...) w/ happy + edge prompts | **YES — real LLM** (loads .env, forces off Gemini) | `py -3.11 scripts/test_agents.py [--agent billing] [--save out.json]` | Agent-level, LLM-dependent |
| `scripts/smoke_demo.py` | E2E happy path via HTTP: register→login→create client→product→invoice(line). Idempotent register. | Pure HTTP, no LLM | `py -3.11 scripts/smoke_demo.py` (server on :8080) | Narrow (billing path only) |
| `scripts/smoke_orchestrator.py` | Drives `orchestrator.ainvoke()` (Coordinador) with NL prompts, mono+multi-domain. **REAL DB side-effects**, SMTP mocked. Hardcoded `TENANT_ID=9cd49fbb-…`, `USER_ID=0d7e5ea1-…` | **YES — real LLM** | `py -3.11 scripts/smoke_orchestrator.py [--only X] [--skip Y]` | Tests the AI router end-to-end; LLM-heavy |
| `scripts/audit_domain_completeness.py` | Static cross-check of routing sync (VALID_DOMAINS vs DISPATCHER_MAP vs keyword maps in `agents/orchestrator/`). exit 0 clean / 1 asymmetry | **NO** — pure static file parse | `py -3.11 scripts/audit_domain_completeness.py` | No DB; routing-config audit only |

**Recommendation:** For "tests all domain functions" pick `full_system_test.py` (widest endpoint sweep) — but it's deprecated; the maintained equivalent is the pytest suite (`cd backend && pytest tests/test_e2e_happy_path.py -v`, plus the ~40 `tests/test_api_*.py`). For a **no-LLM, direct-service** population/verification, call the service-layer create functions in §4 directly (no server, no LLM).

---

## 3. DOMAIN → ENTITY MAP (`app/db/models/*.py`)

| Domain | File(s) | Main ORM entities (table) |
|---|---|---|
| auth/tenant | `auth.py` | Tenant(tenants), User(users), ClientPortalToken, PasswordResetToken, UserInvitation, TelemetryOptOut, TenantRegapStatus |
| billing | `billing.py` | InvoiceSeries, Invoice(invoices), InvoiceLine(invoice_lines), VerifactuRecord(verifactu_chain), VerifactuConfig, Quote(quotes), QuoteLine, RecurringInvoice(recurring_invoices), DocumentTemplate, DeliveryNote(delivery_notes) + lines |
| accounting | `accounting.py` | JournalEntry(journal_entries), JournalLine(journal_lines), BankTransaction(bank_transactions), FixedAsset(fixed_assets), AccountingPeriod, TenantCertificate, AeatPresentation(aeat_presentations) |
| crm | (crm/sales models) | Opportunity(opportunities), Activity(activities), Event(events), Reservation(reservations), Client(clients) |
| hr | (hr models) | Employee(employees), Payroll(payrolls), LeaveRequest(leave_requests), Attendance(attendance), JornadaRecord(jornada_records), HrDocument(hr_documents), Settlement(settlements) |
| recruitment | recruitment models | Candidate(candidates), RecruitmentPosition(recruitment_positions) |
| inventory/products | sales/inventory models | Product(products), ProductStock(product_stock), ProductLot(product_lots), StockMovement(stock_movements) |
| sales/orders | sales models | SalesOrder(sales_orders)+lines, PurchaseOrder(purchase_orders)+lines |
| pos | pos models | PosSession(pos_sessions), PosSessionLine(pos_session_lines) |
| treasury | treasury models | SepaRemittance(sepa_remittances)+orders |
| projects/tasks | `project_*` / task models | Project(projects), ProjectTask(project_tasks), Task(tasks) |
| documents | document models | TenantDocument(tenant_documents), DocumentEmbedding(document_embeddings), SignedDocument(signed_documents), GeneratedUi(generated_uis) |
| marketing/email_mkt | marketing models | MarketingCampaign(marketing_campaigns), MarketingProviderConfig, ScheduledPost(scheduled_posts)+metrics, SocialAccount(social_accounts) |
| workflows | workflow models | Workflow(workflows) + executions, PendingApproval(pending_approvals) |
| ai_employees | `ai_employees.py` | AIEmployee(ai_employees), EmployeeMemory(employee_memory), AgentSkill, TokenLedger, ActivityEntry(activity_feed), AgentExecutionTrace |
| misc | various | AlertLog, BackupRecord, Notification(notifications), IdempotencyKey, TenantIntegration, AutonomyPolicy, AuditLog, DomainEvent |

(Run `grep -rn '__tablename__' app/db/models/` for the exhaustive list — ~70 tables.)

---

## 4. SERVICE-LAYER CREATE FUNCTIONS (call directly to bulk-populate, no LLM)

All take `db: AsyncSession` and `tenant_id` unless noted. **Most `commit()` internally** (per-call commit), so bulk loops are simple but slower.

| Domain | file:function | Signature (key args) |
|---|---|---|
| **billing** | `app/services/billing/commands.py:create_invoice` | `create_invoice(client_id, payload_dict: dict, lines_data: list[dict], tenant_id, user_id, db)` — strips totals, computes them, consumes invoice number (advisory lock). Needs existing client_id. |
| billing | `…/commands.py:create_journal_entry` | `(db, tenant_id, *, date, description, reference_id, lines: list[dict {account_code,debit,credit}], invoice_id=None, payroll_id=None)` — must balance debit==credit; blocks if period locked |
| billing | `…/commands.py:create_fixed_asset` | `(db, tenant_id, data: dict)` |
| billing | `…/commands.py:create_recurring` | recurring invoice template |
| **crm** | `app/services/crm/commands.py:create_opportunity` | `(db, tenant_id, data: dict)` |
| crm | `…/crm/commands.py:create_activity` | `(db, tenant_id, data: dict)` |
| crm | `…/crm/commands.py:create_event` / `create_reservation` | `(db, tenant_id, data: dict)` |
| **sales/clients** | `app/services/sales/commands.py:create_client` | `(db, tenant_id, user_id, data: dict)` — dedup on NIF/email (ValueError), emits event |
| **inventory/products** | `app/services/sales/commands.py:create_product` | `(db, tenant_id, data: dict)` |
| inventory | `…/sales/commands.py:create_stock_movement` | `(db, tenant_id, product_id, data: dict {movement_type: entrada/salida/ajuste, quantity})` — mutates Product.stock_quantity, FEFO lot logic on salida |
| inventory | `app/services/inventory/warehouse_service.py:create_warehouse` | `(db, tenant_id, data)`; also `lot_service.create_lot/add_lot`, `stock_service.add_to_warehouse` |
| sales/orders | `…/sales/commands.py:create_sales_order` / `create_purchase_order` / `create_quote` / `create_albaran` | `(db, tenant_id, data)` |
| **hr** | `app/services/hr/commands.py:create_employee` | `create_employee(data: dict, tenant_id, db)` — **note arg order (data first, db last)**; dedup NIF (ValueError) |
| hr | `app/services/hr/_payroll.py:create_payroll` | `create_payroll(payload, tenant_id, db)` — payload is a Pydantic model (`.model_dump()`); arg order (payload, tenant_id, db). Also `create_payroll_auto`. |
| hr | `…/hr/commands.py:create_position` | `(db, tenant_id, payload: dict)` → returns dict (RecruitmentPosition) |
| hr | `…/hr/commands.py:create_leave_request` / `create_expense`; `finiquito.py:create_settlement` | various |
| **recruitment** | `app/agents/recruitment/tools.py:create_candidate` | `create_candidate(tenant_id: str, name, email="", phone="", position_id="")` — **AGENT TOOL: opens its own `AsyncSessionLocal()`, takes str args, returns a str message, NOT (db, dict).** No standalone service create_candidate exists. For bulk, insert `Candidate(...)` ORM directly or call this tool per-row. |
| **accounting** | (see billing create_journal_entry) + `app/services/billing/auto_accounting.py:create_invoice_journal_entry/create_payroll_journal_entry` | `(db, tenant_id, invoice|payroll)` |
| **aeat** | `app/services/aeat/presentation_service.py:create_presentation` | model presentations |
| **projects/tasks** | `app/services/project_service.py:create_project` | `(db, tenant_id, data: dict)` |
| projects | `app/services/project_service.py:create_task` | `(db, tenant_id, ...)` |
| **ai_employees** | `app/services/ai/employee_crud.py:create_employee` (AI), `:create_activity` | AI-employee records |
| **treasury** | `app/services/treasury/remittances.py:create_transfer_remittance` / `create_direct_debit_remittance` | SEPA |
| **marketing** | `app/services/marketing/provider_config.py:add_provider_config`; `zernio_client.py:create_post` | config / social post |
| **notifications** | `app/services/notifications.py:create_notification` | notification |

**BANKING — no plain create:** `app/services/banking/service.py` only has `list_transactions`, `sync_transactions(db, tenant_id, user_id)` (pulls from PSD2 provider), `reconcile/ignore/unreconcile_transaction`, `purge_demo_transactions`. To bulk-seed bank movements, insert `BankTransaction` ORM rows directly (as `seed_demo.py` does) — there is NO `create_bank_transaction(db, tenant_id, data)` service.

---

## 5. CURRENT DB STATE (live, read-only)

Connected via `AsyncSessionLocal`/engines from `settings`. Ran with `SET app.current_tenant` GUC.
**Both RUNTIME (DATABASE_URL / pyme_app, RLS) and ADMIN (ADMIN_DATABASE_URL / pyme_user) returned IDENTICAL counts and ZERO permission/RLS errors.** No table errored. RLS did not block the runtime role for counts.

| Entity (table) | Rows |
|---|---|
| tenants | 1 |
| users | 1 |
| clients | 1 |
| products | 0 |
| product_stock | 0 |
| stock_movements | 0 |
| invoices | 1 |
| invoice_lines | 1 |
| recurring_invoices | 0 |
| quotes | 0 |
| delivery_notes | 0 |
| employees | 0 |
| payrolls | 0 |
| leave_requests | 0 |
| attendance | 0 |
| opportunities | 0 |
| activities | 0 |
| events | 0 |
| reservations | 0 |
| bank_transactions | 0 |
| journal_entries | 1 |
| journal_lines | 3 |
| fixed_assets | 0 |
| candidates | 0 |
| recruitment_positions | 0 |
| sales_orders | 0 |
| purchase_orders | 0 |
| projects | 0 |
| project_tasks | 0 |
| tasks | 4 |
| tenant_documents | 4 |
| workflows | 5 |
| marketing_campaigns | 0 |
| scheduled_posts | 0 |
| pos_sessions | 0 |
| sepa_remittances | 0 |
| ai_employees | 10 |
| notifications | 0 |

Essentially an empty tenant: 1 client, 1 invoice, 1 journal entry, 5 workflows, 10 ai_employees, a few tasks/docs. Almost every business domain is at 0 — ideal for mass-seeding.

---

## BLOCKERS / FLAGS for the mass-seed script

1. **Single tenant id** `c5857aad-357d-471f-b0c0-64009dac0a5e`; only 1 user. Confirm `user_id` (needed by `create_invoice` and `create_client`) — query `SELECT id FROM users WHERE tenant_id='c585…'`.
2. **RLS is NOT a blocker for inserts via these services** — counts returned fine under pyme_app. But the services build their own session; if you open your own `AsyncSessionLocal()` and RLS is enforced on INSERT, you may need `SET app.current_tenant`. Test one insert first. The admin URL (pyme_user) bypasses RLS if needed.
3. **FK ordering:** invoices need a client_id; invoice journal entries need invoices; payrolls need employee_id; stock_movements need product_id; activities need opportunity_id+client_id. Seed in order: clients → products → employees → invoices → payrolls → opportunities → activities → stock_movements → journal_entries.
4. **Arg-order inconsistency (easy to trip on):**
   - `create_invoice(client_id, payload_dict, lines_data, tenant_id, user_id, db)`
   - `create_client(db, tenant_id, user_id, data)`
   - `create_employee(data, tenant_id, db)` ← data first, db last
   - `create_payroll(payload, tenant_id, db)` ← payload is a Pydantic model, not dict
   - Most others: `(db, tenant_id, data)`.
5. **No LLM dependency** in any §4 create function — pure DB. `create_candidate` (recruitment) is the exception in *shape* (agent tool, str args, own session) but still no LLM; for bulk prefer direct `Candidate(...)` ORM insert.
6. **No `create_bank_transaction` service** — insert `BankTransaction` ORM directly.
7. **Per-call commits:** most create_* commit individually → fine for correctness, slower for thousands of rows. For true mass volume, prefer direct ORM `db.add()` + bulk `flush/commit` (the pattern `seed_demo.py` uses) over per-row service calls.
8. **`python` alias broken** on this machine — use `py -3.11`.
