# Capacidades del LLM en AutomatizaCore

**Inventario completo de qué puede hacer el LLM por dominio.**
Fecha: 2026-05-06. Basado en auditoría estática (76 `@tool` en 29 archivos).

---

## Cómo funciona

El usuario manda una intención → orchestrator clasifica el dominio → cada agente es un grafo LangGraph con su propio set de tools → el LLM decide qué tool ejecutar y con qué argumentos → la tool corre contra la BD multi-tenant del usuario → respuesta de vuelta.

**Providers LLM soportados** (vía `core/llm_factory.py`): Anthropic (claude-sonnet-4-6), OpenAI (gpt-4o-mini), Groq, OpenRouter, Mock.
**Multi-tenant:** cada tool recibe `tenant_id`; las keys de API se almacenan encriptadas por tenant en `TenantLlmConfig`.

---

## Por dominio

### 💰 Billing (facturación) — 15 tools
- `create_invoice` — crear factura con líneas
- `update_invoice` / `update_invoice_status` — modificar factura, marcar como pagada/pendiente/cancelada
- `list_invoices(limit)` — listar pendientes
- `send_invoice_by_email(invoice_id, recipient)` — enviar por email
- `search_client(query)` — buscar cliente por NIF/nombre
- + tools internas de albarán, generación PDF, validadores

### 👥 HR (recursos humanos) — 7 tools
- `create_employee(...)` — alta de empleado
- `list_employees`
- `calculate_and_create_payroll(employee_id, month, year)` — calcular y crear nómina individual
- `generate_all_payrolls(month, year)` — **generar nóminas masivas del mes** ← capacidad estrella
- `list_payrolls`, `update_payroll`, `approve_payroll`

### 🏦 Banking — 4 tools
- `check_balances` — saldos de todas las cuentas
- `list_transactions(days_back)` — movimientos recientes
- `financial_summary(days_back)` — resumen ingreso/gasto
- `reconcile_transactions` — **conciliación automática contra facturas**

### 📒 Accounting (contabilidad) — 5 tools
- `create_journal_entry` — asiento contable
- `list_journal_entries`
- `get_account_balance(account_code)` — saldo cuenta concreta (ej. 430)
- `get_profit_loss_summary` — pérdidas y ganancias
- `list_fixed_assets` — inmovilizado

### 📄 Documents — 6 tools (2 propias + 4 shared)
- `classify_document` — clasificar tipo (factura/contrato/nómina/...)
- `search_documents_semantic(query)` — búsqueda RAG
- `create_document`, `list_tenant_documents`, `update_existing_document`, `get_document_content`

### 🤝 CRM — 5 tools
- `create_opportunity`, `list_opportunities`, `update_opportunity_stage`
- `qualify_leads` — **cualificación automática de leads con LLM**
- `create_client`

### 📧 Email — 3 tools
- `send_email`, `check_inbox`, `check_unread`

### 📊 Excel — 5 tools
- `import_excel`, `read_excel`, `modify_excel`
- `export_erp_data` — exportar datos del ERP a Excel
- `list_available_datasets`

### 📜 Compliance fiscal — 3 tools
- `check_fiscal_deadlines` — vencimientos modelo 303, 111, 200, etc.
- `check_boe_news` — novedades del BOE
- `fiscal_query` — consultas fiscales generales

### 🎯 Recruitment — 5 tools
- `create_position`, `list_positions`
- `process_cv` — **parseo automático de CVs**
- `list_candidates`, `update_candidate_status`

### 🤖 RAG (búsqueda en knowledge base) — 2 tools
- `search_documents`, `answer_from_documents` — Q&A sobre documentos del tenant

### 📢 Marketing — 1 tool
- `get_product_catalog`

### 🛠 Tools transversales (`agent_tools/`)
- Knowledge base: `get_tenant_knowledge`, `upsert_tenant_knowledge`, `delete_tenant_knowledge`
- AI employees: `create_ai_employee_from_description`

---

## Orchestrator: dispatching de intenciones

`POST /tasks` con `{domain, user_intent}` → orchestrator clasifica y enruta a uno de **11 dispatchers**: `accounting, banking, billing, chat, compliance, crm, documents, hr, misc, reports`.

Si pides "genera las nóminas de marzo" sin especificar dominio, el classifier LLM lo mapea a `hr` automáticamente (vocabulario en `MockChatModel._classify_domain`: `nomina/empleado/sueldo → hr`, `factura/cobro/cliente → billing`, `iva/fiscal → compliance`, `banco/saldo → banking`, etc.).

---

## Lo que NO puede hacer (sea consciente)

- **No tiene navegador web** — `check_boe_news` y `fiscal_query` operan sobre datos pre-cargados, no scrapean en vivo
- **No envía SMS/WhatsApp** — solo email
- **No firma facturas digitalmente** — VeriFactu está en BD pero no automatizado
- **No conecta con bancos reales** — `banking` opera sobre `BankTransaction` simulados (sync genera datos demo)
- **6 tools sin docstring** (en crm/email/recruitment) — el LLM puede invocarlas mal porque no sabe exactamente qué hacen. Ver audit doc, sección 5.
