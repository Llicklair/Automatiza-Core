# Repo skeleton (determinista, sin LLM)
_1681 archivos · 254421 loc · 11 directorios raíz._

## 🔗 Conectividad (grafo de imports internos)

**Hubs** (más importados — tocarlos arrastra a muchos):
- `frontend/src/lib/api.ts` ← 202 archivos
- `backend/app/db/models/models.py` ← 145 archivos
- `backend/app/db/base.py` ← 138 archivos
- `frontend/src/components/ui/button.tsx` ← 84 archivos
- `frontend/src/stores/toast.ts` ← 83 archivos
- `backend/app/core/dependencies.py` ← 66 archivos
- `frontend/src/lib/api/client.ts` ← 64 archivos
- `frontend/src/components/shared/PageContainer.tsx` ← 59 archivos
- `backend/app/db/models/billing.py` ← 48 archivos
- `frontend/src/lib/logger.ts` ← 47 archivos
- `frontend/src/components/shared/PageHeader.tsx` ← 45 archivos
- `frontend/src/stores/confirm.ts` ← 43 archivos
- `backend/app/middleware/rate_limit.py` ← 43 archivos
- `frontend/src/lib/utils.ts` ← 42 archivos
- `backend/app/db/models/crm.py` ← 41 archivos

**Más acoplados** (más dependencias internas salientes):
- `frontend/src/lib/api/index.ts` → 45 archivos
- `backend/app/db/models/__init__.py` → 25 archivos
- `frontend/src/app/(dashboard)/page.tsx` → 18 archivos
- `backend/app/db/models/models.py` → 15 archivos
- `frontend/src/app/(dashboard)/inventario/stock/page.tsx` → 15 archivos
- `backend/app/agents/documents/tools.py` → 14 archivos
- `frontend/src/app/(dashboard)/rrhh/empleados/page.tsx` → 14 archivos
- `backend/app/agents/orchestrator/dispatchers/__init__.py` → 13 archivos
- `frontend/src/app/(dashboard)/impuestos/ResumenPanel.tsx` → 13 archivos
- `frontend/src/app/(dashboard)/layout.tsx` → 13 archivos
- `backend/app/api/v1/routes/client_portal.py` → 12 archivos
- `frontend/src/app/(dashboard)/clientes/page.tsx` → 12 archivos
- `frontend/src/app/(dashboard)/configuracion/usuarios/page.tsx` → 11 archivos
- `frontend/src/app/(dashboard)/rrhh/gastos/page.tsx` → 11 archivos
- `backend/app/api/v1/routes/marketing.py` → 10 archivos

**⚠️ Ciclos de import** (2 grupos enredados — deuda estructural):
- `backend/app/services/ai/node_engine.py` ↔ `backend/app/services/ai/__init__.py`
- `frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizacionesCRUD.ts` ↔ `frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizaciones.ts`

## 🎯 Prioridad para el debate (señal determinista, no veredicto)

_Dónde mirar primero: blast-radius (←) + acoplamiento (→) + tamaño + churn (⟳ commits recientes) + ciclo. Es una guía de ATENCIÓN; el juicio de calidad es del consejo. `←`=cuántos lo importan, `→`=cuántos importa, `⟳`=cuántas veces cambió._

- **64** `backend/app/db/models/models.py` (←145 →15, 63 loc · ⟳6 · inest=0.09)
- **59** `backend/app/core/dependencies.py` (←66 →6, 162 loc · ⟳11 · inest=0.08)
- **57** `frontend/src/lib/api/client.ts` (←64 →3, 275 loc · ⟳12 · inest=0.04)
- **56** `backend/app/db/base.py` (←138 →2, 51 loc · ⟳7 · inest=0.01)
- **54** `backend/app/core/llm_factory.py` (←28 →3, 459 loc · ⟳19 · inest=0.1)
- **52** `backend/app/main.py` (←8 →8, 370 loc · ⟳30 · inest=0.5)
- **52** `frontend/src/lib/api.ts` (←202 →0, 11 loc · ⟳12 · inest=0.0)
- **51** `backend/app/db/models/billing.py` (←48 →1, 325 loc · ⟳11 · inest=0.02)
- **51** `backend/app/db/models/__init__.py` (←6 →25, 65 loc · ⟳19 · inest=0.81)
- **50** `backend/app/core/config.py` (←39 →0, 185 loc · ⟳33 · inest=0.0)
- **49** `backend/app/services/hr/queries.py` (←10 →7, 842 loc · ⟳9 · inest=0.41)
- **48** `backend/app/db/models/auth.py` (←39 →1, 170 loc · ⟳9 · inest=0.03)
- **48** `backend/app/db/models/hr.py` (←28 →1, 368 loc · ⟳11 · inest=0.03)
- **48** `backend/app/services/hr/commands.py` (←7 →8, 783 loc · ⟳10 · inest=0.53)
- **48** `backend/app/workers/tasks_scheduler.py` (←3 →9, 656 loc · ⟳25 · inest=0.75)
- **47** `backend/app/db/models/crm.py` (←41 →1, 97 loc · ⟳8 · inest=0.02)
- **46** `backend/app/db/models/inventory.py` (←28 →1, 168 loc · ⟳10 · inest=0.03)
- **46** `backend/app/services/reports/modelos_aeat.py` (←9 →3, 1081 loc · ⟳11 · inest=0.25)
- **46** `backend/app/agents/agent_tools/reports.py` (←12 →4, 339 loc · ⟳8 · inest=0.25)
- **46** `backend/app/agents/documents/tools.py` (←2 →14, 538 loc · ⟳18 · inest=0.88)

## (root)/  (8 archivos)
`ACCESO-REMOTO.md` (markdown, 111 loc) — Acceso remoto — decisión de producto y arquitectura
  symbols: # Acceso remoto — decisión de producto y arquitectura; ## 1. Qué es y cómo funciona (resumen); ## 2. Estado; ## 3. La mecánica del botón (Fase 2, cuando toque); ## 4. La decisión clave: ¿quiero ser el operador?; ## 5. Costes; ## 6. Recomendación / próximos pasos; ### Antes de dar de alta empleados no-admin (Fase 1.5)
`AGENTS.md` (markdown, 79 loc) — GitNexus — Code Intelligence
  symbols: # GitNexus — Code Intelligence; ## Always Do; ## When Debugging; ## When Refactoring; ## Never Do; ## Tools Quick Reference; ## Impact Risk Levels; ## Resources; ## Self-Check Before Finishing; ## CLI
`ARCHITECTURE.md` (markdown, 451 loc) — AutomatizaCore — Arquitectura Limpia & Principios de Código
  symbols: # AutomatizaCore — Arquitectura Limpia & Principios de Código; ## 0. Terminología canónica; ## 1. Capas del sistema — Fronteras estrictas; ### 1.1 Tipos de Service — Domain vs Infra; ## 2. Contrato del módulo agente; ### Cómo se invoca un agente; # patrón real de dispatch (agents/orchestrator/dispatchers/<domain>.py); # el dispatcher normaliza el result_state a AgentResult; # agents/base.py — usar siempre este tipo de retorno; ## 3. Aislamiento entre agentes — Prohibido el acoplamiento directo; # ❌ NUNCA: un agente importando herramientas de otro agente; # ✅ CORRECTO: la coordinación entre dominios la hace el Coordinador, no un agente.
`CLAUDE.md` (markdown, 217 loc) — AutomatizaCore — Project Rules
  symbols: # AutomatizaCore — Project Rules; ## Core Principles; ## Workflow Orchestration; ## Task Management; ## Architecture Rules (enforced — see ARCHITECTURE.md for full details); ### Layer boundaries; ### Agent structure (mandatory); ### Naming: "orchestrator" vs "coordinator"; ### Frontend rules; ### Agent communication; ### Commit discipline; # GitNexus — Code Intelligence
`GITNEXUS.md` (markdown, 46 loc) — GitNexus — Full Reference
  symbols: # GitNexus — Full Reference; ## Tools; ## Impact Risk Levels; ## Workflows; ## Resources; ## CLI
`MARKETING.md` (markdown, 93 loc) — AutomatizaCore — Mensajes de marketing canónicos
  symbols: # AutomatizaCore — Mensajes de marketing canónicos; ## Promesa central; ## Definición de "datos de negocio"; ## Tiers de pricing; ## Posicionamiento competitivo; ## SLA tier; ## Compromisos sobre IA; ## Plataforma soportada en v1; ## Punto de contacto privacidad
`README.md` (markdown, 794 loc) — AutomatizaCore
  symbols: # AutomatizaCore; ## Índice; ## Qué es y para quién; ## Capacidades; ### ERP funcional; ### Capa IA — Lo que nos diferencia; ### Plataforma; ### Desktop (Electron); ## Modelo local-first (con matices honestos); ### Lo que sí es local; ### Lo que NO es local; ### Cuándo importa el matiz
`SCOPE.md` (markdown, 358 loc) — AutomatizaCore — Scope de Producto v1
  symbols: # AutomatizaCore — Scope de Producto v1; ## 0. Visión y diferenciación; ### Qué es; ### Para quién; ### Por qué existe; ### Riesgo competitivo; ## 1. Capacidades v1; ### Facturación y ventas; ### Recursos Humanos; ### Control horario y gestión de jornadas; ### CRM y clientes; ### Banca y contabilidad

## .claude/  (12 archivos)
`.claude/agents/code-reviewer.md` (markdown, 65 loc) — Revisor general adversarial
  symbols: # Revisor general adversarial; ## Qué revisar, en orden — pega la SALIDA REAL, no la parafrasees; ### 1. ¿Corre y pasan las puertas de CI del área tocada?; ### 2. Límites de arquitectura (CLAUDE.md) — violarlos es REJECT; ### 3. Seguridad (este repo tiene test_security_hardening*); ### 4. Correctitud y casos borde; ## Apóyate en el grafo (opcional); ## Formato del veredicto (siempre)
`.claude/agents/fiscal-reviewer.md` (markdown, 70 loc) — Revisor fiscal adversarial
  symbols: # Revisor fiscal adversarial; ## Postura (no negociable); ## Línea roja (rechazo automático, sin discusión); ## Qué revisar, en orden; ## Apóyate en el grafo (opcional); ## Formato del veredicto (siempre)
`.claude/settings.json` (json, 93 loc)
  symbols: key: permissions
`.claude/skills/code-review.md` (markdown, 58 loc) — Lightweight Code Review
  symbols: # Lightweight Code Review; ## When to Use; ## When to Skip; ## Process; ## Integration Point
`.claude/skills/cuadre/SKILL.md` (markdown, 76 loc) — /cuadre — el bucle que dice "no" antes de descuadrar a un cliente
  symbols: # /cuadre — el bucle que dice "no" antes de descuadrar a un cliente; ## Rutas fiscales que vigila (el "radio de visión"); ## Movimientos (lo que haces en cada turno); ### 1. DISCOVERY — encuentra el trabajo tú mismo; ### 2. HANDOFF — delega aislado; ### 3. VERIFICATION — el que dice "no"; ### 4. PERSISTENCE — la memoria fuera del chat; ### 5. SCHEDULING / la puerta humana (lo que NO automatizas); ## Topes (ponlos siempre, asume que algo girará en vano de noche); ## Salida final al usuario (cada pasada)
`.claude/skills/gitnexus/gitnexus-cli/SKILL.md` (markdown, 83 loc) — GitNexus CLI Commands
  symbols: # GitNexus CLI Commands; ## Commands; ### analyze — Build or refresh the index; ### status — Check index freshness; ### clean — Delete the index; ### wiki — Generate documentation from the graph; ### list — Show all indexed repos; ## After Indexing; ## Troubleshooting
`.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` (markdown, 90 loc) — Debugging with GitNexus
  symbols: # Debugging with GitNexus; ## When to Use; ## Workflow; ## Checklist; ## Debugging Patterns; ## Tools; ## Example: "Payment endpoint returns 500 intermittently"
`.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` (markdown, 79 loc) — Exploring Codebases with GitNexus
  symbols: # Exploring Codebases with GitNexus; ## When to Use; ## Workflow; ## Checklist; ## Resources; ## Tools; ## Example: "How does payment processing work?"
`.claude/skills/gitnexus/gitnexus-guide/SKILL.md` (markdown, 65 loc) — GitNexus Guide
  symbols: # GitNexus Guide; ## Always Start Here; ## Skills; ## Tools Reference; ## Resources Reference; ## Graph Schema
`.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` (markdown, 98 loc) — Impact Analysis with GitNexus
  symbols: # Impact Analysis with GitNexus; ## When to Use; ## Workflow; ## Checklist; ## Understanding Output; ## Risk Assessment; ## Tools; ## Example: "What breaks if I change validateUser?"
`.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` (markdown, 122 loc) — Refactoring with GitNexus
  symbols: # Refactoring with GitNexus; ## When to Use; ## Workflow; ## Checklists; ### Rename Symbol; ### Extract Module; ### Split Function/Service; ## Tools; ## Risk Rules; ## Example: Rename `validateUser` to `authenticateUser`
`.claude/skills/ronda/SKILL.md` (markdown, 80 loc) — /ronda — el bucle que patrulla todo el proyecto y dice "no"
  symbols: # /ronda — el bucle que patrulla todo el proyecto y dice "no"; ## Movimientos; ### 1. DISCOVERY — encuentra el trabajo tú mismo; ### 2. ROUTING + HANDOFF — el juez correcto por área, aislado; ### 3. VERIFICATION — el que dice "no"; ### 4. PERSISTENCE — memoria fuera del chat; ### 5. SCHEDULING / puerta humana — lo que NO automatizas; ## Topes (asume que algo girará en vano de noche); ## Las cuatro deudas silenciosas (vigílalas tú, que el bucle no las ve); ## Salida final al usuario (cada pasada)

## .github/  (3 archivos)
`.github/dependabot.yml` (yaml, 79 loc)
  symbols: version:; updates:
`.github/workflows/ci.yml` (yaml, 276 loc)
  symbols: name:; on:; env:; jobs:
`.github/workflows/release.yml` (yaml, 72 loc)
  symbols: name:; on:; env:; jobs:

## backend/  (945 archivos)
`backend/.vscode/settings.json` (json, 5 loc)
  symbols: key: python.terminal.activateEnvironment; key: python.terminal.useEnvFile
`backend/app/__init__.py` (python, 1 loc)
`backend/app/agents/__init__.py` (python, 1 loc)
`backend/app/agents/accounting/__init__.py` (python, 4 loc)
  imports: app
  → usa: backend/app/agents/accounting/agent.py
`backend/app/agents/accounting/agent.py` (python, 109 loc) — Accounting agent — LangGraph graph for accounting and journal entries
  symbols: async def accounting_agent_node(state); def accounting_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph
  → usa: backend/app/agents/agent_tools/reports.py, backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/accounting/prompts.py, backend/app/agents/accounting/tools.py, backend/app/agents/tenant_context.py
`backend/app/agents/accounting/prompts.py` (python, 37 loc)
`backend/app/agents/accounting/tools.py` (python, 302 loc) — Herramientas de contabilidad para el agente de asientos y libro diario
  symbols: async def create_journal_entry(tenant_id, description, entry_date, lines); async def list_journal_entries(tenant_id, date_from, date_to, account_code, limit); async def get_account_balance(tenant_id, account_code, date_to); async def get_profit_loss_summary(tenant_id, date_from, date_to); async def list_fixed_assets(tenant_id, status)
  imports: app, datetime, decimal, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/shared/validators/billing.py, backend/app/db/base.py, backend/app/db/models/accounting.py
`backend/app/agents/agent_tools/__init__.py` (python, 2 loc)
`backend/app/agents/agent_tools/ai_team.py` (python, 187 loc) — Herramienta para crear empleados IA desde descripción en lenguaje natural…
  symbols: async def create_ai_employee_from_description(tenant_id, description)
  imports: app, json, langchain_core, logging, uuid
  → usa: backend/app/core/llm_factory.py, backend/app/db/base.py, backend/app/db/models/ai_employees.py
`backend/app/agents/agent_tools/clients.py` (python, 58 loc) — Shared client lookup tools…
  symbols: async def search_client(tenant_id, query); async def _search_client_async(tenant_id, query)
  imports: app, langchain_core, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/agents/agent_tools/documents.py` (python, 299 loc) — Herramientas compartidas para que los agentes IA lean y modifiquen documentos del Escanear (TenantDocument) en la BD local
  symbols: def _normalize_category(category); async def create_document(tenant_id, file_name, content, category); async def list_tenant_documents(tenant_id, category, limit, offset); async def update_existing_document(tenant_id, document_id, new_content, append); async def get_document_content(tenant_id, document_id)
  imports: app, datetime, langchain_core, logging, os, sqlalchemy, uuid
  → usa: backend/app/agents/agent_tools/reports.py, backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/agents/agent_tools/knowledge.py` (python, 101 loc) — Herramientas para gestionar la memoria a largo plazo (TenantKnowledge)…
  symbols: async def get_tenant_knowledge(tenant_id, category); async def delete_tenant_knowledge(tenant_id, key); async def upsert_tenant_knowledge(tenant_id, key, value, category)
  imports: app, langchain_core, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/agents/agent_tools/memory.py` (python, 200 loc) — Tools de memoria persistente para AIEmployee…
  symbols: async def _employee_or_none(db, tenant_id, employee_id); async def remember(tenant_id, employee_id, key, value, importance); async def recall(tenant_id, employee_id, key); async def recall_all(tenant_id, employee_id, limit)
  imports: __future__, app, json, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/ai_employees.py
`backend/app/agents/agent_tools/reports.py` (python, 339 loc) — Tool compartida para que los agentes IA generen informes PDF profesionales…
  symbols: def _resolve_upload_dir(category); def _slugify(text); async def create_pdf_report(tenant_id, report, category); async def create_pdf_text_report(tenant_id, title, body, author, subtitle, category)
  imports: __future__, app, datetime, json, langchain_core, logging, os, pydantic, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/db/models/models.py, backend/app/services/pdf_reports/agent_report.py
`backend/app/agents/agent_tools/semantic_search.py` (python, 156 loc) — Búsqueda semántica sin pgvector: cálculo coseno en Python…
  symbols: def _cosine_distance(a, b); async def cosine_topk(db); def similarity_from_distance(distance); def is_missing_table_or_extension(exc)
  imports: __future__, app, collections, logging, math, sqlalchemy, uuid
  → usa: backend/app/db/models/embeddings.py
`backend/app/agents/banking/__init__.py` (python, 24 loc) — Banking agent package…
  → usa: backend/app/agents/banking/agent.py, backend/app/agents/banking/tools.py
`backend/app/agents/banking/_account_tools.py` (python, 72 loc) — Banking agent — account balance tools
  symbols: async def check_balances(tenant_id); async def _check_balances_async(tenant_id)
  imports: app, langchain_core, logging
  → usa: backend/app/agents/banking/_psd2_helpers.py, backend/app/services/banking/psd2.py
`backend/app/agents/banking/_psd2_helpers.py` (python, 78 loc) — Banking agent — datos demo y umbrales de alerta…
`backend/app/agents/banking/_reconciliation_tools.py` (python, 59 loc) — Banking agent — transaction reconciliation tool (delega en el servicio)
  symbols: async def reconcile_transactions(tenant_id, tolerance_days, tolerance_amount); async def _reconcile_transactions_async(tenant_id)
  imports: app, langchain_core, logging, uuid
  → usa: backend/app/db/base.py, backend/app/services/autonomy_gate.py
`backend/app/agents/banking/_transaction_tools.py` (python, 166 loc) — Banking agent — transaction listing and financial summary tools
  symbols: async def list_transactions(tenant_id, days_back); async def _list_transactions_async(tenant_id, days_back); async def financial_summary(tenant_id, days_back); async def _financial_summary_async(tenant_id, days_back)
  imports: app, datetime, json, langchain_core, logging
  → usa: backend/app/agents/banking/_psd2_helpers.py, backend/app/core/llm_factory.py, backend/app/services/banking/psd2.py
`backend/app/agents/banking/agent.py` (python, 79 loc) — Banking agent node + LangGraph graph builder
  symbols: async def banking_agent_node(state); def banking_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph, logging
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/banking/prompts.py, backend/app/agents/banking/tools.py
`backend/app/agents/banking/prompts.py` (python, 6 loc) — System prompts for the banking agent
  imports: app
  → usa: backend/app/prompts/__init__.py
`backend/app/agents/banking/tools.py` (python, 46 loc) — Banking agent tools re-export facade…
  imports: app
  → usa: backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/knowledge.py, backend/app/agents/agent_tools/reports.py, backend/app/agents/banking/_account_tools.py, backend/app/agents/banking/_reconciliation_tools.py, backend/app/agents/banking/_transaction_tools.py, backend/app/agents/tenant_context.py
`backend/app/agents/base.py` (python, 25 loc)
  symbols: class AgentState
  imports: langgraph, typing
`backend/app/agents/billing/__init__.py` (python, 28 loc) — Billing agent package…
  → usa: backend/app/agents/billing/agent.py, backend/app/agents/billing/tools.py
`backend/app/agents/billing/_albaran_tools.py` (python, 141 loc) — Delivery note (albarán) tools for the billing agent
  symbols: async def list_albaranes(tenant_id, status); async def create_albaran(tenant_id, client_name, lines_json, albaran_date, notes)
  imports: app, datetime, decimal, json, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/billing.py, backend/app/agents/billing/_client_tools.py
`backend/app/agents/billing/_client_tools.py` (python, 72 loc) — Client resolution helper for the billing agent…
  symbols: async def _resolve_client(tenant_id, client_name, client_nif)
  imports: app, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/agents/billing/_invoice_create_async.py` (python, 231 loc) — Core async logic for invoice creation…
  symbols: async def _create_invoice_async(tenant_id, client_name, concept, amount_base_str, vat_rate, invoice_date_str, client_nif, notes, issuer_name, issuer_nif, issuer_address, issuer_email)
  imports: app, datetime, decimal, logging, sqlalchemy, uuid
  → usa: backend/app/agents/shared/validators/billing.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/agents/billing/_client_tools.py, backend/app/agents/billing/_invoice_pdf_tools.py, backend/app/agents/billing/_invoice_validators.py
`backend/app/agents/billing/_invoice_pdf_tools.py` (python, 113 loc) — PDF generation and template helpers for invoices
  symbols: async def _load_invoice_template(tenant_id); async def _generate_and_save_invoice_pdf(tenant_id, invoice, invoice_line, client, issuer_name, issuer_nif, issuer_address, issuer_email, theme_config)
  imports: app, logging, os, uuid
  → usa: backend/app/core/config.py, backend/app/db/base.py, backend/app/db/models/billing.py, backend/app/db/models/models.py
`backend/app/agents/billing/_invoice_query_tools.py` (python, 166 loc) — Invoice query and delivery tools (read operations + email)…
  symbols: async def _list_invoices_async(tenant_id, limit); async def _send_invoice_by_email_async(tenant_id, invoice_id, recipient_email); async def list_invoices(tenant_id, limit); async def send_invoice_by_email(tenant_id, invoice_id, recipient_email)
  imports: app, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/agents/billing/_invoice_tools.py` (python, 46 loc) — Invoice tools — re-export facade…
  → usa: backend/app/agents/billing/_invoice_create_async.py, backend/app/agents/billing/_invoice_pdf_tools.py, backend/app/agents/billing/_invoice_query_tools.py, backend/app/agents/billing/_invoice_write_tools.py
`backend/app/agents/billing/_invoice_validators.py` (python, 22 loc) — Shared parsing helpers for invoice agent tools
  symbols: def parse_amount_str(raw)
  imports: decimal, re
`backend/app/agents/billing/_invoice_write_tools.py` (python, 318 loc) — Invoice write tools: update_status, update, and the create_invoice @tool…
  symbols: async def _update_invoice_status_async(tenant_id, invoice_id, new_status); async def _update_invoice_async(tenant_id, invoice_id, concept, amount_base_str, vat_rate, notes); async def create_invoice(tenant_id, client_name, concept, amount_base, vat_rate, invoice_date, client_nif, notes, issuer_name, issuer_nif, issuer_address, issuer_email); async def update_invoice_status(tenant_id, invoice_id, new_status); async def update_invoice(tenant_id, invoice_id, concept, amount_base, vat_rate, notes)
  imports: app, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/agents/billing/_invoice_create_async.py, backend/app/agents/billing/_invoice_validators.py
`backend/app/agents/billing/agent.py` (python, 90 loc) — Billing agent — LangGraph graph definition and node logic
  symbols: async def billing_agent_node(state); def billing_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/billing/prompts.py, backend/app/agents/billing/tools.py
`backend/app/agents/billing/prompts.py` (python, 6 loc) — Billing agent prompt constants
  imports: app
  → usa: backend/app/prompts/__init__.py
`backend/app/agents/billing/tools.py` (python, 74 loc) — Billing agent tool definitions — re-export facade…
  imports: app
  → usa: backend/app/agents/agent_tools/clients.py, backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/knowledge.py, backend/app/agents/agent_tools/reports.py, backend/app/agents/billing/_albaran_tools.py, backend/app/agents/billing/_client_tools.py, backend/app/agents/billing/_invoice_tools.py, backend/app/agents/tenant_context.py
`backend/app/agents/compliance/__init__.py` (python, 24 loc) — Compliance agent package…
  → usa: backend/app/agents/compliance/agent.py, backend/app/agents/compliance/tools.py
`backend/app/agents/compliance/agent.py` (python, 71 loc) — Compliance agent — LangGraph graph definition and node logic
  symbols: async def compliance_agent_node(state); def compliance_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/compliance/prompts.py, backend/app/agents/compliance/tools.py
`backend/app/agents/compliance/prompts.py` (python, 6 loc) — System prompts for the compliance agent
  imports: app
  → usa: backend/app/prompts/__init__.py
`backend/app/agents/compliance/tools.py` (python, 299 loc) — Compliance agent — tools: vencimientos fiscales, BOE y consultas RAG
  symbols: async def check_fiscal_deadlines(days_ahead, tenant_id); async def check_boe_news(tenant_id); async def _search_tenant_docs(tenant_id, question); async def fiscal_query(tenant_id, question); async def check_quarter_preventive(tenant_id, quarter, year)
  imports: __future__, app, json, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/knowledge.py, backend/app/agents/agent_tools/reports.py, backend/app/core/llm_factory.py, backend/app/core/prompt_sanitizer.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/integrations/boe_scraper.py, backend/app/agents/tenant_context.py
`backend/app/agents/crm/__init__.py` (python, 24 loc) — CRM agent package…
  → usa: backend/app/agents/crm/agent.py, backend/app/agents/crm/tools.py
`backend/app/agents/crm/agent.py` (python, 71 loc) — CRM agent — LangGraph graph definition and node logic
  symbols: async def crm_agent_node(state); def crm_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/crm/prompts.py, backend/app/agents/crm/tools.py
`backend/app/agents/crm/prompts.py` (python, 25 loc) — System prompts for the CRM agent
`backend/app/agents/crm/tools.py` (python, 308 loc) — Herramientas del agente CRM
  symbols: async def list_opportunities(tenant_id, stage); async def _list_opportunities_async(tenant_id, stage); async def create_opportunity(tenant_id, client_nif, title, expected_value, stage); async def _create_opportunity_async(tenant_id, client_nif, title, expected_value, stage); async def update_opportunity_stage(tenant_id, opportunity_id, new_stage, notes); async def _update_opportunity_stage_async(tenant_id, opportunity_id, new_stage, notes); async def qualify_leads(tenant_id); async def _qualify_leads_async(tenant_id); async def create_client(tenant_id, name, nif, email, phone, address, city, postal_code, client_type)
  imports: app, datetime, langchain_core, sqlalchemy, uuid
  → usa: backend/app/agents/agent_tools/clients.py, backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/reports.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/agents/tenant_context.py
`backend/app/agents/documents/__init__.py` (python, 22 loc) — Documents agent package…
  → usa: backend/app/agents/documents/agent.py, backend/app/agents/documents/tools.py
`backend/app/agents/documents/agent.py` (python, 71 loc) — Documents agent — LangGraph graph definition and node logic
  symbols: async def documents_agent_node(state); def documents_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/documents/prompts.py, backend/app/agents/documents/tools.py
`backend/app/agents/documents/prompts.py` (python, 6 loc) — System prompts for the documents agent
  imports: app
  → usa: backend/app/prompts/__init__.py
`backend/app/agents/documents/tools.py` (python, 538 loc) — Herramientas del agente de documentos
  symbols: class ClassifiedDocument; async def import_invoice_document(tenant_id, document_id, confirm, apply_stock); async def classify_document(tenant_id, document_id); async def _load_doc_and_extract_text(tenant_id, document_id); async def _link_client_from_nif(tenant_id, primary_nif, key_entities); async def _store_embeddings(tenant_id, document_id, raw_text, parsed_doc); async def _update_doc_status(document_id, raw_text); async def _emit_document_processed(tenant_id, document_id, classified); async def _classify_with_llm(raw_text, rule_result); async def _classify_document_async(tenant_id, document_id); async def search_documents_semantic(tenant_id, query, limit); async def _search_documents_semantic_async(tenant_id, query, limit)
  imports: app, json, langchain_core, logging, os, pydantic, re, sqlalchemy, uuid
  → usa: backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/knowledge.py, backend/app/core/llm_factory.py, backend/app/core/prompt_sanitizer.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/db/models/embeddings.py, backend/app/db/models/models.py, backend/app/prompts/__init__.py, backend/app/services/documents/classifier.py (+4)
`backend/app/agents/email/__init__.py` (python, 15 loc) — Email agent package
  → usa: backend/app/agents/email/agent.py, backend/app/agents/email/tools.py
`backend/app/agents/email/_provider_tools.py` (python, 279 loc) — Dynamic tool factory for email providers (Gmail, Outlook, IMAP/SMTP)…
  symbols: def build_real_tools(providers, imap_creds, default_provider)
  imports: app, langchain_core, logging
  → usa: backend/app/services/email/sender.py, backend/app/services/email/service.py
`backend/app/agents/email/agent.py` (python, 192 loc) — Agente gestor de correos electrónicos…
  symbols: class EmailAgentResult {__init__}; def _build_provider_note(providers, available_names, is_mock); def _build_graph(tools_list, mode_note); async def run_email_agent(user_intent, tenant_id, task_id)
  imports: app, datetime, langchain_core, langgraph, logging
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/services/email/credentials.py, backend/app/agents/email/_provider_tools.py, backend/app/agents/email/prompts.py, backend/app/agents/email/tools.py
`backend/app/agents/email/prompts.py` (python, 32 loc) — System prompts for the email agent
  symbols: def build_system_prompt(mode_note, tenant_id)
`backend/app/agents/email/tools.py` (python, 147 loc) — Herramientas del agente de correo electrónico…
  symbols: def check_inbox(tenant_id, max_results); def check_unread(tenant_id, max_results); def send_email(tenant_id, to, subject, body, attachment_ids, confirm); def build_tools_list(real_check_fn, real_unread_fn, real_send_fn, real_reply_fn, real_markread_fn)
  imports: app, langchain_core, logging
  → usa: backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/knowledge.py
`backend/app/agents/excel/__init__.py` (python, 25 loc) — Excel agent package…
  → usa: backend/app/agents/excel/agent.py, backend/app/agents/excel/tools.py
`backend/app/agents/excel/_export_tools.py` (python, 144 loc) — ERP data export tools for the Excel agent…
  symbols: async def export_erp_data(tenant_id, datasets, user_request); async def _export_erp_data_async(tenant_id, datasets_str, user_request); async def list_available_datasets(tenant_id); async def _list_available_datasets_async(tenant_id)
  imports: app, datetime, langchain_core, logging, os, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/tenant.py, backend/app/agents/excel/_fetchers.py, backend/app/agents/excel/_writer.py
`backend/app/agents/excel/_fetchers.py` (python, 231 loc) — DB fetchers for the Excel agent…
  symbols: async def _fetch_invoices(tenant_id); async def _fetch_clients(tenant_id); async def _fetch_employees(tenant_id); async def _fetch_payrolls(tenant_id); async def _fetch_products(tenant_id); async def _fetch_bank(tenant_id); def _detect_datasets(intent)
  imports: app, pandas, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/accounting.py, backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/db/models/inventory.py
`backend/app/agents/excel/_import_tools.py` (python, 228 loc) — Excel import tools for the Excel agent…
  symbols: async def _load_excel_doc(tenant_id, document_id); def _detect_import_target(sheet_title); def _map_excel_columns(headers, config); async def _import_rows_to_db(rows, col_mapping, config, model_cls, tenant_id); async def import_excel(tenant_id, document_id, target, sheet_name); async def _import_excel_async(tenant_id, document_id, target, sheet_name)
  imports: app, langchain_core, logging, openpyxl, os, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/db/models/inventory.py, backend/app/db/models/tenant.py
`backend/app/agents/excel/_modify_tools.py` (python, 175 loc) — Excel modification and reading tools for the Excel agent…
  symbols: def _parse_mods_json(modifications_json); def _apply_mods_to_workbook(wb, mods, default_sheet); async def modify_excel(tenant_id, document_id, modifications, sheet_name); async def _modify_excel_async(tenant_id, document_id, modifications_json, default_sheet); async def read_excel(tenant_id, document_id, sheet_name, max_rows); async def _read_excel_async(tenant_id, document_id, sheet_name, max_rows)
  imports: app, json, langchain_core, logging, openpyxl, os, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/tenant.py, backend/app/agents/excel/_import_tools.py
`backend/app/agents/excel/_writer.py` (python, 75 loc) — Excel file writer utilities for the Excel agent…
  symbols: def _hex_to_lighter(hex_color, factor); def _write_excel(sheets, output_path, theme)
  imports: openpyxl, os, pandas
`backend/app/agents/excel/agent.py` (python, 80 loc) — Agente de Excel — Autónomo con LangGraph…
  symbols: async def excel_agent_node(state); def excel_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/excel/prompts.py, backend/app/agents/excel/tools.py
`backend/app/agents/excel/prompts.py` (python, 6 loc) — Prompt loading for the Excel agent
  imports: app
  → usa: backend/app/prompts/__init__.py
`backend/app/agents/excel/tools.py` (python, 59 loc) — Excel agent tool definitions — re-export facade…
  imports: app, os
  → usa: backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/knowledge.py, backend/app/agents/agent_tools/reports.py, backend/app/agents/excel/_export_tools.py, backend/app/agents/excel/_import_tools.py, backend/app/agents/excel/_modify_tools.py, backend/app/agents/tenant_context.py
`backend/app/agents/hr/__init__.py` (python, 29 loc) — HR agent package…
  → usa: backend/app/agents/hr/agent.py, backend/app/agents/hr/tools.py
`backend/app/agents/hr/_employee_tools.py` (python, 120 loc) — HR agent — employee management tools (thin wrappers over services/hr)
  symbols: async def list_employees(tenant_id); async def _list_employees_async(tenant_id); async def create_employee(tenant_id, name, nif, base_salary, role, department, email, irpf_rate); async def _create_employee_async(tenant_id, name, nif, base_salary, role, department, email, irpf_rate)
  imports: app, langchain_core, logging, uuid
  → usa: backend/app/db/base.py
`backend/app/agents/hr/_payroll_calc.py` (python, 361 loc) — HR agent — payroll calculation tools (individual + bulk)
  symbols: async def calculate_and_create_payroll(tenant_id, nif, month, year, deductions); async def _create_payroll_async(tenant_id, nif, month, year, deductions); async def generate_all_payrolls(tenant_id, month, year); async def _generate_all_payrolls_async(tenant_id, month, year)
  imports: app, calendar, datetime, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/hr/_payroll_pdf.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/hr/queries.py
`backend/app/agents/hr/_payroll_crud.py` (python, 312 loc) — HR agent — payroll CRUD tools (update, approve, list)
  symbols: async def update_payroll(tenant_id, payroll_id, base_salary, deductions, notes); async def _update_payroll_async(tenant_id, payroll_id, base_salary_str, deductions_str, notes); async def approve_payroll(tenant_id, payroll_id, approve_all, month, year); async def _approve_payroll_async(tenant_id, payroll_id, approve_all, month, year); async def list_payrolls(tenant_id, month, year, status_filter); async def _list_payrolls_async(tenant_id, month, year, status_filter)
  imports: app, calendar, datetime, decimal, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/shared/validators/billing.py, backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/agents/hr/_payroll_pdf.py` (python, 92 loc) — HR agent — payroll PDF generation helper
  symbols: async def _generate_and_save_payroll_pdf(tenant_id, employee, payroll_numbers, start_date, end_date, month, year)
  imports: app, datetime, logging, os, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/agents/hr/_payroll_tools.py` (python, 28 loc) — HR agent — payroll tools re-export facade…
  imports: app
  → usa: backend/app/agents/hr/_payroll_calc.py, backend/app/agents/hr/_payroll_crud.py, backend/app/agents/hr/_payroll_pdf.py
`backend/app/agents/hr/_schedule_tools.py` (python, 110 loc) — Tool de propuesta y aplicación de horarios de trabajo (gateada por autonomía)
  symbols: def _summary(kwargs); async def propose_schedule(tenant_id, schedules, rationale)
  imports: app, datetime, langchain_core, logging, re, sqlalchemy, typing, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/hr.py, backend/app/db/models/models.py, backend/app/services/autonomy_gate.py
`backend/app/agents/hr/agent.py` (python, 130 loc) — HR agent — agent definition, graph nodes, and LLM orchestration
  symbols: async def hr_agent_node(state); def hr_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph, logging
  → usa: backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/knowledge.py, backend/app/agents/agent_tools/reports.py, backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/hr/prompts.py, backend/app/agents/hr/tools.py, backend/app/agents/tenant_context.py
`backend/app/agents/hr/prompts.py` (python, 52 loc) — HR agent — system prompts and prompt templates
  symbols: def build_system_prompt(tenant_id)
  imports: datetime
`backend/app/agents/hr/tools.py` (python, 31 loc) — HR agent — tool functions re-export facade…
  imports: app
  → usa: backend/app/agents/hr/_employee_tools.py, backend/app/agents/hr/_payroll_tools.py, backend/app/agents/hr/_schedule_tools.py
`backend/app/agents/inventory/__init__.py` (python, 4 loc)
  imports: app
  → usa: backend/app/agents/inventory/agent.py
`backend/app/agents/inventory/agent.py` (python, 85 loc) — Inventory (stock) agent — LangGraph graph for stock queries and batch edits
  symbols: async def inventory_agent_node(state); def inventory_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/inventory/prompts.py, backend/app/agents/inventory/tools.py
`backend/app/agents/inventory/prompts.py` (python, 42 loc)
`backend/app/agents/inventory/tools.py` (python, 377 loc) — Inventory (stock) agent — tools de consulta y de modificación por lotes…
  symbols: def _parse_uuid(value, label); def _parse_items(items_json); async def get_stock_overview(tenant_id); async def list_low_stock(tenant_id); async def find_products(tenant_id, query, category); async def get_product_stock(tenant_id, ref); def _format_adjust_preview(res); def _format_update_preview(res); async def _gated_batch(tenant_uuid); async def batch_adjust_stock(tenant_id, items_json, op, reason, confirm); async def batch_update_products(tenant_id, items_json, confirm)
  imports: __future__, app, json, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/agent_tools/reports.py, backend/app/agents/shared/db.py, backend/app/db/models/inventory.py, backend/app/services/autonomy_gate.py, backend/app/services/inventory/__init__.py, backend/app/services/workflow/approval_actions.py, backend/app/agents/tenant_context.py
`backend/app/agents/marketing/__init__.py` (python, 17 loc) — Marketing agent package…
  → usa: backend/app/agents/marketing/agent.py, backend/app/agents/marketing/tools.py
`backend/app/agents/marketing/agent.py` (python, 71 loc) — Marketing agent — LangGraph graph definition and node logic
  symbols: async def marketing_agent_node(state); def marketing_finalize_node(state); async def run_agent(prompt, tenant_id)
  imports: app, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/core/llm_factory.py, backend/app/agents/marketing/prompts.py, backend/app/agents/marketing/tools.py
`backend/app/agents/marketing/prompts.py` (python, 6 loc) — System prompts for the marketing agent
  imports: app
  → usa: backend/app/prompts/__init__.py
`backend/app/agents/marketing/tools.py` (python, 285 loc) — Marketing agent — tools: catálogo, búsqueda de imágenes y creación de posts
  symbols: async def get_product_catalog(tenant_id); async def search_image(query, tenant_id); async def generate_image(prompt, tenant_id); async def list_social_accounts(tenant_id); async def create_post(tenant_id, platform, content, social_account_id, image_url, scheduled_at); async def create_campaign(tenant_id, name, posts, description)
  imports: __future__, app, datetime, langchain_core, logging, sqlalchemy, typing, uuid
  → usa: backend/app/agents/agent_tools/reports.py, backend/app/db/base.py, backend/app/db/models/inventory.py, backend/app/db/models/marketing.py, backend/app/services/autonomy_gate.py, backend/app/services/marketing/image_generation.py, backend/app/services/marketing/image_search.py, backend/app/agents/tenant_context.py
`backend/app/agents/orchestrator/__init__.py` (python, 36 loc) — Orchestrator (Coordinador) package — superficie pública mínima…
  imports: app
  → usa: backend/app/agents/orchestrator/_core.py, backend/app/agents/orchestrator/_dispatch_handlers.py, backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/_core.py` (python, 108 loc) — Orquestador central basado en LangGraph…
  symbols: def route_after_validate(state); def route_after_dispatch(state); def _route_after_load_knowledge(state); def build_orchestrator()
  imports: app, langgraph
  → usa: backend/app/agents/orchestrator/classifier.py, backend/app/agents/orchestrator/node_handlers.py, backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/_dispatch_handlers.py` (python, 636 loc) — Node handlers: dispatch_node and all dispatch helpers
  symbols: async def _invoke_dynamic_employee(enriched_state, subtask, agent_name, tenant_id); async def _invoke_dispatcher_impl(enriched_state, subtask, agent_name); async def invoke_dispatcher(enriched_state, subtask, agent_name); async def _persist_agent_trace(enriched_state, agent_name, dispatch_status, elapsed_s); async def _execute_one(idx, subtask, state, exec_ctx); def _process_gathered_results(gathered, state, plan, updated_plan, new_results, _audit_tasks); async def dispatch_node(state)
  imports: app, asyncio, datetime, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/orchestrator/dispatchers/__init__.py, backend/app/agents/orchestrator/state.py, backend/app/db/base.py, backend/app/db/models/ai_employees.py, backend/app/services/execution_context.py, backend/app/services/orchestration/executor.py
`backend/app/agents/orchestrator/_init_handlers.py` (python, 96 loc) — Node handlers: init_tenant_node and load_knowledge_node
  symbols: async def init_tenant_node(state); async def load_knowledge_node(state)
  imports: app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/agents/orchestrator/state.py, backend/app/core/llm_factory.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/encryption.py
`backend/app/agents/orchestrator/_plan_handlers.py` (python, 568 loc) — Node handlers: plan_node and its helpers (_plan_from_blueprint, _plan_from_llm)
  symbols: async def _employee_passes_health_check(emp, db); async def _load_tenant_custom_employees(tenant_id); def _custom_employees_block(employees); def _custom_employees_hash(employees); async def _plan_from_blueprint(state, wf); async def _plan_from_llm(state); async def plan_node(state)
  imports: app, asyncio, datetime, hashlib, json, logging, pydantic, sqlalchemy, uuid
  → usa: backend/app/agents/orchestrator/state.py, backend/app/core/config.py, backend/app/core/llm_factory.py, backend/app/db/base.py, backend/app/db/models/ai_employees.py, backend/app/db/models/models.py, backend/app/services/llm_cache.py
`backend/app/agents/orchestrator/_summarize_handlers.py` (python, 103 loc) — Node handlers: summarize_node
  symbols: async def summarize_node(state)
  imports: app, asyncio, langchain_core, logging
  → usa: backend/app/agents/orchestrator/state.py, backend/app/core/llm_factory.py
`backend/app/agents/orchestrator/_validate_handlers.py` (python, 193 loc) — Node handlers: validate_node
  symbols: def _heuristic_classify(intent); def needs_clarification(intent); async def validate_node(state)
  imports: app, asyncio, logging
  → usa: backend/app/agents/orchestrator/state.py, backend/app/services/llm_cache.py
`backend/app/agents/orchestrator/classifier.py` (python, 456 loc) — Clasificador de intenciones del orquestador…
  symbols: def _strip_accents(text); def _normalize_for_cache(text); def _is_question(text); def _strong_keyword_match(intent_lower); def _has_multi_step_connector(intent_lower); def _is_pure_chitchat(intent_lower); def _keyword_classify(intent_lower); def _meets_employee_contract(emp); async def _resolve_custom_employee(state, intent_lower); def _classify_cache_ttl(); async def classify_node(state)
  imports: app, logging, unicodedata
  → usa: backend/app/agents/orchestrator/classifier_data.py, backend/app/agents/orchestrator/state.py, backend/app/core/config.py, backend/app/prompts/__init__.py
`backend/app/agents/orchestrator/classifier_data.py` (python, 354 loc) — Tablas de datos del Coordinador (clasificador de intenciones)…
  imports: re
`backend/app/agents/orchestrator/dispatchers/__init__.py` (python, 66 loc) — Dispatcher registry — centraliza el mapeo agent_name → función dispatcher
  imports: app
  → usa: backend/app/agents/orchestrator/dispatchers/accounting.py, backend/app/agents/orchestrator/dispatchers/banking.py, backend/app/agents/orchestrator/dispatchers/billing.py, backend/app/agents/orchestrator/dispatchers/chat.py, backend/app/agents/orchestrator/dispatchers/compliance.py, backend/app/agents/orchestrator/dispatchers/crm.py, backend/app/agents/orchestrator/dispatchers/documents.py, backend/app/agents/orchestrator/dispatchers/hr.py, backend/app/agents/orchestrator/dispatchers/inventory.py, backend/app/agents/orchestrator/dispatchers/marketing.py (+3)
`backend/app/agents/orchestrator/dispatchers/_outcome.py` (python, 134 loc) — Detección ESTRUCTURADA de fallo de un agente LangGraph…
  symbols: def tool_was_invoked(messages); def write_tool_was_invoked(messages); def detect_failure(messages, final_text, intent)
  imports: __future__, typing
`backend/app/agents/orchestrator/dispatchers/accounting.py` (python, 15 loc) — Dispatcher contable (accounting agent)
  symbols: async def _dispatch_accounting(state, subtask)
  imports: app, logging
  → usa: backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/dispatchers/banking.py` (python, 19 loc) — Dispatcher bancario (banking agent)…
  symbols: async def _dispatch_banking(state, subtask)
  imports: app, logging
  → usa: backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/dispatchers/billing.py` (python, 196 loc) — Dispatcher de facturación (billing agent)…
  symbols: async def _dispatch_billing(state, subtask)
  imports: app, datetime, logging
  → usa: backend/app/agents/orchestrator/dispatchers/_outcome.py, backend/app/agents/orchestrator/state.py, backend/app/services/orchestration/__init__.py
`backend/app/agents/orchestrator/dispatchers/chat.py` (python, 464 loc) — Dispatcher de chat — responde preguntas generales y consultas de estado sin invocar agentes especializados…
  symbols: async def _dispatch_chat(state, subtask); def _build_tenant_context(state); def _detect_topics(intent); async def _build_extra_context(state); async def _load_workflow_context(tenant_id); async def _load_billing_context(tenant_id); async def _load_hr_context(tenant_id); async def _load_crm_context(tenant_id); async def _load_banking_context(tenant_id); async def _load_recent_tasks_context(tenant_id)
  imports: app, asyncio, datetime, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/orchestrator/state.py, backend/app/core/llm_factory.py, backend/app/db/base.py, backend/app/db/models/accounting.py, backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/db/models/models.py
`backend/app/agents/orchestrator/dispatchers/compliance.py` (python, 19 loc) — Dispatcher de compliance fiscal…
  symbols: async def _dispatch_compliance(state, subtask)
  imports: app, logging
  → usa: backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/dispatchers/crm.py` (python, 92 loc) — Dispatcher de CRM / ventas…
  symbols: async def _dispatch_crm(state, subtask)
  imports: app, logging
  → usa: backend/app/agents/orchestrator/dispatchers/_outcome.py, backend/app/agents/orchestrator/state.py, backend/app/services/orchestration/__init__.py
`backend/app/agents/orchestrator/dispatchers/documents.py` (python, 107 loc) — Dispatcher de documentos (documents agent)…
  symbols: async def _dispatch_documents(state, subtask)
  imports: app, logging
  → usa: backend/app/agents/orchestrator/dispatchers/_outcome.py, backend/app/agents/orchestrator/state.py, backend/app/services/orchestration/__init__.py
`backend/app/agents/orchestrator/dispatchers/hr.py` (python, 19 loc) — Dispatcher de Recursos Humanos (HR agent)…
  symbols: async def _dispatch_hr(state, subtask)
  imports: app, logging
  → usa: backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/dispatchers/inventory.py` (python, 12 loc) — Dispatcher para el agente de stock (inventario)
  symbols: async def _dispatch_inventory(state, subtask)
  imports: app
  → usa: backend/app/agents/orchestrator/dispatchers/misc.py, backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/dispatchers/marketing.py` (python, 12 loc) — Dispatcher para el agente de marketing autónomo
  symbols: async def _dispatch_marketing(state, subtask)
  imports: app
  → usa: backend/app/agents/orchestrator/dispatchers/misc.py, backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/dispatchers/misc.py` (python, 265 loc) — Dispatchers misceláneos: RAG, Excel, Email, Workflow, Skill…
  symbols: def _extract_final_text(result_state); async def _run_graph_agent(graph, state, subtask, agent_name, category); async def _dispatch_rag(state, subtask); async def _dispatch_excel(state, subtask); async def _dispatch_email(state, subtask); async def _dispatch_workflow(state, subtask); async def _dispatch_skill(state, subtask)
  imports: app, inspect, logging
  → usa: backend/app/agents/orchestrator/dispatchers/_outcome.py, backend/app/agents/orchestrator/state.py, backend/app/services/orchestration/__init__.py, backend/app/skills/registry.py
`backend/app/agents/orchestrator/dispatchers/recruitment.py` (python, 12 loc) — Dispatcher para el agente de reclutamiento autónomo
  symbols: async def _dispatch_recruitment(state, subtask)
  imports: app
  → usa: backend/app/agents/orchestrator/dispatchers/misc.py, backend/app/agents/orchestrator/state.py
`backend/app/agents/orchestrator/dispatchers/reports.py` (python, 271 loc) — Dispatcher de informes mensuales (report)
  symbols: async def _dispatch_report(state, subtask)
  imports: app, calendar, datetime, logging, os, sqlalchemy, uuid
  → usa: backend/app/agents/orchestrator/state.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/orchestration/__init__.py, backend/app/services/pdf/__init__.py
`backend/app/agents/orchestrator/node_handlers.py` (python, 26 loc) — Node handler functions for the LangGraph orchestrator…
  imports: app
  → usa: backend/app/agents/orchestrator/_dispatch_handlers.py, backend/app/agents/orchestrator/_init_handlers.py, backend/app/agents/orchestrator/_plan_handlers.py, backend/app/agents/orchestrator/_summarize_handlers.py, backend/app/agents/orchestrator/_validate_handlers.py
`backend/app/agents/orchestrator/state.py` (python, 91 loc) — Tipos de estado del orquestador…
  symbols: class TaskStatus; class SubTask; class AgentResult; class OrchestratorState
  imports: enum, typing
`backend/app/agents/rag/__init__.py` (python, 20 loc) — RAG agent package…
  → usa: backend/app/agents/rag/agent.py, backend/app/agents/rag/tools.py
`backend/app/agents/rag/agent.py` (python, 71 loc) — RAG agent — LangGraph graph definition and node logic
  symbols: async def rag_agent_node(state); def rag_finalize_node(state)
  imports: app, datetime, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/agents/types.py, backend/app/core/llm_factory.py, backend/app/agents/rag/prompts.py, backend/app/agents/rag/tools.py
`backend/app/agents/rag/prompts.py` (python, 6 loc) — System prompts for the RAG agent
  imports: app
  → usa: backend/app/prompts/__init__.py
`backend/app/agents/rag/tools.py` (python, 280 loc) — RAG agent — tools: búsqueda semántica y respuesta desde documentos
  symbols: async def search_documents(tenant_id, query, top_k, employee_id); async def answer_from_documents(tenant_id, question, top_k, employee_id)
  imports: __future__, app, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/agent_tools/documents.py, backend/app/agents/agent_tools/knowledge.py, backend/app/agents/agent_tools/reports.py, backend/app/agents/agent_tools/semantic_search.py, backend/app/core/llm_factory.py, backend/app/db/base.py
`backend/app/agents/recruitment/__init__.py` (python, 28 loc) — Recruitment agent package…
  → usa: backend/app/agents/recruitment/agent.py, backend/app/agents/recruitment/tools.py
`backend/app/agents/recruitment/agent.py` (python, 48 loc) — Recruitment agent — LangGraph graph definition and node logic
  symbols: async def recruitment_agent_node(state); def recruitment_finalize_node(state)
  imports: app, langchain_core, langgraph
  → usa: backend/app/agents/base.py, backend/app/core/llm_factory.py, backend/app/agents/recruitment/prompts.py, backend/app/agents/recruitment/tools.py
`backend/app/agents/recruitment/prompts.py` (python, 6 loc) — System prompts for the recruitment agent
  imports: app
  → usa: backend/app/prompts/__init__.py
`backend/app/agents/recruitment/tools.py` (python, 364 loc) — Recruitment agent — tools: gestión de puestos y candidatos
  symbols: def _parse_uuid(value, label); async def create_position(tenant_id, title, department, description, required_skills, experience_min_years, salary_range_min, salary_range_max); async def list_positions(tenant_id, status); async def process_cv(tenant_id, position_id, cv_file_path); async def list_candidates(tenant_id, position_id, status); async def update_candidate_status(tenant_id, candidate_id, new_status); async def create_candidate(tenant_id, name, email, phone, position_id)
  imports: __future__, app, json, langchain_core, logging, sqlalchemy, uuid
  → usa: backend/app/agents/agent_tools/reports.py, backend/app/db/base.py, backend/app/db/models/hr.py, backend/app/agents/tenant_context.py
`backend/app/agents/shared/__init__.py` (python, 1 loc)
`backend/app/agents/shared/db.py` (python, 49 loc) — Sesión de BD para tools de agentes…
  symbols: async def tool_session(tenant_id)
  imports: __future__, app, collections, contextlib, sqlalchemy, uuid
  → usa: backend/app/core/tenant_context.py, backend/app/db/base.py
`backend/app/agents/shared/validators/__init__.py` (python, 1 loc)
`backend/app/agents/shared/validators/billing.py` (python, 266 loc) — Validadores deterministas para facturación española…
  symbols: def validate_nif(nif); def validate_iban(iban); def _coerce_number(value); def validate_vat_rate(rate); def validate_amount(amount); def validate_invoice_date(invoice_date); class InvoiceValidationResult {__init__, is_valid, to_dict}; def validate_invoice_data(client_nif, amount_base, vat_rate, invoice_date, iban)
  imports: datetime, decimal, re
`backend/app/agents/tenant_context.py` (python, 88 loc) — Aislamiento multi-tenant a nivel de tool execution…
  symbols: def set_active_tenant(tenant_id); def get_active_tenant(); def enforce_tenant(tool); def isolated(tools)
  imports: __future__, app, functools, logging, typing
  → usa: backend/app/core/tenant_context.py
`backend/app/agents/tool_registry.py` (python, 270 loc) — Registro central de herramientas (@tool) de todos los agentes…
  symbols: def _build_registry(); def get_tool_for_employee(tool_module); def get_registry(); def list_tools(); def call_tool(tool_name, params)
  imports: app, collections, logging, typing
  → usa: backend/app/agents/tenant_context.py, backend/app/agents/tool_timeout.py
`backend/app/agents/tool_timeout.py` (python, 95 loc) — Timeout por tool ejecutada por agentes…
  symbols: def with_timeout(seconds); def apply_default_timeout(tool); def timed(tools)
  imports: __future__, app, asyncio, functools, logging, time, typing
  → usa: backend/app/core/observability.py
`backend/app/agents/types.py` (python, 15 loc) — Tipos base compartidos por todos los agentes
  symbols: class StepResult
  imports: pydantic, typing
`backend/app/agents/workers/__init__.py` (python, 14 loc) — Workers package — AI Employee budget guard and dynamic agent compiler
  → usa: backend/app/agents/workers/budget_guard.py, backend/app/agents/workers/compiler.py
`backend/app/agents/workers/budget_guard.py` (python, 19 loc) — Backward-compatibility shim — implementacion en services/agent_budget.py…
  imports: app
  → usa: backend/app/services/agent_budget.py
`backend/app/agents/workers/compiler.py` (python, 171 loc) — Dynamic Agent Compiler — Compila un grafo LangGraph para un AIEmployee…
  symbols: async def compile_dynamic_agent(employee_id, db)
  imports: app, langchain_core, langgraph, logging, sqlalchemy, typing
  → usa: backend/app/agents/base.py, backend/app/agents/tool_registry.py, backend/app/core/llm_factory.py, backend/app/db/models/ai_employees.py
`backend/app/agents/workflow/__init__.py` (python, 13 loc) — Workflow agent package
  → usa: backend/app/agents/workflow/agent.py, backend/app/agents/workflow/tools.py
`backend/app/agents/workflow/agent.py` (python, 206 loc) — Workflow agent â€” orquestación principal: LLM â†’ parse â†’ DB â†’ resultado
  symbols: class WorkflowAgentResult; async def run_workflow_agent(user_intent, tenant_id, user_id, task_id, execution_mode)
  imports: __future__, app, dataclasses, json, langchain_core, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/prompts/__init__.py, backend/app/agents/workflow/tools.py
`backend/app/agents/workflow/tools.py` (python, 71 loc) — Workflow agent — tools: compilación de pasos deterministas
  symbols: async def compile_deterministic_steps(name, description, trigger_type, action_instruction)
  imports: __future__, app, json, langchain_core, logging, typing
  → usa: backend/app/prompts/__init__.py
`backend/app/api/__init__.py` (python, 1 loc)
`backend/app/api/v1/__init__.py` (python, 1 loc)
`backend/app/api/v1/router.py` (python, 118 loc)
  imports: app, fastapi
  → usa: backend/app/api/v1/routes/__init__.py
`backend/app/api/v1/routes/__init__.py` (python, 1 loc)
`backend/app/api/v1/routes/accounting.py` (python, 293 loc)
  symbols: async def list_journal_entries(request, db, current_user); async def create_journal_entry(request, payload, db, current_user); async def delete_journal_entry(request, entry_id, db, current_user); async def list_fixed_assets(request, db, current_user); async def create_fixed_asset(request, payload, db, current_user); async def update_fixed_asset(request, asset_id, payload, db, current_user); async def delete_fixed_asset(request, asset_id, db, current_user); class _ClosePeriodIn; class _ReopenIn; def _period_to_dict(p); async def list_accounting_periods(request, year, db, current_user); async def close_accounting_period(request, payload, db, current_user) … (+6)
  imports: app, datetime, fastapi, pydantic, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/accounting/__init__.py, backend/app/services/billing/__init__.py
`backend/app/api/v1/routes/admin.py` (python, 261 loc) — Endpoints de administración: backup y restauración de la base de datos…
  symbols: def _parse_db_url(url); async def download_backup(request, current_user); async def restore_backup(request, file, current_user); async def invalidate_llm_cache(request, prefix, current_user); async def db_status(request, current_user, db)
  imports: app, asyncio, datetime, fastapi, logging, re, sqlalchemy, urllib
  → usa: backend/app/core/config.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py
`backend/app/api/v1/routes/advisory.py` (python, 65 loc)
  symbols: async def get_boe_news(request, section, limit, current_user); async def get_fiscal_calendar(request, days_ahead, current_user); async def get_advisory_guides(request, section, current_user)
  imports: app, fastapi
  → usa: backend/app/core/dependencies.py, backend/app/integrations/advisory_guides.py, backend/app/integrations/boe_scraper.py, backend/app/middleware/rate_limit.py
`backend/app/api/v1/routes/aeat_presentation.py` (python, 326 loc) — Endpoints AEAT — custodia de certificado y presentación electrónica de modelos…
  symbols: async def get_active_cert(request, db, current_user); async def upload_cert(request, file, password, label, notes, db, current_user); async def revoke_cert(request, cert_id, db, current_user); class _CreatePresentationIn; async def create_presentation_endpoint(request, payload, db, current_user); async def create_303_from_quarter(request, quarter, year, environment, db, current_user); async def _build_xml_generic(db, tenant_id, model_code, year, period, quarter); async def create_quarterly_presentation(request, model_code, quarter, year, environment, db, current_user); async def create_yearly_presentation(request, model_code, year, environment, db, current_user); async def submit_presentation_endpoint(request, presentation_id, dry_run, db, current_user); async def list_presentations_endpoint(request, limit, db, current_user); async def download_acuse(request, presentation_id, db, current_user)
  imports: app, fastapi, logging, pydantic, sqlalchemy, uuid
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/aeat/__init__.py
`backend/app/api/v1/routes/ai_employees.py` (python, 265 loc) — Rutas para el sistema de Empleados IA — thin controller
  symbols: async def list_ai_employees(db, current_user); async def create_ai_employee(payload, background_tasks, db, current_user); async def list_available_skills(current_user); async def get_ai_employee(employee_id, db, current_user); async def get_employee_usage(employee_id, limit, offset, db, current_user); async def provision_ai_employee(employee_id, payload, db, current_user); async def update_employee_icon(employee_id, payload, db, current_user); async def update_employee_appearance(employee_id, payload, db, current_user); async def update_employee_budget(employee_id, payload, db, current_user); async def update_employee_status(employee_id, new_status, db, current_user); async def instruct_employee(employee_id, payload, db, current_user); async def delete_ai_employee(employee_id, db, current_user) … (+3)
  imports: app, fastapi, logging, sqlalchemy, typing
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/ai/__init__.py
`backend/app/api/v1/routes/albaranes.py` (python, 124 loc) — Albaranes (delivery notes) API routes
  symbols: async def list_albaranes(request, db, current_user); async def create_albaran(request, payload, db, current_user); async def get_albaran(request, albaran_id, db, current_user); async def update_albaran_status(request, albaran_id, payload, db, current_user); async def delete_albaran(request, albaran_id, db, current_user); async def get_albaran_pdf(request, albaran_id, db, current_user)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/sales/__init__.py
`backend/app/api/v1/routes/alerts.py` (python, 46 loc) — Rutas para alertas automáticas
  symbols: async def list_alerts(request, hours, db, current_user); async def trigger_check(request, db, current_user)
  imports: app, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/alerts/service.py
`backend/app/api/v1/routes/analytics.py` (python, 43 loc) — Analytics dashboard endpoint — single aggregated source for the /analitica page
  symbols: async def get_analytics_dashboard(request, period, db, current_user)
  imports: app, datetime, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/analytics/__init__.py, backend/app/services/reports/__init__.py
`backend/app/api/v1/routes/approvals.py` (python, 66 loc) — Rutas de aprobaciones humanas pendientes
  symbols: async def list_pending_approvals(request, db, current_user); async def decide_approval(request, approval_id, decision, db, current_user); async def cleanup_approvals(request, db, current_user)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/workflow/__init__.py
`backend/app/api/v1/routes/auth.py` (python, 88 loc) — Rutas de autenticación: registro, login y refresh token
  symbols: async def get_me(current_user); async def register(request, payload, db); async def login(request, payload, db); async def refresh(payload); async def forgot_password(request, payload, db); async def reset_password(payload, db)
  imports: app, fastapi, sqlalchemy
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/core/net.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/auth/__init__.py
`backend/app/api/v1/routes/autonomy.py` (python, 100 loc) — Rutas REST de política de autonomía (SEC.AUT)
  symbols: class PolicyEntry; class PolicyListOut; async def get_all_policies(user, db); class SetPolicyIn; async def put_policy(domain, payload, user, db); async def delete_policy(domain, user, db)
  imports: __future__, app, fastapi, logging, pydantic, sqlalchemy, typing
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/autonomy.py
`backend/app/api/v1/routes/backup_local.py` (python, 95 loc) — Endpoints REST de registro de backups locales (BAK.LOC + BAK.UI)
  symbols: class RecordBackupRequest; class RecordBackupResponse; class BackupStatusResponse; async def record_backup_endpoint(body, user, db); async def get_backup_status(user, db)
  imports: app, datetime, fastapi, pydantic, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/backup_local.py
`backend/app/api/v1/routes/banking.py` (python, 172 loc)
  symbols: async def get_banking_summary(request, db, current_user); async def list_transactions(request, db, current_user); async def sync_bank_transactions(request, db, current_user); async def purge_demo_transactions(request, db, current_user); async def reconcile_transaction(request, tx_id, payload, db, current_user); async def ignore_transaction(request, tx_id, db, current_user); async def unreconcile_transaction(request, tx_id, db, current_user); async def get_reconciliation_suggestions(request, db, current_user); async def reject_reconciliation_suggestion(request, payload, db, current_user); async def auto_reconcile(request, db, current_user); async def get_banking_analytics(request, db, current_user)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/__init__.py
`backend/app/api/v1/routes/calendar.py` (python, 123 loc) — Calendario unificado — agrega eventos de múltiples módulos
  symbols: async def unified_calendar(request, start, end, db, current_user)
  imports: app, datetime, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/billing.py, backend/app/db/models/calendar.py, backend/app/db/models/hr.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py
`backend/app/api/v1/routes/client_portal.py` (python, 242 loc) — Portal externo de clientes — autenticación por token + vista de facturas
  symbols: class PortalAuthRequest; async def get_portal_token_status(request, client_id, db, current_user); async def generate_portal_token(request, client_id, days_valid, db, current_user); async def revoke_portal_token(request, client_id, db, current_user); async def authenticate_portal(request, payload, db); async def portal_me(request, db, client); async def portal_download_invoice_pdf(request, invoice_id, db, client)
  imports: app, datetime, fastapi, logging, pydantic, sqlalchemy, uuid
  → usa: backend/app/core/config.py, backend/app/core/datetime_utils.py, backend/app/core/dependencies.py, backend/app/core/security.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py (+2)
`backend/app/api/v1/routes/clients.py` (python, 111 loc)
  symbols: async def list_clients(request, skip, limit, client_type, db, current_user); async def create_client(request, payload, db, current_user); async def update_client(request, client_id, payload, db, current_user); async def delete_client(request, client_id, db, current_user); async def list_client_invoices(request, client_id, skip, limit, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/sales/__init__.py
`backend/app/api/v1/routes/collections.py` (python, 62 loc) — Rutas de inteligencia de cobros (F3.9) — ranking de riesgo + recordatorios
  symbols: async def get_collections_risk(request, only_with_outstanding, db, current_user); async def get_due_reminders(request, fire_date, db, current_user)
  imports: app, datetime, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/middleware/rate_limit.py, backend/app/services/collections/__init__.py
`backend/app/api/v1/routes/crm.py` (python, 229 loc)
  symbols: async def list_opportunities(request, db, current_user); async def create_opportunity(request, payload, db, current_user); async def update_opportunity(request, opp_id, payload, db, current_user); async def delete_opportunity(request, opp_id, db, current_user); async def list_activities(request, client_id, opportunity_id, db, current_user); async def create_activity(request, payload, db, current_user); async def delete_activity(request, activity_id, db, current_user); async def list_events(request, db, current_user); async def create_event(request, payload, db, current_user); async def update_event(request, event_id, payload, db, current_user); async def delete_event(request, event_id, db, current_user); async def list_reservations(request, db, current_user) … (+3)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/crm/__init__.py
`backend/app/api/v1/routes/documents.py` (python, 669 loc) — Rutas para gestión documental: upload y listado de documentos del tenant
  symbols: async def search_documents(q, limit, db, current_user); async def contract_interview(body, db, current_user); async def contract_save(body, db, current_user); async def upload_document(request, file, category, db, current_user); async def scan_documents(request, files, db, current_user); async def upload_bulk_documents(request, file, category, db, current_user); async def export_documents(request, db, current_user); async def list_documents(request, category, db, current_user); async def delete_document(request, document_id, db, current_user); async def download_document(request, document_id, db, current_user); async def update_document_content(request, document_id, body, db, current_user); async def list_documents_by_category(request, category, db, current_user) … (+10)
  imports: app, fastapi, logging, os, sqlalchemy, uuid, zipfile
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/db/models/tenant.py, backend/app/middleware/rate_limit.py, backend/app/services/documents/__init__.py
`backend/app/api/v1/routes/email_marketing.py` (python, 215 loc) — Email marketing: plantillas, campañas y envíos masivos…
  symbols: def _validate_future(v); class TemplateCreate; class TemplateOut; class CampaignCreate {_check_scheduled_at}; class CampaignUpdate {_check_scheduled_at}; class CampaignOut; async def list_templates(db, current_user); async def create_template(body, db, current_user); async def update_template(template_id, body, db, current_user); async def delete_template(template_id, db, current_user); async def list_campaigns(db, current_user); async def create_campaign(body, db, current_user) … (+4)
  imports: app, datetime, fastapi, pydantic, sqlalchemy, uuid
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/email_marketing.py, backend/app/db/models/models.py, backend/app/services/email_marketing/__init__.py
`backend/app/api/v1/routes/erp.py` (python, 32 loc) — ERP routes — re-exports sub-routers for backward compatibility…
  imports: app, fastapi
  → usa: backend/app/api/v1/routes/albaranes.py, backend/app/api/v1/routes/clients.py, backend/app/api/v1/routes/invoices.py, backend/app/api/v1/routes/products.py, backend/app/api/v1/routes/purchase_orders.py, backend/app/api/v1/routes/recurring_invoices.py, backend/app/api/v1/routes/sales_orders.py
`backend/app/api/v1/routes/generative_ui.py` (python, 159 loc) — Sandbox de UI Generativa — Interfaces permanentes generadas por IA…
  symbols: async def debug_llm(db, current_user); async def generate_ui(payload, db, current_user); async def list_generated_uis(pinned_only, limit, offset, db, current_user); async def get_generated_ui(ui_id, db, current_user); async def update_generated_ui(ui_id, payload, db, current_user); async def delete_generated_ui(ui_id, db, current_user)
  imports: app, fastapi, logging, sqlalchemy
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/ai/__init__.py
`backend/app/api/v1/routes/hr.py` (python, 20 loc) — Rutas RRHH — agregador de los submódulos HR…
  imports: app, fastapi
  → usa: backend/app/api/v1/routes/__init__.py
`backend/app/api/v1/routes/hr_documents.py` (python, 125 loc) — Asesoria Documental — Generacion de documentos laborales con IA…
  symbols: async def generate_hr_document(payload, db, current_user); async def list_hr_documents(doc_type, status_filter, limit, offset, db, current_user); async def get_hr_document(doc_id, db, current_user); async def hr_document_pdf(doc_id, db, current_user); async def approve_hr_document(doc_id, db, current_user); async def delete_hr_document(doc_id, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/hr/__init__.py
`backend/app/api/v1/routes/hr_employees.py` (python, 239 loc) — Rutas RRHH — empleados, documentos de empleado y documentos PDF HR
  symbols: async def list_employees(request, db, current_user); async def create_employee(request, payload, db, current_user); async def update_employee(request, employee_id, payload, db, current_user); async def delete_employee(request, employee_id, db, current_user); async def list_employee_documents(employee_id, db, current_user); async def upload_employee_document_file(employee_id, file, db, current_user); async def download_employee_document(employee_id, doc_id, db, current_user); async def delete_employee_document(employee_id, doc_id, db, current_user); async def generate_finiquito_pdf_endpoint(request, payload, db, current_user); async def generate_liquidacion_finiquito_pdf_endpoint(request, payload, db, current_user); async def generate_registro_jornada_pdf_endpoint(request, payload, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/hr/__init__.py
`backend/app/api/v1/routes/hr_expenses.py` (python, 202 loc) — Rutas RRHH — gastos de empleados
  symbols: async def list_expenses(request, status_filter, employee_id, db, current_user); async def create_expense(request, payload, db, current_user); async def scan_expense_receipt(request, file, current_user); async def approve_expense(request, expense_id, db, current_user); async def reject_expense(request, expense_id, db, current_user); async def reimburse_expense(request, expense_id, db, current_user); async def upload_expense_receipt(request, expense_id, file, db, current_user); async def download_expense_receipt(request, expense_id, db, current_user); async def delete_expense(request, expense_id, db, current_user); def _expense_row(exp)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/hr/__init__.py
`backend/app/api/v1/routes/hr_payrolls.py` (python, 168 loc) — Rutas RRHH — nóminas
  symbols: async def preview_payroll(request, employee_id, db, current_user); async def generate_payroll_auto(request, payload, db, current_user); async def list_payrolls(request, db, current_user); async def generate_payroll(request, payload, db, current_user); async def approve_payroll(request, payroll_id, background_tasks, db, current_user); async def update_payroll(request, payroll_id, payload, db, current_user); async def delete_payroll(request, payroll_id, db, current_user); async def download_payroll_pdf(request, payroll_id, db, current_user)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/hr/__init__.py, backend/app/services/state_machine.py
`backend/app/api/v1/routes/hr_time.py` (python, 269 loc) — Rutas RRHH — horarios, fichajes y ausencias
  symbols: async def list_schedules(request, db, current_user); async def export_schedules(request, format, db, current_user); async def get_employee_schedule(request, employee_id, db, current_user); async def upsert_employee_schedule(request, employee_id, payload, db, current_user); async def ai_suggest_schedules(request, payload, db, current_user); async def list_attendance(request, date, db, current_user); async def get_currently_working(request, db, current_user); async def clock_in(request, payload, db, current_user); async def clock_out(request, attendance_id, db, current_user); async def list_leave_requests(request, status_filter, db, current_user); async def create_leave_request(request, payload, db, current_user); async def approve_leave_request(request, request_id, db, current_user) … (+3)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/hr/__init__.py
`backend/app/api/v1/routes/import_bulk.py` (python, 222 loc) — Bulk CSV import endpoints for employees, clients and products…
  symbols: class ImportResult; def _to_response(result); async def import_employees(body, db, current_user); async def import_clients(body, db, current_user); async def import_products(body, db, current_user); class MigrationImportResult; async def import_payrolls(body, db, current_user); async def import_invoices(body, db, current_user); async def import_bank_transactions(body, db, current_user); class N43ImportResult; async def import_bank_statement_n43(file, db, current_user)
  imports: app, fastapi, pydantic, sqlalchemy, typing
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/services/migration/bulk_import.py
`backend/app/api/v1/routes/integrations.py` (python, 328 loc) — Rutas para gestionar integraciones de cada tenant — thin controller
  symbols: async def list_integrations(request, db, current_user); async def connect_psd2(request, payload, db, current_user); async def disconnect_psd2(request, db, current_user); async def connect_email(request, payload, db, current_user); async def disconnect_email(request, db, current_user); async def email_status(request, db, current_user); async def google_auth_url(request, current_user); async def google_callback(request, code, state, db); async def disconnect_gmail(request, db, current_user); async def disconnect_gdrive(request, db, current_user); async def gmail_status(request, db, current_user); async def gmail_recent(request, db, current_user) … (+10)
  imports: app, fastapi, json, logging, sqlalchemy
  → usa: backend/app/api/v1/__init__.py, backend/app/core/config.py, backend/app/core/dependencies.py, backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/integration/__init__.py
`backend/app/api/v1/routes/invoices.py` (python, 515 loc) — Rutas para facturas — thin controller
  symbols: async def scan_invoice(request, file, db, current_user); async def learn_scan_correction(request, payload, db, current_user); async def scan_invoices_batch(request, files, db, current_user); async def import_invoices(request, payload, db, current_user); async def list_invoices(request, skip, limit, db, current_user); async def get_invoice(request, invoice_id, db, current_user); async def update_invoice_status(request, invoice_id, payload, db, current_user); async def delete_invoice(request, invoice_id, db, current_user); async def create_invoice(request, client_id, payload, background_tasks, db, current_user); async def create_rectificativa(request, invoice_id, payload, background_tasks, db, current_user); async def download_invoice_pdf(request, invoice_id, db, current_user); async def download_rectificative_invoice_pdf(request, invoice_id, reason, db, current_user) … (+3)
  imports: app, fastapi, logging, pathlib, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/billing/__init__.py, backend/app/services/billing/facturae.py, backend/app/services/event_bus.py
`backend/app/api/v1/routes/license.py` (python, 47 loc) — Endpoints de licencia: estado y activación
  symbols: class ActivateRequest; async def license_status(request); async def license_activate(body, request); async def license_warmup(background)
  imports: app, fastapi, pydantic
  → usa: backend/app/core/license.py
`backend/app/api/v1/routes/llm_usage.py` (python, 27 loc) — Endpoint para consultar el uso de LLM por tenant (llamadas, tokens, coste estimado)
  symbols: async def get_llm_usage_stats(months, current_user)
  imports: app, fastapi
  → usa: backend/app/core/dependencies.py, backend/app/services/__init__.py
`backend/app/api/v1/routes/marketing.py` (python, 832 loc) — Marketing: social accounts, campaigns, scheduled posts, OAuth callbacks
  symbols: def _popup_html(success, platform, message); def _zernio_state(tenant_id, config_id); def _zernio_unstate(state); class SocialAccountOut; class CampaignCreate; class CampaignOut; class PostCreate; class PostOut; async def list_accounts(db, current_user); class GenerateImageRequest; async def generate_image_endpoint(body, current_user); async def _pick_config(db, tenant_id, config_id) … (+24)
  imports: app, asyncio, base64, datetime, fastapi, json, pydantic, sqlalchemy, typing, uuid
  → usa: backend/app/core/config.py, backend/app/core/dependencies.py, backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/marketing.py, backend/app/db/models/models.py, backend/app/services/encryption.py, backend/app/services/marketing/image_generation.py, backend/app/services/marketing/provider_config.py, backend/app/services/marketing/zernio_client.py
`backend/app/api/v1/routes/marketplace.py` (python, 128 loc) — Rutas del marketplace de workflows (F3.10)
  symbols: async def list_marketplace_templates(request, category, db, current_user); async def get_marketplace_template(request, slug, db, current_user); async def install_marketplace_template(request, slug, payload, db, current_user); async def seed_official(request, db, current_user); async def export_workflow_yaml(request, workflow_id, db, current_user); async def import_workflow_yaml(request, payload, db, current_user)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/db/models/workflows.py, backend/app/middleware/rate_limit.py, backend/app/services/workflow_marketplace/__init__.py
`backend/app/api/v1/routes/messaging.py` (python, 554 loc) — Rutas de mensajería externa — Telegram webhook + Email + gestión de conexión
  symbols: async def telegram_webhook(request, db); async def connect_telegram(request, db, current_user); async def disconnect_telegram(request, db, current_user); async def telegram_status(request, db, current_user); async def setup_telegram_webhook(request, current_user); class EmailSendPayload; class EmailInstructPayload; async def send_email(request, payload, current_user); async def instruct_email_agent(request, payload, current_user); async def email_status(current_user); async def email_inbox(request, limit, current_user); async def drive_list_files(request, folder, q, current_user) … (+7)
  imports: app, asyncio, fastapi, logging, pydantic, sqlalchemy
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/integrations/telegram_client.py, backend/app/middleware/rate_limit.py, backend/app/services/integration/__init__.py
`backend/app/api/v1/routes/metrics.py` (python, 25 loc) — Rutas de métricas de valor (centro de mando) — thin controller
  symbols: async def get_time_saved(request, days, current_user, db)
  imports: app, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/middleware/rate_limit.py, backend/app/services/metrics/time_saved.py
`backend/app/api/v1/routes/modelos_aeat.py` (python, 335 loc) — Rutas REST para generación de Modelos AEAT calculados (MOD.130/347/390/111/190)…
  symbols: def _current_year(); async def get_modelo_130(quarter, year, user, db); async def get_modelo_111(quarter, year, user, db); async def get_modelo_190(year, user, db); async def get_modelo_347(year, user, db); async def get_modelo_390(year, user, db); async def get_modelo_200(year, tipo_impositivo_pct, pagos_fraccionados_pagados, user, db); async def get_preventive_check(quarter, year, user, db); def _pdf_response(pdf, filename); async def download_modelo_303_pdf(quarter, year, user, db); async def download_modelo_130_pdf(quarter, year, user, db); async def download_modelo_111_pdf(quarter, year, user, db) … (+8)
  imports: __future__, app, datetime, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/reports/modelos_aeat.py
`backend/app/api/v1/routes/notifications.py` (python, 78 loc) — Rutas REST de notificaciones persistentes (UI.NOT)
  symbols: class NotificationOut; class ListResponse; async def list_endpoint(only_unread, limit, user, db); async def mark_read_endpoint(notification_id, user, db); async def mark_all_read_endpoint(user, db)
  imports: __future__, app, fastapi, pydantic, sqlalchemy, uuid
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/__init__.py
`backend/app/api/v1/routes/onboarding_regap.py` (python, 146 loc) — Rutas REST del wizard REGAP (PRES.REG)
  symbols: class RegapStatusOut; def _to_out(record); async def get_status(user, db); class StartIdentificationIn; async def post_start(payload, user, db); async def post_grant(user, db); class VerifyIn; async def post_verify(payload, user, db); async def post_reset(user, db)
  imports: __future__, app, fastapi, logging, pydantic, sqlalchemy, typing
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/onboarding/regap.py
`backend/app/api/v1/routes/onboarding_wizard.py` (python, 150 loc) — Rutas REST del wizard onboarding focado (UI.ONB)
  symbols: class WizardStateOut; async def get_wizard(user, db); class SetStepIn; async def patch_step(payload, user, db); async def post_skip(user, db); async def get_simulate_303(quarter, year, user); async def post_reset(user, db); async def post_seed(user, db); async def delete_seed(user, db); async def get_seed(user, db)
  imports: __future__, app, fastapi, pydantic, sqlalchemy, typing
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/onboarding/seed.py, backend/app/services/onboarding/simulate_303.py, backend/app/services/onboarding/wizard.py
`backend/app/api/v1/routes/portal.py` (python, 232 loc) — Employee self-service portal — data scoped to the logged-in user's employee record
  symbols: async def _get_my_employee(db, current_user); async def _get_active_attendance(db, tenant_id, employee_id); def _attendance_dict(record); async def _build_portal_payload(db, employee, tenant_id); async def get_portal_me(db, current_user); async def export_my_schedule(format, db, current_user); async def get_portal_as_employee(employee_id, db, current_user); async def submit_my_leave_request(body, db, current_user); async def my_clock_in(body, db, current_user); async def my_clock_out(db, current_user)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/db/models/hr.py, backend/app/services/hr/commands.py, backend/app/services/hr/queries.py
`backend/app/api/v1/routes/pos.py` (python, 207 loc) — Rutas TPV (Punto de Venta)
  symbols: async def get_current_session(request, db, current_user); async def open_session(request, db, current_user); async def list_sessions(request, status_filter, only_mine, limit, db, current_user); async def get_session(request, session_id, db, current_user); async def add_line(request, session_id, payload, db, current_user); async def update_line(request, session_id, line_id, payload, db, current_user); async def remove_line(request, session_id, line_id, db, current_user); async def checkout(request, session_id, payload, db, current_user); async def cancel_session(request, session_id, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/sales/__init__.py
`backend/app/api/v1/routes/presentacion_asistida.py` (python, 87 loc) — Rutas REST de presentación asistida AEAT (PRES.ASS)
  symbols: async def get_info(modelo, user); async def download_xml(modelo, ejercicio, trimestre, user, db)
  imports: __future__, app, datetime, fastapi, sqlalchemy, typing
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/presentacion/asistida.py
`backend/app/api/v1/routes/products.py` (python, 342 loc)
  symbols: async def list_products(request, skip, limit, q, category, is_active, status, db, current_user); async def get_product_by_barcode(request, code, db, current_user); async def update_product(request, product_id, payload, db, current_user); async def delete_product(request, product_id, db, current_user); async def create_product(request, payload, db, current_user); async def stock_valuation(request, db, current_user); async def list_stock_movements(request, product_id, db, current_user); async def create_stock_movement(request, product_id, payload, db, current_user); async def list_expiring_lots(request, days, db, current_user); async def list_product_lots(request, product_id, db, current_user); async def create_product_lot(request, product_id, payload, db, current_user); async def update_product_lot(request, product_id, lot_id, payload, db, current_user) … (+6)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/inventory/__init__.py, backend/app/services/sales/__init__.py
`backend/app/api/v1/routes/projects.py` (python, 130 loc) — Rutas Projects — thin controller para proyectos y tareas de proyecto
  symbols: async def list_projects(request, db, current_user); async def create_project(request, payload, db, current_user); async def update_project(request, project_id, payload, db, current_user); async def delete_project(request, project_id, db, current_user); async def list_tasks(request, project_id, db, current_user); async def create_task(request, payload, db, current_user); async def update_task(request, task_id, payload, db, current_user); async def delete_task(request, task_id, db, current_user)
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/__init__.py
`backend/app/api/v1/routes/purchase_orders.py` (python, 109 loc) — Rutas Purchase Orders — thin controller para pedidos de compra
  symbols: async def list_purchase_orders(request, db, current_user); async def create_purchase_order(request, payload, db, current_user); async def update_purchase_order(request, order_id, payload, db, current_user); async def delete_purchase_order(request, order_id, db, current_user); async def receive_purchase_order(request, order_id, payload, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/sales/__init__.py
`backend/app/api/v1/routes/quotes.py` (python, 104 loc)
  symbols: async def create_quote(request, quote_in, db, current_user); async def list_quotes(request, db, current_user, skip, limit); async def get_quote(request, quote_id, db, current_user); async def update_quote(request, quote_id, quote_update, db, current_user); async def convert_quote_to_invoice(request, quote_id, db, current_user); async def delete_quote(request, quote_id, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/sales/__init__.py
`backend/app/api/v1/routes/recruitment.py` (python, 117 loc) — Endpoints para gestion de reclutamiento…
  symbols: async def list_positions(request, status_filter, db, current_user); async def create_position(request, payload, db, current_user); async def list_candidates(request, position_id, db, current_user); async def upload_cv(request, position_id, file, db, current_user); async def update_candidate_status(request, candidate_id, payload, db, current_user); async def analyze_cv_standalone(request, file, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/middleware/rate_limit.py, backend/app/services/hr/__init__.py
`backend/app/api/v1/routes/recurring_invoices.py` (python, 92 loc) — Rutas para facturas recurrentes — thin controller
  symbols: async def list_recurring_invoices(request, db, current_user); async def create_recurring_invoice(request, payload, db, current_user); async def update_recurring_invoice(request, rec_id, payload, db, current_user); async def delete_recurring_invoice(request, rec_id, db, current_user); async def run_recurring_invoice(request, rec_id, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/billing/__init__.py
`backend/app/api/v1/routes/reports/__init__.py` (python, 21 loc) — Reports API package…
  imports: fastapi
  → usa: backend/app/api/v1/routes/reports/fiscal.py, backend/app/api/v1/routes/reports/snapshot.py, backend/app/api/v1/routes/reports/specialized.py
`backend/app/api/v1/routes/reports/_schemas.py` (python, 15 loc) — Re-exports report schemas from the services layer (canonical location)
  imports: app
  → usa: backend/app/services/reports/_schemas.py
`backend/app/api/v1/routes/reports/fiscal.py` (python, 141 loc) — Fiscal snapshot GET + POST generate + modelo 303 + libro registro endpoints
  symbols: async def get_fiscal_snapshot(period, db, current_user); async def generate_fiscal_snapshot_pdf(period, db, current_user, tenant); async def generate_modelo_303(quarter, year, db, current_user); async def get_modelo_303_expediente(quarter, year, db, current_user); async def export_libro_registro(year, type, db, current_user)
  imports: app, datetime, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/pdf/__init__.py, backend/app/services/pdf_reports/__init__.py, backend/app/services/reports/__init__.py, backend/app/api/v1/routes/reports/_schemas.py
`backend/app/api/v1/routes/reports/snapshot.py` (python, 128 loc) — Company snapshot GET + POST generate + report management (list, download, delete)
  symbols: async def get_company_snapshot(month, db, current_user); async def generate_company_snapshot_pdf(month, db, current_user); async def list_reports(db, current_user); async def download_report(report_id, db, current_user); async def delete_report(report_id, db, current_user)
  imports: app, datetime, fastapi, sqlalchemy, uuid
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/documents/snapshot.py, backend/app/services/pdf/__init__.py, backend/app/services/reports/__init__.py, backend/app/api/v1/routes/reports/_schemas.py
`backend/app/api/v1/routes/reports/specialized.py` (python, 142 loc) — Cashflow + delinquency + compliance RGPD endpoints
  symbols: async def generate_cashflow(start, end, db, current_user); async def generate_delinquency(db, current_user); async def generate_rgpd_registry(db, current_user, tenant)
  imports: app, datetime, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/pdf/__init__.py, backend/app/services/reports/__init__.py
`backend/app/api/v1/routes/sales_orders.py` (python, 79 loc) — Rutas Sales Orders — thin controller para pedidos de venta
  symbols: async def list_sales_orders(request, db, current_user); async def create_sales_order(request, payload, db, current_user); async def update_sales_order(request, order_id, payload, db, current_user); async def delete_sales_order(request, order_id, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/sales/__init__.py
`backend/app/api/v1/routes/scanner.py` (python, 154 loc) — Scanner / Gatekeeper — Endpoints para escáner móvil de almacén…
  symbols: async def generate_qr_token(request, payload, current_user); async def scanner_whoami(scanner); async def scan_product(request, payload, scanner, db); async def stock_entry(request, payload, scanner, db); async def stock_exit(request, payload, scanner, db); async def confirm_delivery(request, payload, scanner, db)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/middleware/rate_limit.py, backend/app/middleware/scanner_auth.py, backend/app/services/documents/__init__.py
`backend/app/api/v1/routes/search.py` (python, 91 loc)
  symbols: async def global_search(q, db, current_user)
  imports: app, fastapi, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/hr.py
`backend/app/api/v1/routes/signing.py` (python, 162 loc) — Rutas de firma electrónica AutoFirma (F3.11)
  symbols: def _default_servlet_url(path); async def init_autofirma(request, payload, db, current_user); async def get_autofirma_status(session_token, db, current_user); async def autofirma_callback(request, db)
  imports: __future__, app, base64, fastapi, sqlalchemy, uuid
  → usa: backend/app/core/config.py, backend/app/core/dependencies.py, backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/middleware/rate_limit.py, backend/app/services/signing/__init__.py
`backend/app/api/v1/routes/system.py` (python, 233 loc) — System routes — frontend error reporting, diagnostics, backups
  symbols: class FrontendError; async def report_frontend_error(payload, request); class BackupItem; class RestoreResult; class RunBackupResult; async def list_backups_endpoint(); async def run_backup_endpoint(); async def download_backup_endpoint(filename); async def restore_backup_endpoint(filename); async def delete_backup_endpoint(filename); async def get_invoice_preconditions(db); async def require_invoice_preconditions(db) … (+4)
  imports: app, fastapi, logging, pydantic, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/__init__.py, backend/app/services/billing/backfill_verifactu.py, backend/app/services/system/diagnostic_bundle.py, backend/app/services/system/preconditions.py
`backend/app/api/v1/routes/tasks.py` (python, 189 loc) — Rutas CRUD de tareas del orquestador
  symbols: async def create_task(request, payload, background_tasks, db, current_user); async def list_tasks(request, skip, limit, status_filter, db, current_user); async def cleanup_tasks(request, db, current_user); async def get_task(request, task_id, db, current_user); async def cancel_task(request, task_id, db, current_user); async def get_task_cost(task_id, db, current_user); async def stream_task_events(task_id, db, current_user); async def get_task_audit(request, task_id, db, current_user)
  imports: app, fastapi, json, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/workflow/__init__.py, backend/app/services/workflow/task_event_hub.py
`backend/app/api/v1/routes/telemetry.py` (python, 106 loc) — Endpoints de gestión de telemetría (AI.REV)…
  symbols: class TelemetryStatusResponse; class RevokeResponse; async def get_my_telemetry_status(user, db); async def revoke_my_telemetry(user, db)
  imports: app, datetime, fastapi, pydantic, sqlalchemy
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py
`backend/app/api/v1/routes/templates.py` (python, 145 loc) — Endpoints para gestion de plantillas de documentos (facturas, nominas, excel)…
  symbols: async def list_templates(request, template_type, db, current_user); async def create_template(request, payload, db, current_user); async def update_template(request, template_id, payload, db, current_user); async def delete_template(request, template_id, db, current_user); async def set_default(request, template_id, db, current_user); async def seed_defaults(request, template_type, db, current_user); async def preview_template(request, payload, current_user, db)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/middleware/rate_limit.py, backend/app/services/__init__.py
`backend/app/api/v1/routes/tenant.py` (python, 278 loc)
  symbols: async def get_tenant_me(request, db, current_user); async def update_tenant_me(request, payload, db, current_user); async def get_llm_config(request, db, current_user); async def update_llm_config(request, payload, db, current_user); async def claude_code_setup(request, current_user); async def claude_code_login(request, current_user); async def claude_code_logout(request, current_user); async def get_certificate_status(request, db, current_user); async def upload_certificate(request, file, password, db, current_user); async def delete_certificate(request, db, current_user); async def get_logo_status(request, db, current_user); async def upload_logo(request, file, db, current_user) … (+1)
  imports: app, fastapi, pathlib, sqlalchemy
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/__init__.py
`backend/app/api/v1/routes/treasury.py` (python, 406 loc) — Rutas de tesorería (F2.7) — proyección cashflow + remesas SEPA
  symbols: def _remittance_to_dict(r); def _parse_uuid(value); async def get_cashflow_projection(request, days_ahead, db, current_user); async def generate_pain001(request, payload, db, current_user); async def download_pain001(request, payload, db, current_user); async def generate_pain008(request, payload, db, current_user); async def get_remittances(request, status_filter, limit, offset, db, current_user); async def get_remittance_detail(request, remittance_id, db, current_user); async def download_remittance_xml(request, remittance_id, db, current_user); async def change_remittance_status(request, remittance_id, payload, db, current_user)
  imports: __future__, app, datetime, decimal, fastapi, sqlalchemy, uuid
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/middleware/rate_limit.py, backend/app/services/treasury/__init__.py, backend/app/services/treasury/sepa.py
`backend/app/api/v1/routes/users.py` (python, 310 loc) — Users management endpoints
  symbols: class UserOut; class UserCreate; class UserUpdate; def _user_out(u); async def list_users(db, current_user); async def get_me(current_user); async def create_user(payload, db, current_user); class InvitationCreate; class InvitationOut; class InvitationCreateResponse; class InvitationPublic; class InvitationAccept … (+10)
  imports: app, datetime, fastapi, logging, pydantic, sqlalchemy, uuid
  → usa: backend/app/core/datetime_utils.py, backend/app/core/dependencies.py, backend/app/core/security.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/__init__.py
`backend/app/api/v1/routes/verifactu_config.py` (python, 69 loc) — Rutas REST de configuración del modo Verifactu (FAC.MODE)
  symbols: class VerifactuConfigOut; async def get_endpoint(user, db); class SetModeIn; async def put_endpoint(payload, user, db)
  imports: __future__, app, fastapi, pydantic, sqlalchemy, typing
  → usa: backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/auth.py, backend/app/services/billing/verifactu_mode.py
`backend/app/api/v1/routes/verify.py` (python, 67 loc) — Endpoint público de verificación Verifactu (FAC.QR)…
  symbols: async def verify_invoice_by_huella(huella, db)
  imports: app, fastapi, sqlalchemy
  → usa: backend/app/db/base.py, backend/app/db/models/billing.py, backend/app/services/billing/verifactu_chain.py
`backend/app/api/v1/routes/warehouses.py` (python, 56 loc) — Almacenes / tiendas (multi-almacén, capa 1)
  symbols: async def list_warehouses(request, db, current_user); async def create_warehouse(request, payload, db, current_user); async def update_warehouse(request, warehouse_id, payload, db, current_user)
  imports: app, fastapi, logging, sqlalchemy, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/middleware/rate_limit.py, backend/app/services/inventory/__init__.py
`backend/app/api/v1/routes/workflows.py` (python, 259 loc) — Rutas para Workflows & Automatizaciones — thin controller
  symbols: async def list_workflows(request, current_user, db); async def recent_completions(request, since, current_user, db); async def create_workflow(request, workflow_in, current_user, db); async def seed_defaults(request, current_user, db); async def get_workflow(request, workflow_id, current_user, db); async def update_workflow(request, workflow_id, workflow_in, current_user, db); async def delete_workflow(request, workflow_id, current_user, db); async def run_workflow_manually(request, workflow_id, background_tasks, current_user, db); async def cancel_execution(request, workflow_id, execution_id, current_user, db); async def run_workflow_with_context(request, workflow_id, body, background_tasks, current_user, db); async def resume_execution(request, workflow_id, execution_id, current_user, db); async def get_execution_logs(request, workflow_id, execution_id, current_user, db) … (+3)
  imports: app, fastapi, logging, sqlalchemy, typing, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/core/dependencies.py, backend/app/db/base.py, backend/app/db/models/__init__.py, backend/app/middleware/rate_limit.py, backend/app/services/workflow/__init__.py
`backend/app/api/v1/schemas/accounting.py` (python, 85 loc)
  symbols: class JournalLineBase; class JournalLineCreate; class JournalLineResponse; class JournalEntryBase; class JournalEntryCreate; class JournalEntryResponse; class FixedAssetBase; class FixedAssetCreate; class FixedAssetUpdate; class FixedAssetResponse
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/ai_employees.py` (python, 97 loc) — Schemas Pydantic para empleados IA y activity feed
  symbols: class AIEmployeeOut; class AIEmployeeCreate; class AIEmployeeProvision; class AIEmployeeIconUpdate; class AIEmployeeAppearanceUpdate; class AIEmployeeBudgetUpdate; class InstructPayload; class ActivityEntryOut; class ActivityEntryCreate
  imports: pydantic
`backend/app/api/v1/schemas/albaranes.py` (python, 55 loc) — Pydantic schemas for albaranes (delivery notes)
  symbols: class DeliveryNoteLineCreate; class DeliveryNoteCreate; class DeliveryNoteStatusUpdate; class DeliveryNoteLineResponse; class DeliveryNoteResponse
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/approvals.py` (python, 6 loc) — Schemas de aprobaciones — re-exportados desde tasks para mantener coherencia
  imports: app
  → usa: backend/app/api/v1/__init__.py
`backend/app/api/v1/schemas/auth.py` (python, 70 loc) — Schemas Pydantic para autenticación y usuarios
  symbols: class LoginRequest; class TokenResponse; class RefreshRequest; class TenantOut; class UserOut; class ForgotPasswordRequest; class ResetPasswordRequest
  imports: app, datetime, pydantic, uuid
  → usa: backend/app/services/auth/_schemas.py
`backend/app/api/v1/schemas/banking.py` (python, 21 loc)
  symbols: class TransactionReconcile; class BankTransactionResponse
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/crm.py` (python, 112 loc)
  symbols: class OpportunityBase; class OpportunityCreate; class OpportunityUpdate; class OpportunityResponse; class ActivityBase; class ActivityCreate; class ActivityResponse; class EventBase; class EventCreate; class EventResponse; class ReservationBase; class ReservationCreate … (+3)
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/documents.py` (python, 101 loc) — Schemas Pydantic para gestión documental
  symbols: class DocumentOut; class ScanResultOut; class ImportDBOut; class ContractTemplateOut; class ContractPreviewHtmlOut; class ContractBodyHtmlIn; class ContractChatMsg; class ContractInterviewIn; class ContractInterviewOut; class ContractSaveIn; class SemanticSearchHit; class DocumentContentUpdate … (+1)
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/erp.py` (python, 375 loc)
  symbols: class ClientCreate; class ClientResponse; class ProductCreate; class ProductResponse; class InvoiceLineCreate; class InvoiceLineResponse; class ClientUpdate; class ProductUpdate; class InvoiceStatusUpdate; class InvoiceCreate; class InvoiceResponse; class StockMovementCreate … (+17)
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/generative_ui.py` (python, 28 loc) — Schemas Pydantic para Generative UI
  symbols: class GenerateRequest; class GeneratedUIOut; class UpdateUIRequest
  imports: pydantic
`backend/app/api/v1/schemas/hr.py` (python, 272 loc)
  symbols: class EmployeeBase; class EmployeeCreate; class EmployeeUpdate; class EmployeeResponse; class ScheduleDay; class ScheduleUpsert; class ScheduleAISuggestRequest; class ClockInRequest; class AttendanceResponse; class ExpenseCreate; class ExpenseUpdate; class ExpenseResponse … (+14)
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/hr_documents.py` (python, 28 loc) — Pydantic schemas for HR Documents endpoints
  symbols: class GenerateRequest; class HRDocumentOut
  imports: datetime, pydantic
`backend/app/api/v1/schemas/integrations.py` (python, 25 loc) — Schemas Pydantic para integraciones
  symbols: class IntegrationStatusOut; class Psd2ConnectRequest; class EmailConnectRequest
  imports: pydantic
`backend/app/api/v1/schemas/labels.py` (python, 16 loc) — Schemas de impresión de etiquetas
  symbols: class LabelItem; class LabelsRequest
  imports: pydantic, uuid
`backend/app/api/v1/schemas/lots.py` (python, 24 loc) — Schemas para la gestión de lotes de producto
  symbols: class LotCreate; class LotUpdate
  imports: datetime, pydantic
`backend/app/api/v1/schemas/messaging.py` (python, 10 loc) — Pydantic schemas for messaging routes
  symbols: class TelegramConnectResponse
  imports: pydantic
`backend/app/api/v1/schemas/pos.py` (python, 58 loc) — Schemas Pydantic para TPV (Punto de Venta)
  symbols: class PosLineAdd; class PosLineUpdate; class PosLineResponse; class PosSessionResponse; class PosCheckoutRequest
  imports: datetime, pydantic, typing, uuid
`backend/app/api/v1/schemas/projects.py` (python, 69 loc)
  symbols: class ProjectBase; class ProjectCreate; class ProjectUpdate; class ProjectResponse; class ProjectTaskBase; class ProjectTaskCreate; class ProjectTaskUpdate; class ProjectTaskResponse
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/receiving.py` (python, 19 loc) — Schemas de recepción de mercancía contra pedido de compra
  symbols: class ReceiveLine; class ReceiveRequest
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/recruitment.py` (python, 54 loc) — Pydantic schemas for recruitment endpoints
  symbols: class PositionCreate; class PositionResponse; class CandidateResponse; class StatusUpdate
  imports: pydantic, uuid
`backend/app/api/v1/schemas/sales.py` (python, 69 loc)
  symbols: class QuoteLineBase; class QuoteLineCreate; class QuoteLineResponse; class QuoteBase; class QuoteCreate; class QuoteUpdate; class QuoteResponse
  imports: datetime, pydantic, uuid
`backend/app/api/v1/schemas/scanner.py` (python, 34 loc) — Pydantic schemas for the Scanner module
  symbols: class GenerateQRRequest; class ScanProductRequest; class StockMovementRequest; class ConfirmDeliveryRequest
  imports: datetime, pydantic
`backend/app/api/v1/schemas/tasks.py` (python, 79 loc) — Schemas Pydantic para Tasks, AuditLog y Aprobaciones
  symbols: class TaskCreate; class TaskOut; class AuditLogOut; class ApprovalDecision; class PendingApprovalOut
  imports: app, datetime, pydantic, typing, uuid
  → usa: backend/app/agents/types.py
`backend/app/api/v1/schemas/templates.py` (python, 58 loc) — Pydantic schemas for document template endpoints
  symbols: class TemplateCreate; class TemplateUpdate; class TemplateResponse; class PreviewRequest
  imports: pydantic, uuid
`backend/app/api/v1/schemas/tenant.py` (python, 52 loc)
  symbols: class TenantMeResponse; class TenantMeUpdate; class LlmConfigUpdate; class LlmConfigResponse; class ClaudeCodeSetupResponse
  imports: app, pydantic, typing, uuid
  → usa: backend/app/services/_tenant_schemas.py
`backend/app/api/v1/schemas/warehouse.py` (python, 31 loc) — Schemas de almacenes (multi-almacén)
  symbols: class WarehouseCreate; class WarehouseUpdate; class StockTransferRequest
  imports: pydantic, uuid
`backend/app/api/v1/schemas/workflows.py` (python, 101 loc)
  symbols: class WorkflowBase; class WorkflowCreate; class WorkflowParseRequest; class WorkflowParseResponse; class WorkflowUpdate; class WorkflowResponse; class WorkflowExecutionBase; class WorkflowExecutionResponse
  imports: datetime, pydantic, typing, uuid
`backend/app/api/ws/notifications.py` (python, 96 loc)
  symbols: class ConnectionManager {__init__, connect, disconnect, send_personal_message, broadcast_to_tenant}; async def get_token_tenant(token); async def websocket_endpoint(websocket, token)
  imports: app, fastapi, jose, logging
  → usa: backend/app/core/config.py
`backend/app/celery_app.py` (python, 53 loc) — Celery application factory…
  symbols: def _make_celery()
  imports: __future__, logging
`backend/app/core/__init__.py` (python, 1 loc)
`backend/app/core/config.py` (python, 185 loc)
  symbols: class Settings {check_secrets}; def get_settings(); def frontend_origin()
  imports: functools, logging, pathlib, pydantic, pydantic_settings
`backend/app/core/datetime_utils.py` (python, 36 loc) — Helpers compartidos para manejo de datetime…
  symbols: def as_aware(dt, default_tz)
  imports: datetime
`backend/app/core/dependencies.py` (python, 162 loc)
  symbols: def _employee_can_access(path); async def get_current_user(request, credentials, db); async def get_current_tenant(current_user); async def get_tenant_or_404(current_user, db); async def get_current_client_portal(credentials, db); def require_role()
  imports: app, fastapi, sqlalchemy, uuid
  → usa: backend/app/core/security.py, backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/crm.py, backend/app/db/models/models.py, backend/app/services/__init__.py
`backend/app/core/exceptions.py` (python, 73 loc) — Jerarquia de excepciones tipadas para respuestas estructuradas
  symbols: class AppException {__init__}; class NotFoundError {__init__}; class ValidationError {__init__}; class ConflictError {__init__}; class ForbiddenError {__init__}; class ExternalServiceError {__init__}; class OrchestratorTimeoutError {__init__}
  imports: __future__
`backend/app/core/license.py` (python, 294 loc) — Validación de licencia contra el servidor externo…
  symbols: def _verify_server_sig(nonce, plan, sig_b64); def get_machine_id(); def _sign(payload, machine_id); def _cache_payload(key, plan, last_validated, machine_id); def _read_cache(); def _write_cache(data); def _verify_cache(cache, machine_id); def get_stored_key(); def save_license(key, plan); class LicenseResult {__init__}; def cached_license_state(); async def validate_license() … (+3)
  imports: app, base64, cryptography, datetime, hashlib, hmac, httpx, json, logging, platform, secrets, uuid
  → usa: backend/app/core/paths.py
`backend/app/core/llm/claude_code.py` (python, 784 loc) — ClaudeCodeChatModel — LangChain wrapper para Claude Code CLI (suscripcion VSCode/Pro)…
  symbols: class LLMRefusedToolUseError; class LLMToolFormatError; def _resolve_claude_bin(); def _clean_env(); def _neutral_cwd(); async def _spawn_process(); def _parse_cli_output(raw); def _tools_to_schema(tools); def _is_write_tool_name(name); def _build_tool_system_prompt(tools); def _extract_json_from_text(text); def _escape_control_chars_in_json_strings(s) … (+3)
  imports: asyncio, json, langchain_core, logging, os, pydantic, re, shutil, typing, uuid
`backend/app/core/llm/mock.py` (python, 396 loc) — LLM simulado para testing y desarrollo sin API keys…
  symbols: class MockChatModel {_llm_type, bind_tools, with_structured_output, _generate, _agenerate, _build_response, _multi_agent_plan, _classify_domain}
  imports: json, langchain_core, re, uuid
`backend/app/core/llm_callbacks.py` (python, 161 loc) — Callback de LangChain para tracking de uso de tokens por tenant/agente…
  symbols: class UsageTrackingCallback {__init__, on_llm_start, on_chat_model_start, on_llm_end}; def get_langfuse_callback(tenant_id, agent, task_id); def _extract_tokens(response)
  imports: app, langchain_core, logging, typing
  → usa: backend/app/core/config.py, backend/app/services/__init__.py
`backend/app/core/llm_factory.py` (python, 459 loc) — Fábrica centralizada de LLMs…
  symbols: def _mock_fallback(); def set_tenant_llm_context(llm, provider); def _resolve_active_provider(); def make_cached_system_message(text); def get_llm(temperature, format_output, provider, max_tokens); def get_llm_with_fallback(temperature, provider); async def get_llm_for_tenant(tenant_id, db, temperature, format_output); def get_embedder(); def _try_openai_fallback(temperature, format_output, max_tokens); def _try_groq_fallback(temperature, max_tokens); def _build_groq(temperature, format_output, max_tokens, base_fallbacks, mock_fallback); def _build_anthropic(temperature, format_output, max_tokens, base_fallbacks, mock_fallback) … (+2)
  imports: app, contextvars, functools, langchain_core, langchain_openai, logging, sqlalchemy
  → usa: backend/app/core/config.py, backend/app/core/__init__.py, backend/app/core/llm_trace.py
`backend/app/core/llm_trace.py` (python, 293 loc) — Callback que registra cada llamada LLM en un fichero JSONL para debug post-mortem…
  symbols: def _truncate(value, limit); def _serialize_message(msg); def _serialized_model_name(serialized); class LLMTraceCallback {__init__, _today_path, _write, on_chat_model_start, on_llm_start, on_llm_end, on_llm_error}; def is_enabled(); def get_trace_callback(); def attach_to(llm)
  imports: __future__, datetime, json, langchain_core, logging, os, pathlib, threading, time, typing, uuid
`backend/app/core/net.py` (python, 23 loc) — Utilidades de red: distinguir peticiones locales de las que llegan por la LAN o a través del proxy de acceso remoto (Cloudflare Tunnel)
  symbols: def is_local_request(request)
  imports: starlette
`backend/app/core/observability.py` (python, 364 loc) — Capa de observabilidad — Fase 3…
  symbols: class StructuredFormatter {format}; def get_logger(name); def _get_langfuse(); def trace_llm_call(name, agent, tenant_id, task_id, trace_id, metadata); def record_task_metric(event, tenant_id, domain, status); def record_llm_latency(agent, duration_seconds, model); def record_tool_execution(tool, status, duration_seconds); def record_agent_run(agent, status, duration_seconds); def set_approvals_pending(tenant_id, count); def record_http_request(method, path, status_code, duration_seconds); def ws_connection_opened(); def ws_connection_closed() … (+1)
  imports: app, collections, contextlib, json, logging, time, typing, uuid
  → usa: backend/app/core/config.py
`backend/app/core/paths.py` (python, 40 loc) — Directorio de datos de la app (fuente única de verdad)…
  symbols: def app_data_dir()
  imports: __future__, os, pathlib, sys
`backend/app/core/prompt_sanitizer.py` (python, 38 loc) — Sanitizador de inputs de usuario antes de enviarlos al LLM…
  symbols: def sanitize_user_input(text, max_length)
  imports: re
`backend/app/core/request_context.py` (python, 47 loc) — Request context — ContextVar para el request_id de la petición HTTP actual…
  symbols: def set_current_request_id(request_id); def get_current_request_id(); def request_context(request_id)
  imports: __future__, collections, contextlib, contextvars
`backend/app/core/security.py` (python, 97 loc)
  symbols: def mask_iban(value); def verify_password(plain_password, hashed_password); def get_password_hash(password); def create_access_token(data, expires_delta); def create_refresh_token(data); def create_client_portal_access_token(client_id, tenant_id); def decode_token(token)
  imports: app, bcrypt, datetime, jose, re
  → usa: backend/app/core/config.py
`backend/app/core/structured_logging.py` (python, 125 loc) — Logger JSON estructurado (CONT.LOG)…
  symbols: class JSONFormatter {__init__, format}; def get_log_dir(); def setup_structured_logging()
  imports: app, datetime, json, logging, pathlib
  → usa: backend/app/core/telemetry_scrubber.py
`backend/app/core/telemetry_scrubber.py` (python, 135 loc) — Scrubber de telemetría (AI.SCR) — protege privacidad antes de enviar a Sentry…
  symbols: def scrub_text(text); def hash_tenant_id(tenant_id, salt); def scrub_event(event)
  imports: __future__, hashlib, re, typing
`backend/app/core/tenant_context.py` (python, 128 loc) — Tenant context — fuente de verdad única del tenant activo en el contexto async…
  symbols: def set_current_tenant(tenant_id); def get_current_tenant(); def set_current_task(task_id); def get_current_task(); def require_current_tenant(); def is_rls_bypass(); def rls_bypass(); def tenant_context(tenant_id)
  imports: __future__, collections, contextlib, contextvars
`backend/app/db/__init__.py` (python, 1 loc)
`backend/app/db/base.py` (python, 51 loc)
  symbols: class Base; async def get_db()
  imports: app, sqlalchemy
  → usa: backend/app/core/config.py, backend/app/db/rls.py
`backend/app/db/migrations/env.py` (python, 99 loc)
  symbols: def run_migrations_offline(); def run_migrations_online()
  imports: alembic, logging, os, pathlib, sqlalchemy
`backend/app/db/migrations/versions/0001_initial_squashed.py` (python, 1467 loc) — Initial squashed migration - replaces all 44 original migrations Revision ID: 0001_initial_squash Revises: (none) Create Date: 2026-04-23 Th…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0002_add_cross_domain_accounting_fks.py` (python, 85 loc) — Add cross-domain accounting foreign keys…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0003_create_document_embeddings_jsonb.py` (python, 77 loc) — Create document_embeddings table with JSONB embedding (no pgvector)…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0004_tenant_logo_and_pdf_report_skill.py` (python, 60 loc) — Add tenant logo support and inject reports.create_pdf_report skill…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0005_backfill_pdf_text_report_skill.py` (python, 43 loc) — Backfill the reports.create_pdf_text_report skill for every AIEmployee…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0006_employees_unique_nif_per_tenant.py` (python, 38 loc) — Unique NIF per tenant for employees (case-insensitive)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0007_payrolls_unique_period.py` (python, 42 loc) — Unique payroll per (tenant, employee, period_start)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0008_drop_candidate_ai_act_columns.py` (python, 40 loc) — Drop Candidate.score and Candidate.score_breakdown (AI Act compliance)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0009_create_user_invitations.py` (python, 49 loc) — Create user_invitations table (move from _ensure_schema to Alembic)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0011_verifactu_chain.py` (python, 93 loc) — Create verifactu_chain table — append-only registry per RD 1007/2023…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0012_sec_worm_audit.py` (python, 107 loc) — SEC.WORM — append-only enforced para audit_log y agent_execution_trace…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0013_fiscal_approval_log.py` (python, 83 loc) — SEC.APR — Crea fiscal_approval_log append-only para actos fiscales AEAT…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0014_telemetry_opt_out.py` (python, 35 loc) — AI.REV — Crea telemetry_opt_out (RGPD Art…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0015_metering.py` (python, 66 loc) — OPS.OVR + OPS.CRON — Tablas de metering para billing + cron caps…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0016_sec_rls.py` (python, 96 loc) — SEC.RLS — Row-Level Security en Postgres con `app.current_tenant`…
  symbols: def _enable_rls_sql(table); def _disable_rls_sql(table); def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0017_backup_records.py` (python, 78 loc) — BAK.LOC + BAK.VF — Tabla de registro de backups locales del cliente…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0018_verifactu_backfill_flag.py` (python, 62 loc) — Add is_backfilled flag and backfilled_at to verifactu_chain (A.5)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0019_tenant_regap_status.py` (python, 54 loc) — Create tenant_regap_status — estado del apoderamiento REGAP por tenant…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0020_autonomy_policy.py` (python, 54 loc) — Create autonomy_policy — política de autonomía por dominio (SEC.AUT)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0021_tenant_onboarding.py` (python, 52 loc) — Create tenant_onboarding — wizard 4 pasos de UI.ONB…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0022_notifications.py` (python, 57 loc) — Create notifications — bandeja persistente cross-session (UI.NOT)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0023_verifactu_config.py` (python, 47 loc) — Create verifactu_config — modo de remisión por tenant (FAC.MODE)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0024_inventory_extensions.py` (python, 79 loc) — INV.EXT — Extensión de inventario: barcode, coste, unidad, soft-delete, trazabilidad…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0025_pos_sessions.py` (python, 114 loc) — POS.SESSIONS — TPV: sesiones de venta y líneas de carrito…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0026_product_location.py` (python, 31 loc) — INV.LOC — Ubicación física del producto en almacén…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0027_tasks_is_deleted.py` (python, 45 loc) — Soft-delete en tasks — bug cleanup vs WORM audit_log (lessons 2026-05-19)…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0028_clients_unique_nif_per_tenant.py` (python, 72 loc) — UNIQUE(tenant_id, nif) en clients — cerrar race en upsert de billing…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0029_aiemployee_contract.py` (python, 77 loc) — Contrato mínimo del AIEmployee custom — capacidades verificables…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0030_accounting_periods.py` (python, 52 loc) — Crear tabla accounting_periods para cierre contable mensual/trimestral…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0031_aeat_presentation.py` (python, 97 loc) — Custodia de certificado digital del cliente + registro de presentaciones AEAT…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0032_employee_memory_and_rag_scope.py` (python, 97 loc) — Memoria persistente del AIEmployee + filtro RAG por employee…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy, uuid
`backend/app/db/migrations/versions/0033_supplier_invoice_templates.py` (python, 107 loc) — Templates de proveedor + cache de escaneos para OCR con aprendizaje…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy, uuid
`backend/app/db/migrations/versions/0034_reconciliation_rejections.py` (python, 65 loc) — Rechazos persistentes de sugerencias de conciliación bancaria (F2.6)…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy, uuid
`backend/app/db/migrations/versions/0035_workflow_templates.py` (python, 62 loc) — Marketplace de workflows (F3.10) — plantillas curadas reutilizables…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy, uuid
`backend/app/db/migrations/versions/0036_signed_documents.py` (python, 74 loc) — Firma eIDAS con AutoFirma del Estado (F3.11)…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy, uuid
`backend/app/db/migrations/versions/0037_llm_usage_monthly.py` (python, 59 loc) — Persistencia del consumo LLM agregado (snapshot del tracker en memoria)…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy, uuid
`backend/app/db/migrations/versions/0038_workflow_execution_notified.py` (python, 33 loc) — Flag `notified` en workflow_executions para el alertado de fallos…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0039_payroll_cuota_solidaridad.py` (python, 35 loc) — Columna `cuota_solidaridad` en payrolls (parte trabajador)…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0040_invoice_rectificativa.py` (python, 51 loc) — Campos de factura rectificativa en `invoices`…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0041_invoice_unique_number_emitted.py` (python, 40 loc) — Índice UNIQUE parcial del número de factura para las emitidas…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0042_document_source_entity.py` (python, 51 loc) — Procedencia y enlace a entidad en `tenant_documents`…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0043_product_lots.py` (python, 52 loc) — LOTES FEFO — Tabla product_lots para trazabilidad por lote y caducidad…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0044_warehouses.py` (python, 107 loc) — MULTI-ALMACÉN (capa 1) — almacenes, stock por almacén y warehouse_id…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0045_product_stock_default_derived.py` (python, 34 loc) — MULTI-ALMACÉN (capa 2) — el stock del almacén por defecto se deriva…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0046_product_reorder.py` (python, 32 loc) — REPOSICIÓN — proveedor habitual y cantidad de reposición por producto…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0047_po_received_quantity.py` (python, 27 loc) — RECEPCIÓN — cantidad recibida por línea de pedido de compra…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0048_marketing_social.py` (python, 75 loc) — Marketing: social_accounts, marketing_campaigns, scheduled_posts…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0049_email_marketing.py` (python, 69 loc) — Email marketing: email_templates, email_campaigns, email_campaign_recipients…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0050_post_retry_count.py` (python, 24 loc) — Marketing: scheduled_posts.retry_count para reintentos con backoff…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0051_employee_pagas.py` (python, 28 loc) — HR: employees.num_pagas y prorratear_pagas (pagas extra 12/14)…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0052_sepa_remittances.py` (python, 73 loc) — Tesorería: tablas sepa_remittances y sepa_remittance_orders…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0053_invoice_fiscal_regime.py` (python, 31 loc) — Fiscal: régimen especial + retención IRPF Art.95 en invoices…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0054_client_mkt_consent.py` (python, 24 loc) — CRM: clients.marketing_consent — opt-in RGPD para email marketing…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0055_work_sched_uq.py` (python, 46 loc) — Constraint única (employee_id, day_of_week) en work_schedules…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0056_idempotency_keys.py` (python, 29 loc) — Tabla idempotency_keys — claves de idempotencia persistentes del scheduler…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0057_scheduled_post_metrics.py` (python, 50 loc) — Tabla scheduled_post_metrics — analítica de posts de marketing…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0058_hr_document_number.py` (python, 24 loc) — Folio correlativo de documentos de gestoría — hr_documents.doc_number…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0059_onboarding_llm_step.py` (python, 31 loc) — Paso BYOK en el wizard de onboarding — tenant_onboarding.step_llm_config…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0060_app_role_rls.py` (python, 71 loc) — SEC.RLS Fase B — rol de aplicación no-superusuario + policies simétricas…
  symbols: def upgrade(); def downgrade()
  imports: alembic, app, sqlalchemy
  → usa: backend/app/db/security_bootstrap.py
`backend/app/db/migrations/versions/0061_document_embeddings_fk.py` (python, 79 loc) — Integridad RAG — FK document_embeddings.document_id -> tenant_documents(id) CASCADE…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0062_marketing_provider_config.py` (python, 44 loc) — Marketing BYO Zernio: marketing_provider_config (multi-cuenta por tenant) + social_accounts.provider_config_id…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0063_drop_social_account_tokens.py` (python, 29 loc) — Marketing BYO: retira las columnas de token OAuth de social_accounts…
  symbols: def upgrade(); def downgrade()
  imports: alembic
`backend/app/db/migrations/versions/0064_rls_fail_closed.py` (python, 77 loc) — SEC.RLS Fase C — endurece la RLS de fail-OPEN a fail-CLOSED…
  symbols: def upgrade(); def downgrade()
  imports: alembic, app
  → usa: backend/app/db/security_bootstrap.py
`backend/app/db/migrations/versions/0065_stock_writeoff_fields.py` (python, 45 loc) — Bajas de stock por rotura/merma: contador de cajas + motivo en movimientos…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/migrations/versions/0066_demo_data_flag.py` (python, 42 loc) — Flag is_demo en invoices/clients/products: datos de ejemplo del onboarding…
  symbols: def upgrade(); def downgrade()
  imports: alembic, sqlalchemy
`backend/app/db/models/__init__.py` (python, 65 loc) — Paquete de modelos SQLAlchemy…
  → usa: backend/app/db/models/accounting.py, backend/app/db/models/ai_employees.py, backend/app/db/models/alerts.py, backend/app/db/models/auth.py, backend/app/db/models/billing.py, backend/app/db/models/calendar.py, backend/app/db/models/crm.py, backend/app/db/models/email_marketing.py, backend/app/db/models/generative_ui.py, backend/app/db/models/hr.py (+15)
`backend/app/db/models/accounting.py` (python, 190 loc) — Modelos contables: Asientos, Transacciones bancarias e Inmovilizado
  symbols: class JournalEntry; class JournalLine; class BankTransaction; class FixedAsset; class AccountingPeriod; class TenantCertificate; class AeatPresentation
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/ai_employees.py` (python, 142 loc) — Modelos para el sistema de Empleados IA (AIEmployee)…
  symbols: class AIEmployee; class EmployeeMemory; class AgentSkill; class TokenLedger; class ActivityEntry
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/common.py
`backend/app/db/models/alerts.py` (python, 21 loc) — Registro de alertas automáticas disparadas por el scheduler
  symbols: class AlertLog
  → usa: backend/app/db/models/common.py
`backend/app/db/models/auth.py` (python, 170 loc) — Modelos de autenticación y tenancy
  symbols: class Tenant; class User; class ClientPortalToken; class PasswordResetToken; class UserInvitation; class TelemetryOptOut; class TenantRegapStatus
  → usa: backend/app/db/models/common.py
`backend/app/db/models/backup.py` (python, 39 loc) — Modelo de registro de backups locales (BAK.LOC + BAK.VF)
  symbols: class BackupRecord
  → usa: backend/app/db/models/common.py
`backend/app/db/models/billing.py` (python, 325 loc) — Modelos de facturacion: Facturas, Presupuestos y Recurrentes
  symbols: class InvoiceSeries; class Invoice; class VerifactuRecord; class VerifactuConfig; class InvoiceLine; class Quote; class QuoteLine; class RecurringInvoice; class DocumentTemplate; class DeliveryNote; class DeliveryNoteLine
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/calendar.py` (python, 58 loc) — Modelos de calendario: Eventos y Reservas
  symbols: class Event; class Reservation
  → usa: backend/app/db/models/common.py
`backend/app/db/models/common.py` (python, 46 loc) — Imports y utilidades compartidas por todos los modelos de dominio
  symbols: def utcnow()
  imports: app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/base.py
`backend/app/db/models/crm.py` (python, 97 loc) — Modelos CRM: Clientes, Oportunidades y Actividades
  symbols: class Client; class Opportunity; class Activity
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/email_marketing.py` (python, 75 loc)
  symbols: class EmailTemplate; class EmailCampaign; class EmailCampaignRecipient
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/embeddings.py` (python, 54 loc)
  symbols: class DocumentEmbedding
  imports: app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/base.py
`backend/app/db/models/generative_ui.py` (python, 27 loc) — Modelo de interfaz HTML generada por IA
  symbols: class GeneratedUI
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/hr.py` (python, 368 loc) — Modelos RRHH: Empleados, Nóminas, Finiquitos y Reclutamiento
  symbols: class Employee; class Payroll; class Settlement; class JornadaRecord; class RecruitmentPosition; class Candidate; class WorkSchedule; class Attendance; class Expense; class LeaveRequest
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/hr_documents.py` (python, 32 loc) — HR Documents model — labour documents generated by AI
  symbols: class HRDocument
  imports: app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/base.py
`backend/app/db/models/inventory.py` (python, 168 loc) — Modelos de inventario: Productos y Movimientos de stock
  symbols: class Product; class ProductLot; class StockMovement; class Warehouse; class ProductStock
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/llm_usage.py` (python, 48 loc) — Persistencia del consumo LLM agregado por tenant/mes/agente/proveedor…
  symbols: class LlmUsageMonthly
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/marketing.py` (python, 148 loc)
  symbols: class SocialAccount; class Campaign; class ScheduledPost; class ScheduledPostMetrics; class MarketingProviderConfig
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/metering.py` (python, 67 loc) — Metering — contadores mensuales de uso (OPS.OVR + OPS.CRON)
  symbols: class InteractionUsage; class CronExecutionUsage
  imports: sqlalchemy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/models.py` (python, 63 loc) — Re-exportador de compatibilidad…
  → usa: backend/app/db/models/accounting.py, backend/app/db/models/ai_employees.py, backend/app/db/models/auth.py, backend/app/db/models/billing.py, backend/app/db/models/calendar.py, backend/app/db/models/common.py, backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/db/models/inventory.py, backend/app/db/models/llm_usage.py (+5)
`backend/app/db/models/notifications.py` (python, 34 loc) — Modelos de notificaciones persistentes (UI.NOT)
  symbols: class Notification
  → usa: backend/app/db/models/common.py
`backend/app/db/models/orders.py` (python, 99 loc) — Modelos de pedidos: Ventas y Compras
  symbols: class SalesOrder; class SalesOrderLine; class PurchaseOrder; class PurchaseOrderLine
  → usa: backend/app/db/models/common.py
`backend/app/db/models/pos.py` (python, 76 loc) — Modelos de TPV (Punto de Venta)…
  symbols: class PosSession; class PosSessionLine
  → usa: backend/app/db/models/common.py
`backend/app/db/models/projects.py` (python, 62 loc) — Modelos de gestion de proyectos
  symbols: class Project; class ProjectTask
  → usa: backend/app/db/models/common.py
`backend/app/db/models/reconciliation.py` (python, 30 loc) — Rechazos persistentes de sugerencias de conciliación (F2.6)…
  symbols: class ReconciliationRejection
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/common.py
`backend/app/db/models/signed_document.py` (python, 38 loc) — Modelo de documento firmado vía AutoFirma del Estado (F3.11)
  symbols: class SignedDocument
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/common.py
`backend/app/db/models/supplier_learning.py` (python, 57 loc) — Modelos para aprendizaje OCR por proveedor (F2.5)…
  symbols: class InvoiceScanCache; class SupplierInvoiceTemplate
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/common.py
`backend/app/db/models/tasks.py` (python, 198 loc) — Modelos de tareas, auditoría y aprobaciones
  symbols: class Task; class AuditLog; class AgentExecutionTrace; class PendingApproval; class FiscalApprovalLog; class IdempotencyKey
  → usa: backend/app/db/models/common.py
`backend/app/db/models/tenant.py` (python, 137 loc) — Modelos de configuración del tenant: integraciones, conocimiento y documentos
  symbols: class TenantIntegration; class TenantKnowledge; class TenantLlmConfig; class TenantDocument; class TenantOnboarding; class AutonomyPolicy
  → usa: backend/app/db/models/common.py
`backend/app/db/models/treasury.py` (python, 83 loc) — Modelos de tesorería — remesas SEPA persistidas (pain.001 / pain.008)…
  symbols: class SepaRemittance; class SepaRemittanceOrder
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/common.py
`backend/app/db/models/workflow_template.py` (python, 35 loc) — Modelo de plantilla de workflow para el marketplace (F3.10)
  symbols: class WorkflowTemplate
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/common.py
`backend/app/db/models/workflows.py` (python, 94 loc) — Modelos de automatizacion: Workflows, Ejecuciones y Eventos de dominio
  symbols: class Workflow; class WorkflowExecution; class DomainEvent
  → usa: backend/app/db/models/common.py
`backend/app/db/rls.py` (python, 117 loc) — SQLAlchemy hooks para Row-Level Security Postgres (SEC.RLS)…
  symbols: def _desired_tenant(); def _desired_bypass(); def install_rls_listener(engine); async def apply_tenant_rls(session)
  imports: __future__, app, sqlalchemy, uuid
  → usa: backend/app/core/tenant_context.py
`backend/app/db/security_bootstrap.py` (python, 134 loc) — SEC.RLS — objetos de seguridad idempotentes (rol de app + policies RLS)…
  symbols: def ensure_app_role(connection, app_password); def ensure_rls_policies(connection); def ensure_security_objects(connection, app_password)
  imports: __future__, sqlalchemy
`backend/app/db/session.py` (python, 39 loc) — Sesión SQLAlchemy síncrona para uso en agentes LLM y scripts
  symbols: def _get_sync_url()
  imports: app, sqlalchemy
  → usa: backend/app/core/config.py, backend/app/db/rls.py
`backend/app/i18n/__init__.py` (python, 24 loc) — Internacionalización de strings backend (I18N.PDF + futuros emails)…
  → usa: backend/app/i18n/pdf_strings.py
`backend/app/i18n/pdf_strings.py` (python, 175 loc) — Strings i18n para PDFs (factura, nómina, recibo, modelos AEAT)…
  symbols: def get_locale_or_default(raw); def translate(key, locale); def known_keys()
  imports: __future__, typing
`backend/app/integrations/__init__.py` (python, 1 loc)
`backend/app/integrations/advisory_guides.py` (python, 187 loc) — Guías normativas estáticas para PYMEs españolas…
  symbols: def get_guides(section)
`backend/app/integrations/boe_scraper.py` (python, 379 loc) — Scraper del BOE (Boletín Oficial del Estado) para actualizaciones regulatorias…
  symbols: class BOEScraper {__init__, close, get_novedades, get_norma, _parse_rss}; def get_calendario_fiscal(year); def get_proximos_vencimientos(days_ahead, min_count)
  imports: datetime, httpx, xml
`backend/app/integrations/gmail_client.py` (python, 161 loc) — Gmail API client using OAuth access tokens
  symbols: class GmailClient {__init__, close, list_messages, get_message, get_message_body, send_message, search_messages, mark_read}; def _extract_body(payload)
  imports: base64, email, httpx
`backend/app/integrations/google_drive_client.py` (python, 117 loc) — Google Drive API client using OAuth access tokens
  symbols: class GoogleDriveClient {__init__, close, list_files, get_file_metadata, download_file, upload_file, create_folder, sync_document}
  imports: httpx
`backend/app/integrations/google_oauth.py` (python, 108 loc) — Google OAuth 2.0 client for Gmail + Google Drive
  symbols: def _client_id(); def _client_secret(); def _redirect_uri(); def _make_pkce(); def generate_auth_url(tenant_id); async def exchange_code(code, code_verifier); async def refresh_access_token(refresh_token)
  imports: app, base64, hashlib, httpx, secrets, urllib
  → usa: backend/app/core/config.py
`backend/app/integrations/microsoft_oauth.py` (python, 78 loc) — Microsoft OAuth 2.0 client for Outlook + OneDrive (Microsoft Graph)
  symbols: def _client_id(); def _client_secret(); def _redirect_uri(); def generate_auth_url(tenant_id); async def exchange_code(code); async def refresh_access_token(refresh_token)
  imports: app, httpx, secrets, urllib
  → usa: backend/app/core/config.py
`backend/app/integrations/onedrive_client.py` (python, 102 loc) — OneDrive / Microsoft Graph Files client using OAuth access tokens
  symbols: class OneDriveClient {__init__, close, list_files, download_file, upload_file, create_folder, sync_document, backup_invoice}
  imports: httpx
`backend/app/integrations/outlook_client.py` (python, 128 loc) — Outlook / Microsoft Graph Mail client using OAuth access tokens
  symbols: class OutlookClient {__init__, close, list_messages, get_message, send_message, mark_read, reply_message, search_messages}; def _normalize_message(m)
  imports: base64, httpx
`backend/app/integrations/psd2.py` (python, 226 loc) — Integración bancaria PSD2 usando Nordigen (GoCardless)…
  symbols: class NordigenClient {__init__, close, _get_access_token, _auth_headers, list_institutions, create_requisition, get_requisition, get_account_details}
  imports: datetime, httpx
`backend/app/integrations/telegram_client.py` (python, 133 loc) — Telegram Bot API client — enviar mensajes, gestionar webhook, parsear updates…
  symbols: class TelegramUpdate; class TelegramClient {__init__, close, send_message, send_typing, set_webhook, delete_webhook, get_webhook_info, get_me}
  imports: dataclasses, hmac, httpx, logging
`backend/app/main.py` (python, 370 loc) — Aplicación principal FastAPI
  symbols: async def lifespan(app); async def app_exception_handler(request, exc); async def global_exception_handler(request, exc); def _safe_import(module_name); async def metrics_endpoint(); async def health_check(); async def readiness_check(); async def lifecycle_shutdown(request); async def root()
  imports: app, asyncio, contextlib, fastapi, inspect, logging, slowapi, sys
  → usa: backend/app/api/v1/router.py, backend/app/core/config.py, backend/app/core/exceptions.py, backend/app/middleware/rate_limit.py, backend/app/middleware/license_check.py, backend/app/middleware/request_logger.py, backend/app/middleware/security_headers.py, backend/app/api/__init__.py
`backend/app/middleware/__init__.py` (python, 1 loc)
`backend/app/middleware/license_check.py` (python, 39 loc) — Middleware que bloquea peticiones si la licencia no es válida
  symbols: class LicenseCheckMiddleware {dispatch}
  imports: starlette
`backend/app/middleware/rate_limit.py` (python, 57 loc) — Rate limiting middleware usando slowapi (Starlette compatible)
  symbols: def _client_ip(request); def rate_limit_exceeded_handler(request, exc)
  imports: fastapi, slowapi, warnings
`backend/app/middleware/request_logger.py` (python, 82 loc) — Middleware de logging de requests con request_id y metricas
  symbols: class RequestLoggerMiddleware {__init__, __call__}
  imports: app, logging, starlette, time, uuid
  → usa: backend/app/core/observability.py, backend/app/core/request_context.py
`backend/app/middleware/scanner_auth.py` (python, 113 loc) — Scanner Auth — Middleware para tokens de escáner móvil…
  symbols: def create_scanner_token(tenant_id, user_id, device_name); def decode_scanner_token(token); async def get_scanner_user(request, credentials); def is_scanner_token(request)
  imports: app, datetime, fastapi, jwt, logging
  → usa: backend/app/core/config.py
`backend/app/middleware/security_headers.py` (python, 34 loc) — Middleware that adds security headers to every HTTP response
  symbols: class SecurityHeadersMiddleware {__init__, __call__}
  imports: app, starlette
  → usa: backend/app/core/config.py
`backend/app/prompts/__init__.py` (python, 20 loc) — Prompt loader — reads .txt files from the prompts/ folder
  symbols: def load_prompt(name)
  imports: functools, pathlib
`backend/app/services/__init__.py` (python, 1 loc)
`backend/app/services/_tenant_schemas.py` (python, 12 loc) — Schemas owned by the tenant service…
  symbols: class LlmProviderConfig
  imports: pydantic
`backend/app/services/accounting/__init__.py` (python, 28 loc) — Servicios contables — cierre de periodo y generación de libros oficiales
  imports: app
  → usa: backend/app/services/accounting/libros_pdf.py, backend/app/services/accounting/period_close.py
`backend/app/services/accounting/libros_pdf.py` (python, 408 loc) — Generadores PDF de Libros Contables Oficiales: Diario, Mayor, Balance, P&G…
  symbols: def _fmt_eur(v); def _fmt_date(d); async def _load_tenant(db, tenant_id); async def _entries_in_range(db, tenant_id, start, end); def _header_block(title, tenant_name, tenant_nif, periodo, styles); async def generate_libro_diario_pdf(db, tenant_id, start, end); async def generate_libro_mayor_pdf(db, tenant_id, start, end); async def generate_balance_pyg_pdf(db, tenant_id, start, end)
  imports: __future__, app, collections, datetime, decimal, io, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/accounting.py, backend/app/db/models/models.py
`backend/app/services/accounting/period_close.py` (python, 195 loc) — Cierre/reapertura de periodos contables + comprobación de bloqueo…
  symbols: class PeriodClosedError {__init__}; def _month_range(year, month); def _quarter_range(year, quarter); def contains_date(period, target); def _period_label(p); async def is_date_locked(db, tenant_id, target); async def list_periods(db, tenant_id, year); async def close_period(db, tenant_id, user_id, year, kind, period_index, notes); async def reopen_period(db, tenant_id, user_id, period_id, reason)
  imports: __future__, app, calendar, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/accounting.py
`backend/app/services/aeat/__init__.py` (python, 69 loc) — Servicios AEAT — generación + presentación electrónica de modelos fiscales…
  imports: app
  → usa: backend/app/services/aeat/casillas_303.py, backend/app/services/aeat/certificate_storage.py, backend/app/services/aeat/expediente_303.py, backend/app/services/aeat/modelo_303_xml.py, backend/app/services/aeat/modelo_xml_generico.py, backend/app/services/aeat/presentation_service.py, backend/app/services/aeat/sede_client.py, backend/app/services/aeat/xades_signer.py
`backend/app/services/aeat/_casilla.py` (python, 41 loc) — Dataclass y helpers compartidos para las casillas de los modelos AEAT…
  symbols: def round2(x); class Casilla {to_dict}
  imports: __future__, dataclasses, decimal
`backend/app/services/aeat/casillas_100.py` (python, 54 loc) — Mapeo del cálculo agregado del Modelo 100 a las casillas oficiales AEAT…
  symbols: def build_casillas_100(data)
  imports: __future__, app
  → usa: backend/app/services/aeat/_casilla.py
`backend/app/services/aeat/casillas_111.py` (python, 68 loc) — Mapeo del cálculo agregado del Modelo 111 a las casillas oficiales AEAT…
  symbols: def build_casillas_111(data)
  imports: __future__, app
  → usa: backend/app/services/aeat/_casilla.py
`backend/app/services/aeat/casillas_115.py` (python, 39 loc) — Mapeo del cálculo agregado del Modelo 115 a las casillas oficiales AEAT…
  symbols: def build_casillas_115(data)
  imports: __future__, app
  → usa: backend/app/services/aeat/_casilla.py
`backend/app/services/aeat/casillas_130.py` (python, 123 loc) — Mapeo del cálculo agregado del Modelo 130 a las casillas oficiales AEAT…
  symbols: class Casilla130 {to_dict}; def _round2(x); def build_casillas_130(data)
  imports: __future__, dataclasses, decimal
`backend/app/services/aeat/casillas_190.py` (python, 45 loc) — Mapeo del resumen del Modelo 190 a las casillas oficiales de la hoja-resumen…
  symbols: def _sum(rows, key); def build_casillas_190(data)
  imports: __future__, app, decimal
  → usa: backend/app/services/aeat/_casilla.py
`backend/app/services/aeat/casillas_200.py` (python, 51 loc) — Mapeo del cálculo agregado del Modelo 200 a las casillas oficiales AEAT…
  symbols: def build_casillas_200(data)
  imports: __future__, app
  → usa: backend/app/services/aeat/_casilla.py
`backend/app/services/aeat/casillas_303.py` (python, 250 loc) — Mapeo del cálculo agregado del 303 a las casillas oficiales AEAT…
  symbols: class Casilla303 {to_dict}; def _round2(x); def build_casillas_303(data)
  imports: __future__, dataclasses, decimal
`backend/app/services/aeat/casillas_347.py` (python, 51 loc) — Mapeo del resumen del Modelo 347 a las casillas oficiales de la hoja-resumen…
  symbols: def build_casillas_347(data)
  imports: __future__, app, decimal
  → usa: backend/app/services/aeat/_casilla.py
`backend/app/services/aeat/casillas_390.py` (python, 84 loc) — Mapeo del cálculo agregado del Modelo 390 a las casillas oficiales AEAT…
  symbols: def _sum(rows, key); def build_casillas_390(data)
  imports: __future__, app, decimal
  → usa: backend/app/services/aeat/_casilla.py
`backend/app/services/aeat/certificate_storage.py` (python, 208 loc) — Custodia de certificados digitales (.pfx/.p12) de cada tenant…
  symbols: class CertificateError; def _fernet(); class CertificateMetadata; def _extract_metadata(pfx_bytes, password); async def store_certificate(db, tenant_id, user_id, label, pfx_bytes, password, notes); async def get_active_certificate(db, tenant_id); async def load_decrypted(db, tenant_id); async def revoke_certificate(db, tenant_id, certificate_id); def cert_to_dict(cert)
  imports: __future__, app, cryptography, dataclasses, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/accounting.py
`backend/app/services/aeat/expediente_303.py` (python, 160 loc) — Expediente del Modelo 303 — bundle completo listo para presentar…
  symbols: class ExpedienteError; def _checklist_for(quarter, year, resultado); async def build_expediente_303(db, tenant_id, quarter, year)
  imports: __future__, app, base64, logging, sqlalchemy, uuid
  → usa: backend/app/services/aeat/casillas_303.py, backend/app/services/aeat/modelo_303_xml.py
`backend/app/services/aeat/modelo_303_xml.py` (python, 61 loc) — Generador de XML auxiliar del Modelo 303…
  symbols: def build_modelo_303_xml(tenant_name, tenant_nif, year, quarter, casillas)
  imports: __future__, app, xml
  → usa: backend/app/services/aeat/casillas_303.py
`backend/app/services/aeat/modelo_xml_generico.py` (python, 91 loc) — Generador XML auxiliar genérico para modelos AEAT (no-303)…
  symbols: def _to_xml(parent, name, value); def _safe_tag(name); def build_modelo_xml_generic(modelo, year, period, data, tenant_name, tenant_nif)
  imports: __future__, xml
`backend/app/services/aeat/presentation_service.py` (python, 277 loc) — Orquestador de presentación electrónica a SEDE AEAT…
  symbols: class PresentationError; async def create_presentation(db, tenant_id, user_id); async def submit_presentation(db, tenant_id, presentation_id); async def get_presentation(db, tenant_id, presentation_id); def build_acuse_text(p); async def list_presentations(db, tenant_id); def presentation_to_dict(p)
  imports: __future__, app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/accounting.py, backend/app/services/aeat/certificate_storage.py, backend/app/services/aeat/sede_client.py, backend/app/services/aeat/xades_signer.py, backend/app/services/aeat/xsd_validation.py
`backend/app/services/aeat/preventive_check.py` (python, 319 loc) — Asistente fiscal preventivo — chequeos antes de cerrar trimestre…
  symbols: class Finding {to_dict}; async def check_quarter(db, tenant_id, quarter, year); def _check_received_without_supplier_nif(invoices); def _check_invoices_without_lines(invoices); def _check_amount_mismatch(invoices); def _check_draft_in_period(invoices); def _check_imbalance_no_purchases(invoices); async def _check_verifactu_missing(db, tenant_id, invoices); async def _check_unlinked_received_documents(db, tenant_id, start, end)
  imports: __future__, app, calendar, dataclasses, datetime, decimal, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py
`backend/app/services/aeat/sede_client.py` (python, 156 loc) — Cliente HTTP para presentar modelos a la SEDE AEAT…
  symbols: class SubmissionResult; class SedeError; def _endpoint_for(model_code, environment); def _parse_response(body); async def submit_signed_xml(model_code, signed_xml, environment, dry_run)
  imports: __future__, dataclasses, datetime, logging, re, uuid
`backend/app/services/aeat/xades_signer.py` (python, 97 loc) — Firma XAdES-BES enveloped sobre el XML de modelos AEAT…
  symbols: class SignResult; class SigningError; def _is_available(); def sign_xades_bes(xml_str, pfx_bytes, password)
  imports: __future__, dataclasses, logging
`backend/app/services/aeat/xsd_validation.py` (python, 51 loc) — Validación del XML antes de firmar (pre-firma)…
  symbols: def validate_xml_pre_signature(xml_str, model_code)
  imports: __future__, logging, pathlib, xml
`backend/app/services/agent_budget.py` (python, 168 loc) — Agent budget management — control de presupuesto mensual por AIEmployee…
  symbols: async def get_budget_status(employee_id, db); async def check_agent_budget(employee_id, db); async def check_tenant_budget(tenant_id, db); async def record_token_usage(db, tenant_id, employee_id, prompt_tokens, completion_tokens, llm_provider, task_id)
  imports: app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/ai_employees.py
`backend/app/services/ai/__init__.py` (python, 74 loc) — Servicios de IA — dominio ai…
  imports: app
  → usa: backend/app/services/ai/condition_evaluator.py, backend/app/services/ai/cv_parser.py, backend/app/services/ai/employee.py, backend/app/services/ai/generative_ui.py, backend/app/services/ai/node_engine.py, backend/app/services/ai/node_graph_helpers.py
`backend/app/services/ai/condition_evaluator.py` (python, 104 loc) — Evaluador seguro de condiciones para nodos condicionales del motor de nodos…
  symbols: def _resolve_field(field, context); def _coerce_numeric(value); def evaluate_condition(condition, context)
  imports: __future__, typing
`backend/app/services/ai/cv_parser.py` (python, 102 loc) — Servicio de parsing de CVs…
  symbols: async def extract_cv_data(cv_text); async def score_candidate(candidate_data, position_data); async def parse_cv_file(file_path)
  imports: app, json, logging, typing
  → usa: backend/app/core/llm_factory.py, backend/app/prompts/__init__.py
`backend/app/services/ai/employee.py` (python, 59 loc) — Servicio de dominio para empleados IA…
  imports: app
  → usa: backend/app/services/ai/employee_contract.py, backend/app/services/ai/employee_crud.py, backend/app/services/ai/employee_provisioning.py
`backend/app/services/ai/employee_contract.py` (python, 75 loc) — Conteo del "contrato" de capacidades del AIEmployee custom (uso advisory)…
  symbols: def _scope_present(scope); def _workflows_present(workflows); def count_capabilities(); def validate_employee_contract()
  imports: __future__
`backend/app/services/ai/employee_crud.py` (python, 536 loc) — employee_crud â€” CRUD, skills catalog, activity feed and direct instruction for AIEmployee
  symbols: def to_out(e); async def _get_employee(employee_id, tenant_id, db); async def list_employees(tenant_id, db); async def create_employee(name, role_description, budget_limit_usd, tenant_id, db); async def provision_employee(employee_id, tenant_id, domain, role, system_prompt, doc_folder, skills, db); async def update_icon(employee_id, tenant_id, icon, db); async def update_appearance(employee_id, tenant_id, icon, avatar_color, db); async def update_status(employee_id, tenant_id, new_status, db); async def update_budget(employee_id, tenant_id, budget_limit_usd, db); async def delete_employee(employee_id, tenant_id, db); async def instruct_employee(employee_id, message, tenant_id, user_id, db); async def list_activity(tenant_id, db, employee_id, category, limit, offset) … (+6)
  imports: __future__, app, decimal, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/ai_employees.py, backend/app/db/models/tasks.py
`backend/app/services/ai/employee_provisioning.py` (python, 294 loc) — employee_provisioning — Seeding and LLM-driven background provisioning for AIEmployee
  symbols: async def seed_builtin(tenant_id, db); async def provision_employee_bg(employee_id, tenant_id, name, role_description)
  imports: __future__, app, json, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/ai_employees.py, backend/app/db/models/tasks.py, backend/app/services/ai/employee_crud.py
`backend/app/services/ai/generative_ui.py` (python, 317 loc) — Servicio de dominio para Generative UI…
  symbols: async def fetch_erp_context(prompt, tenant_id, db); async def generate_ui(prompt, tenant_id, db, title); async def debug_llm(tenant_id, db); async def list_uis(tenant_id, db); async def get_ui(ui_id, tenant_id, db); async def update_ui(ui_id, tenant_id, db); async def delete_ui(ui_id, tenant_id, db)
  imports: app, asyncio, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/generative_ui.py, backend/app/prompts/__init__.py
`backend/app/services/ai/node_dispatch.py` (python, 25 loc) — node_dispatch — Agent dispatcher for NodeEngine…
  symbols: async def dispatch_agent(domain, state, subtask)
  imports: __future__
`backend/app/services/ai/node_engine.py` (python, 484 loc) — NodeEngine — Motor de ejecución de grafos para workflows con nodos de control de flujo…
  symbols: class NodeEngine {__init__, run, resume, _execute_loop, _emit_node_event, _execute_node, _build_skill_dispatch, _skip_discarded_branch}
  imports: __future__, app, asyncio, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/ai/__init__.py, backend/app/services/ai/node_graph_helpers.py, backend/app/services/audit.py
`backend/app/services/ai/node_engine_nodes.py` (python, 221 loc) — NodeEngine node-type execution handlers…
  symbols: async def execute_skill_node(engine, node, db); async def run_agent_parallel(engine, node); def execute_conditional_node(engine, node); async def execute_delay_node(engine, node, db); async def execute_approval_gate(engine, node, db); def _build_skill_dispatch(engine, node, extra_meta); async def _dispatch_agent(engine, domain, state, subtask)
  imports: __future__, app, datetime, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/ai/condition_evaluator.py, backend/app/services/ai/node_graph_helpers.py, backend/app/services/audit.py, backend/app/services/workflow/task_dispatch.py
`backend/app/services/ai/node_graph_helpers.py` (python, 223 loc) — node_graph_helpers — Funciones puras de traversal de grafo para NodeEngine…
  symbols: def has_advanced_nodes(ui_nodes, ui_edges); def get_predecessors(edges, node_id); def get_successors(edges, node_id); def find_ready_nodes(nodes, edges, node_states); def all_leaf_nodes_completed(nodes, edges, node_states); def has_suspended_nodes(node_states); def build_context_for_node(edges, node_states, node_id); def skip_discarded_branch(edges, node_states, conditional_node_id, chosen_branch); def build_skill_dispatch(node, edges, node_states, tenant_id, user_id, execution_id, extra_meta)
  imports: __future__, datetime, uuid
`backend/app/services/ai/schedule_planner.py` (python, 128 loc) — Generador de horarios semanales con IA…
  symbols: async def suggest_schedules(employees, instruction)
  imports: app, json, logging, typing
  → usa: backend/app/core/llm_factory.py
`backend/app/services/ai/stream_tokens.py` (python, 86 loc) — Helper de streaming token-a-token desde LLM hacia TaskEventHub (UI.AGT v2)…
  symbols: async def stream_llm(llm, messages)
  imports: __future__, logging, typing
`backend/app/services/ai/task_cost.py` (python, 90 loc) — Agregador de coste por tarea (UI.COST)…
  symbols: async def summarize_task_cost(db)
  imports: __future__, app, decimal, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/tasks.py
`backend/app/services/alerts/__init__.py` (python, 2 loc)
  → usa: backend/app/services/alerts/service.py
`backend/app/services/alerts/_expiry.py` (python, 21 loc) — Lógica pura de clasificación de caducidad de lotes (sin base de datos)
  symbols: def expiry_status(expiry_date, today)
  imports: __future__, datetime
`backend/app/services/alerts/service.py` (python, 319 loc) — Alertas automáticas — checks periódicos sobre condiciones de negocio
  symbols: def _fmt(n); async def run_daily_alerts(); async def check_and_alert_tenant(db, tenant_id); async def _emit_overdue_events(db, tenant_id, invoice_ids); async def get_recent_alerts(db, tenant_id, hours); async def _check_overdue_invoices(db, tenant_id); async def _check_due_soon_invoices(db, tenant_id); async def _check_low_stock(db, tenant_id); async def _check_expiring_lots(db, tenant_id); async def _check_pending_payrolls(db, tenant_id); async def _is_duplicate(db, tenant_id, alert_type, entity_id); async def _persist_and_notify(db, tenant_id, alert)
  imports: app, datetime, logging, sqlalchemy
  → usa: backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/alerts.py, backend/app/db/models/auth.py, backend/app/db/models/billing.py, backend/app/db/models/hr.py, backend/app/db/models/inventory.py, backend/app/services/alerts/_expiry.py
`backend/app/services/analytics/__init__.py` (python, 22 loc) — Analytics aggregation services for dashboard endpoints + product event tracking (OPS.MET)
  imports: app
  → usa: backend/app/services/analytics/dashboard.py, backend/app/services/analytics/events.py
`backend/app/services/analytics/dashboard.py` (python, 788 loc) — Dashboard analytics aggregation…
  symbols: def iter_months_back(end_month, n); def _period_label(start); def _real_tx_filter(); def _dashboard_cache_key(db, tenant_id, period, start, end); async def latest_period_with_data(db, tenant_id); async def get_dashboard(db, tenant_id, period, start, end)
  imports: __future__, app, calendar, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/hr.py, backend/app/db/models/inventory.py, backend/app/db/models/models.py, backend/app/db/models/tasks.py, backend/app/services/cache.py
`backend/app/services/analytics/events.py` (python, 137 loc) — Tracking de eventos producto (OPS.MET)…
  symbols: async def track_event(); async def _send_to_posthog(distinct_id, event, properties, api_key)
  imports: __future__, logging, typing, uuid
`backend/app/services/audit.py` (python, 77 loc) — Servicio de auditoría…
  symbols: async def log_action(db); async def log_llm_call(db)
  imports: app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/app/services/auth/__init__.py` (python, 22 loc) — Auth domain services — public re-exports
  imports: app
  → usa: backend/app/services/auth/email_reset.py, backend/app/services/auth/service.py
`backend/app/services/auth/_schemas.py` (python, 18 loc) — Schemas owned by the auth service (canonical location)…
  symbols: class TenantCreate; class UserCreate
  imports: pydantic
`backend/app/services/auth/email_reset.py` (python, 101 loc) — Servicio de envío de email para recuperación de contraseña…
  symbols: def send_password_reset_email(to_email, reset_url, user_name)
  imports: app, email, logging, smtplib
  → usa: backend/app/core/config.py
`backend/app/services/auth/service.py` (python, 226 loc) — Lógica de negocio de autenticación: registro, login, refresh y reset de contraseña
  symbols: def _build_token_data(user); def _make_token_pair(token_data); def get_me(user); async def register(payload, db); async def login(email, password, db); def refresh(refresh_token); async def forgot_password(email, db); async def reset_password(token, new_password, db)
  imports: app, datetime, hashlib, logging, secrets, sqlalchemy
  → usa: backend/app/core/config.py, backend/app/core/datetime_utils.py, backend/app/core/security.py, backend/app/core/tenant_context.py, backend/app/db/models/models.py, backend/app/services/audit.py, backend/app/services/auth/_schemas.py, backend/app/services/auth/email_reset.py
`backend/app/services/autonomy.py` (python, 210 loc) — Servicio de política de autonomía por dominio (SEC.AUT)…
  symbols: def default_mode(domain); async def get_policy(db); async def list_policies(db); async def set_policy(db); async def reset_policy(db); async def check_autonomy(db)
  imports: __future__, app, datetime, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/tenant.py
`backend/app/services/autonomy_gate.py` (python, 295 loc) — Gate de autonomía — puente entre SEC.AUT y los agentes (AI.AGT wiring)…
  symbols: class AutonomyDecision {can_execute, needs_approval, manual_only, persist_pending_approval, to_suggestion_response, to_pending_response}; async def evaluate_autonomy(db); def serialize_action_payload(payload); def gated_tool()
  imports: __future__, app, dataclasses, datetime, json, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/tasks.py, backend/app/services/autonomy.py
`backend/app/services/backup/__init__.py` (python, 48 loc) — Paquete de backup — local (legacy_local) + remoto cifrado E2E (BAK.B2)…
  imports: app
  → usa: backend/app/services/backup/crypto.py, backend/app/services/backup/legacy_local.py, backend/app/services/backup/retention.py
`backend/app/services/backup/b2_client.py` (python, 305 loc) — Cliente HTTPS para Backblaze B2 (BAK.B2 transport)…
  symbols: class B2Error; class B2Credentials {from_settings}; class B2Session; async def authorize(creds); async def get_upload_url(session, bucket_id); def _sha1_hex(blob); async def upload_file(); async def list_file_names(session, bucket_id); async def download_file_by_name(session, bucket_name, file_name); async def delete_file_version(session, file_id, file_name); async def upload_encrypted(); async def download_and_decrypt() … (+1)
  imports: __future__, asyncio, base64, dataclasses, hashlib, httpx, logging, typing
`backend/app/services/backup/crypto.py` (python, 108 loc) — Cifrado E2E para backup remoto Backblaze B2 (BAK.B2)…
  symbols: def new_salt(); def derive_key_from_password(password, salt); def encrypt_e2e(data, password, salt); def decrypt_e2e(blob, password)
  imports: __future__, cryptography, secrets
`backend/app/services/backup/legacy_local.py` (python, 325 loc) — Backups automáticos de la base de datos del usuario…
  symbols: def _default_backup_dir(); def _portable_postgres_bin(); def _find_pg_dump(); def _parse_db_url(url); async def create_backup(backup_dir); def rotate_backups(backup_dir, retention_days); async def run_backup_job(); def _backup_dir(); def _resolve_safe(filename); def list_backups(); def get_backup_path(filename); def delete_backup(filename) … (+2)
  imports: __future__, app, asyncio, datetime, logging, os, pathlib, shutil, sys, time, typing, urllib
  → usa: backend/app/core/config.py, backend/app/core/paths.py
`backend/app/services/backup/retention.py` (python, 95 loc) — Política de retención para backups remotos (BAK.B2)…
  symbols: class BackupCandidate; def apply_rolling_retention(candidates); def _last_n_months(reference, n)
  imports: __future__, dataclasses, datetime
`backend/app/services/backup_local.py` (python, 125 loc) — Registro y estado de backups locales (BAK.LOC + BAK.VF + BAK.UI)…
  symbols: def compute_file_sha256(data); async def record_backup(db); async def get_last_backup(db); async def backup_status_for_banner(db)
  imports: __future__, app, datetime, hashlib, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/backup.py
`backend/app/services/banking/__init__.py` (python, 30 loc) — Banking service domain package
  imports: app
  → usa: backend/app/services/banking/service.py
`backend/app/services/banking/parsers/__init__.py` (python, 10 loc) — Parsers de ficheros de extracto bancario (Norma 43 AEB, etc.)
  imports: app
  → usa: backend/app/services/banking/parsers/norma43.py
`backend/app/services/banking/parsers/norma43.py` (python, 203 loc) — Parser del Cuaderno 43 de la AEB (Norma 43) — extractos bancarios españoles…
  symbols: class Norma43Error; class Norma43Movement; class Norma43Account; def _amount(digits, debe_haber); def _date(s); def _decode(content); def parse_norma43(content); def norma43_to_rows(accounts)
  imports: dataclasses, datetime
`backend/app/services/banking/psd2.py` (python, 40 loc) — Credenciales PSD2 del tenant (TenantIntegration cifrada)…
  symbols: async def get_psd2_credentials(tenant_id)
  imports: app, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/encryption.py
`backend/app/services/banking/service.py` (python, 639 loc) — Banking business logic — raises plain Python exceptions, never HTTPException
  symbols: def _real_tx_filter(); async def get_summary(db, tenant_id); async def list_transactions(db, tenant_id); class BankSyncNotAvailableError; async def sync_transactions(db, tenant_id, user_id); async def purge_demo_transactions(db, tenant_id); async def _apply_payment_entry(db, tenant_id, tx, invoice); async def reconcile_transaction(db, tenant_id, user_id, tx_id, invoice_id_str); async def ignore_transaction(db, tenant_id, tx_id); async def unreconcile_transaction(db, tenant_id, tx_id); def _normalize_client_name(name); def _as_date(value) … (+8)
  imports: app, datetime, random, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/analytics/__init__.py, backend/app/services/event_bus.py, backend/app/services/state_machine.py
`backend/app/services/billing/__init__.py` (python, 55 loc) — Billing domain services — re-exports for backwards compatibility
  imports: app
  → usa: backend/app/services/billing/commands.py, backend/app/services/billing/queries.py
`backend/app/services/billing/accounting.py` (python, 23 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/billing/commands.py, backend/app/services/billing/queries.py
`backend/app/services/billing/auto_accounting.py` (python, 194 loc) — Contabilidad automatica PGC — genera asientos contables deterministas para facturas y nominas segun el Plan General de Contabilidad español…
  symbols: def _line(key, debit, credit); async def _has_entry(db, tenant_id); async def create_invoice_journal_entry(db, tenant_id, invoice); async def create_invoice_payment_entry(db, tenant_id, invoice); async def create_payroll_journal_entry(db, tenant_id, payroll); async def create_payroll_payment_entry(db, tenant_id, payroll)
  imports: __future__, app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/billing/accounting.py
`backend/app/services/billing/backfill_verifactu.py` (python, 255 loc) — Backfill histórico de la cadena Verifactu (A.5)…
  symbols: class BackfillResult {is_empty, to_dict}; async def _is_backfill_needed(db, tenant_id); def _infer_serie(invoice_number); async def backfill_tenant_verifactu_chain(db); async def list_tenants_pending_backfill(db)
  imports: __future__, app, dataclasses, datetime, decimal, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/services/billing/verifactu_chain.py
`backend/app/services/billing/commands.py` (python, 729 loc) — Billing commands â€” write operations (CQRS-lite)…
  symbols: async def create_invoice(client_id, payload_dict, lines_data, tenant_id, user_id, db); async def create_rectificativa(original_invoice_id, reason, tenant_id, db, serie); async def update_status(invoice_id, tenant_id, new_status, db); async def delete_invoice(invoice_id, tenant_id, db); async def generate_and_save_invoice_pdf(invoice, tenant_id, user_id); async def create_journal_entry(db, tenant_id); async def delete_journal_entry(db, tenant_id, entry_id); async def create_fixed_asset(db, tenant_id, data); async def update_fixed_asset(db, tenant_id, asset_id, data); async def delete_fixed_asset(db, tenant_id, asset_id); async def create_recurring(payload, tenant_id, db); async def update_recurring(rec_id, payload, tenant_id, db) … (+2)
  imports: app, datetime, decimal, logging, os, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/billing/numbering.py, backend/app/services/billing/queries.py, backend/app/services/state_machine.py
`backend/app/services/billing/facturae.py` (python, 233 loc) — Generador de FacturaE 3.2.2 — formato XML estándar de la AEAT para B2G/B2B
  symbols: def _sub(parent, tag, text); def _fmt(n); def _amount_el(parent, tag, value); def _build_party(parent, tag, nif, corp_name, address, postal_code, city); async def generate_facturae_xml(invoice_id, tenant_id, db); async def mark_verifactu_sent(invoice_id, tenant_id, db)
  imports: app, collections, datetime, decimal, re, sqlalchemy, uuid, xml
  → usa: backend/app/db/models/auth.py, backend/app/db/models/models.py
`backend/app/services/billing/invoice.py` (python, 39 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/billing/commands.py, backend/app/services/billing/queries.py
`backend/app/services/billing/invoice_import.py` (python, 301 loc) — Integración de facturas escaneadas en el ERP…
  symbols: def _dec(v); def _parse_date(s); async def _resolve_supplier(db, tenant_id, emisor); def _norm(s); async def _match_product(db, tenant_id, description); async def _create_product_from_line(db, tenant_id, ln); async def _stock_ref_exists(db, tenant_id, reference); async def import_received_invoices(db, tenant_id, drafts, user_id); async def _link_source_document(db, tenant_id, draft, invoice_id); async def _import_one(db, tenant_id, draft, user_id)
  imports: __future__, app, datetime, decimal, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/inventory.py, backend/app/services/billing/auto_accounting.py, backend/app/services/sales/commands.py
`backend/app/services/billing/metering.py` (python, 206 loc) — Metered billing (OPS.OVR + OPS.CRON)…
  symbols: class InteractionStatus; class CronCapStatus; def _current_period(); async def _get_or_create_interaction_row(db, tenant_id, year, month); async def _get_or_create_cron_row(db, tenant_id, year, month); async def record_interaction(db); def compute_cron_cap(tier, active_companies); async def record_cron_execution(db)
  imports: app, dataclasses, datetime, decimal, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/metering.py
`backend/app/services/billing/numbering.py` (python, 79 loc) — Numeración correlativa de facturas (FAC.NUM)…
  symbols: async def next_invoice_number(db, tenant_id, series, year)
  imports: app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py
`backend/app/services/billing/queries.py` (python, 368 loc) — Billing queries — read-only operations (CQRS-lite)…
  symbols: def _d(x); def _round2(d); def compute_invoice_totals(lines_data); async def _load_invoice(invoice_id, tenant_id, db, with_joins); async def _load_tenant(tenant_id, db); async def _load_verifactu(invoice_id, db); def _build_invoice_data(invoice, company_name, company_nif, verifactu); async def list_invoices(tenant_id, db, skip, limit); async def get_invoice(invoice_id, tenant_id, db); async def build_invoice_pdf(invoice_id, tenant_id, db); async def build_rectificative_pdf(invoice_id, tenant_id, reason, db); async def build_retention_pdf(invoice_id, tenant_id, retention_pct, db) … (+3)
  imports: app, datetime, decimal, logging, os, sqlalchemy, uuid
  → usa: backend/app/core/config.py, backend/app/db/models/billing.py, backend/app/db/models/models.py
`backend/app/services/billing/recurring.py` (python, 17 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/billing/commands.py, backend/app/services/billing/queries.py
`backend/app/services/billing/registro_facturacion.py` (python, 414 loc) — VeriFactu — generación del XML `RegFactuSistemaFacturacion`…
  symbols: class SistemaInformatico; def default_sistema_informatico(); def _parse_payload(payload); def _txt(parent, ns, tag, value); def _serialize(root); def _fmt_tipo(rate); def _cabecera(root, emisor_nombre, emisor_nif); def _sistema_informatico(parent, s); def _encadenamiento(parent, huella_anterior, prev_record); class _Detalle; def _detalles(invoice, lines); def _desglose(parent, invoice, lines) … (+5)
  imports: __future__, app, dataclasses, decimal, pathlib, typing, xml
  → usa: backend/app/services/billing/verifactu_chain.py
`backend/app/services/billing/verifactu_chain.py` (python, 343 loc) — Cadena hash Verifactu (FAC.HASH) — RD 1007/2023 Art…
  symbols: def _fmt_importe(x); def _fmt_fecha_expedicion(dt); def _fmt_fecha_hora_gen(dt); def build_payload_alta(); def build_payload_anulacion(); def compute_huella(payload_canonico); def order_verifactu_chain(records); def find_tail_huella(records); async def _get_last_huella(db, tenant_id); async def append_verifactu_record(db); async def maybe_append_verifactu_record(db); async def verify_chain_integrity(db, tenant_id)
  imports: __future__, app, collections, datetime, decimal, hashlib, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/billing.py
`backend/app/services/billing/verifactu_mode.py` (python, 81 loc) — Modo de remisión Verifactu por tenant (FAC.MODE)
  symbols: async def get_mode(db); async def get_config(db); async def set_mode(db); async def should_remit(db); def to_dict(record)
  imports: __future__, app, datetime, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/billing.py
`backend/app/services/billing/verifactu_submit.py` (python, 303 loc) — Envío VeriFactu a la AEAT (modelo BYO: el certificado lo pone la pyme)…
  symbols: class VerifactuSubmitError; class VerifactuLineAck; class VerifactuAck; def _ln(tag); def _direct_text(parent, name); def parse_acuse(response_xml); class VerifactuTransport {send}; def _client_ssl_context(pfx_bytes, password); class HttpxVerifactuTransport {send}; class VerifactuSubmitter {submit}; class NoRemissionSubmitter {submit}; class PreproduccionSubmitter {__init__, submit} … (+1)
  imports: __future__, app, dataclasses, sqlalchemy, typing, uuid, xml
  → usa: backend/app/services/aeat/__init__.py, backend/app/services/billing/__init__.py
`backend/app/services/billing/xades_signer.py` (python, 147 loc) — XAdES-BES digital signature for FacturaE 3.2.2
  symbols: def _t(ns, local); def _b64(data); def _sha256b64(data); def _c14n(element); def load_certificate_info(p12_path, password); def sign_xml(xml_bytes, p12_path, password)
  imports: base64, cryptography, datetime, hashlib, lxml, pathlib
`backend/app/services/cache.py` (python, 139 loc) — Caché Redis async ligera con degradación silenciosa…
  symbols: def _get_redis(); async def cache_get(key); async def cache_set(key, value, ttl_seconds); async def cache_invalidate(key); def cached_json(key, ttl_seconds)
  imports: __future__, app, collections, functools, json, logging, typing
  → usa: backend/app/core/config.py
`backend/app/services/client_portal/__init__.py` (python, 14 loc) — Portal de clientes — servicios de dominio…
  imports: app
  → usa: backend/app/services/client_portal/tokens.py
`backend/app/services/client_portal/tokens.py` (python, 61 loc) — Emisión y hashing de tokens del portal de clientes…
  symbols: def hash_token(raw); async def issue_token(client_id, tenant_id, days_valid, db)
  imports: __future__, app, datetime, hashlib, secrets, sqlalchemy, uuid
  → usa: backend/app/db/models/auth.py
`backend/app/services/collections/__init__.py` (python, 35 loc) — Servicios de inteligencia de cobros (F3.9)…
  imports: app
  → usa: backend/app/services/collections/reminders.py, backend/app/services/collections/risk.py
`backend/app/services/collections/reminders.py` (python, 230 loc) — Calendario escalonado de recordatorios de cobro — F3.9…
  symbols: class ReminderStep {to_dict}; def _safe_date(d); def build_reminder_schedule(invoice); async def invoices_due_for_reminder(db, tenant_id)
  imports: __future__, app, dataclasses, datetime, decimal, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/billing.py
`backend/app/services/collections/risk.py` (python, 217 loc) — Scoring de riesgo de cobro por cliente — F3.9…
  symbols: class ClientRiskScore {to_dict}; def _days_between(a, b); def compute_client_risk(client, invoices); async def rank_tenant_collections(db, tenant_id)
  imports: __future__, app, dataclasses, datetime, decimal, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py
`backend/app/services/crm/__init__.py` (python, 48 loc) — CRM domain services — re-exports for backwards compatibility
  imports: app
  → usa: backend/app/services/crm/commands.py, backend/app/services/crm/queries.py
`backend/app/services/crm/commands.py` (python, 166 loc) — CRM commands â€” write operations (CQRS-lite)…
  symbols: async def create_opportunity(db, tenant_id, data); async def update_opportunity(db, tenant_id, opp_id, data); async def delete_opportunity(db, tenant_id, opp_id); async def create_activity(db, tenant_id, data); async def delete_activity(db, tenant_id, activity_id); async def create_event(db, tenant_id, data); async def update_event(db, tenant_id, event_id, data); async def delete_event(db, tenant_id, event_id); async def create_reservation(db, tenant_id, data); async def update_reservation(db, tenant_id, res_id, data); async def delete_reservation(db, tenant_id, res_id); def generate_contract(template_path, context)
  imports: app, io, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/app/services/crm/contract_generator.py` (python, 10 loc)
  imports: app
  → usa: backend/app/services/crm/commands.py, backend/app/services/crm/queries.py
`backend/app/services/crm/queries.py` (python, 129 loc) — CRM queries — read-only operations (CQRS-lite)…
  symbols: async def list_opportunities(db, tenant_id); async def list_activities(db, tenant_id, client_id, opportunity_id); async def list_events(db, tenant_id); async def list_reservations(db, tenant_id); def build_context_for_client(client, tenant); def build_context_for_employee(employee, tenant); def _fmt_date(dt); def _tenant_context(tenant)
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/app/services/crm/service.py` (python, 39 loc)
  imports: app
  → usa: backend/app/services/crm/commands.py, backend/app/services/crm/queries.py
`backend/app/services/documents/__init__.py` (python, 73 loc) — Servicios de dominio para gestión documental
  imports: app
  → usa: backend/app/services/documents/classifier.py, backend/app/services/documents/docx_html_save.py, backend/app/services/documents/docx_preview.py, backend/app/services/documents/scanner.py, backend/app/services/documents/service.py, backend/app/services/documents/smart_chunker.py
`backend/app/services/documents/_contracts.py` (python, 183 loc) — Gestión de plantillas de contrato: CRUD, preview, guardado y generación
  symbols: async def upload_contract_template(filename, contents, content_type, tenant_id, user_id, db); async def list_contract_templates(tenant_id, db); async def get_contract_template(doc_id, tenant_id, db); async def delete_contract_template(doc_id, tenant_id, db); def validate_template_on_disk(doc); def preview_contract_html(file_path); def save_contract_html(html, file_path); async def save_contract_html_and_update(html, doc, db); async def generate_contract_from_template(tpl_doc, entity_type, entity_id, tenant_id, db)
  imports: app, logging, os, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/documents/_file_ops.py
`backend/app/services/documents/_file_ops.py` (python, 126 loc) — Operaciones de archivo: validación, clasificación, guardado y extracción ZIP
  symbols: def auto_classify_category(filename, content_type); def validate_upload(filename, size); def save_file_to_disk(contents, ext); def extract_zip_entries(contents)
  imports: io, mimetypes, os, uuid, zipfile
`backend/app/services/documents/_tabular.py` (python, 164 loc) — Importación y clasificación de archivos tabulares (CSV, Excel, JSON)
  symbols: def parse_tabular_file(file_path, file_name); def auto_classify_tabular(columns); async def import_tabular_file(filename, contents, content_type, tenant_id, user_id, db)
  imports: app, json, logging, os, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/documents/_file_ops.py
`backend/app/services/documents/classifier.py` (python, 210 loc) — Clasificador de documentos por reglas — 0 tokens LLM…
  symbols: class RuleClassification; def classify_by_rules(text)
  imports: dataclasses, logging, re
`backend/app/services/documents/contracts_interview.py` (python, 87 loc) — Asistente conversacional de contratos (entrevista guiada por LLM)…
  symbols: def _system_prompt(contract_label); async def run_interview(tenant_id, db, contract_type, messages)
  imports: __future__, logging, sqlalchemy
`backend/app/services/documents/docx_html_save.py` (python, 55 loc) — Persistir HTML editado en el navegador como .docx (htmldocx + python-docx)…
  symbols: def save_html_as_docx(html, file_path)
  imports: __future__, logging, pathlib, shutil
`backend/app/services/documents/docx_preview.py` (python, 78 loc) — Vista previa de plantillas .docx → HTML (mammoth) + detección de variables docxtpl…
  symbols: def extract_variables_from_html(html); def highlight_variables_in_html(html); def docx_to_preview_html(file_path)
  imports: __future__, pathlib, re
`backend/app/services/documents/erp_import.py` (python, 247 loc) — Integración de archivos tabulares (Excel/CSV/JSON) → entidades del ERP…
  symbols: def _to_number(value); def _coerce(field, value, config); def _norm_headers(columns); def _detect_target(columns); def _map_record(row, header_norm, config); async def _load_doc(db, tenant_id, document_id); def _resolve_target(target, columns); async def preview_import(db, tenant_id, document_id, target); async def apply_import(db, tenant_id, document_id, target)
  imports: __future__, app, logging, os, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/db/models/inventory.py, backend/app/db/models/tenant.py, backend/app/services/documents/_tabular.py
`backend/app/services/documents/scanner.py` (python, 172 loc) — Business logic for the Scanner module…
  symbols: async def _find_product_by_code(db, tenant_id, code); async def scan_product(db, tenant_id, code); async def record_movement(db, tenant_id, code, quantity, notes, movement_type, device, lot_number, expiry_date, cost_price); async def confirm_delivery(db, tenant_id, albaran_number)
  imports: app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/inventory.py, backend/app/services/inventory/__init__.py
`backend/app/services/documents/service.py` (python, 556 loc) — Servicio de dominio para gestión documental…
  symbols: class EmbedderUnavailableError; async def semantic_search(query, limit, tenant_id, db); async def _dispatch_task(tenant_id, user_id, domain, intent, doc, db); async def upload_single(filename, contents, content_type, tenant_id, user_id, db, category); async def scan_single(filename, contents, content_type, tenant_id, user_id, db); async def upload_bulk(contents, tenant_id, user_id, db, category); async def export_all(tenant_id, db); async def list_documents(tenant_id, db, category); async def get_document(doc_id, tenant_id, db); async def delete_document(doc_id, tenant_id, db); def _resolve_file_path(doc); async def prepare_download(doc, tenant_id, db) … (+2)
  imports: app, datetime, io, logging, os, sqlalchemy, typing, uuid, zipfile
  → usa: backend/app/db/models/models.py, backend/app/services/documents/_contracts.py, backend/app/services/documents/_file_ops.py, backend/app/services/documents/_tabular.py
`backend/app/services/documents/smart_chunker.py` (python, 161 loc) — Chunking inteligente basado en estructura del documento…
  symbols: class Chunk; def smart_chunk(elements, max_chunk_size); def _split_large_text(text, max_size)
  imports: app, dataclasses, logging
  → usa: backend/app/services/pdf/parser.py
`backend/app/services/documents/snapshot.py` (python, 122 loc) — Servicio para generación y gestión de informes snapshot (PDF mensuales)
  symbols: async def get_tenant_name(tenant_id, db); async def save_snapshot_report(pdf_bytes, month, tenant_id, user_id, executive_summary, db); async def list_snapshot_reports(tenant_id, db); async def get_snapshot_report(report_id, tenant_id, db); def resolve_report_file_path(doc); async def delete_snapshot_report(report_id, tenant_id, db)
  imports: app, datetime, logging, os, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/documents/_file_ops.py
`backend/app/services/email/__init__.py` (python, 29 loc) — Email domain services
  imports: app
  → usa: backend/app/services/email/credentials.py, backend/app/services/email/sender.py, backend/app/services/email/service.py
`backend/app/services/email/credentials.py` (python, 121 loc) — Credenciales de email del tenant (SMTP/IMAP y OAuth gmail/outlook)…
  symbols: async def get_email_credentials(tenant_id); async def get_oauth_token(tenant_id, integration_type)
  imports: app, httpx, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/email/service.py, backend/app/services/encryption.py
`backend/app/services/email/sender.py` (python, 151 loc) — Email-sender service — public API para que cualquier capa (agentes, routes, otros services) envíe emails sin importar directamente del agent…
  symbols: async def load_attachments(tenant_id, attachment_ids); async def resolve_smtp_attachments(tenant_id, attachment_ids); async def send_email(tenant_id, to, subject, body, attachment_ids); def send_failed(result)
  imports: __future__, app, logging, os, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/email/credentials.py, backend/app/services/email/service.py
`backend/app/services/email/service.py` (python, 348 loc) — Servicio de correo electrónico real usando IMAP (lectura) y SMTP (envío)…
  symbols: class EmailMessage; class EmailCredentials; def _decode_header_value(value); def _extract_body(msg); def read_inbox(credentials, max_results, folder); def read_unread(credentials, max_results); def send_email_smtp(credentials, to, subject, body, reply_to, attachment_paths); def test_imap_connection(credentials); def credentials_from_dict(data)
  imports: dataclasses, email, imaplib, logging, smtplib, ssl
`backend/app/services/email_ai/__init__.py` (python, 6 loc) — Servicios IA para email: clasificación de bandeja + redacción de borradores
  imports: app
  → usa: backend/app/services/email_ai/classifier.py
`backend/app/services/email_ai/classifier.py` (python, 233 loc) — Clasificación de bandeja Gmail/Outlook y redacción de borradores con Anthropic…
  symbols: class EmailClassification {to_dict}; class EmailDraft {to_dict}; class EmailAIError; def _parse_json_loose(text); def _get_client(); def _model(); async def classify_messages(messages); async def draft_reply(message, context, user_full_name)
  imports: __future__, app, dataclasses, json, logging, re
  → usa: backend/app/core/config.py
`backend/app/services/email_marketing/__init__.py` (python, 5 loc)
  → usa: backend/app/services/email_marketing/sender.py
`backend/app/services/email_marketing/campaigns.py` (python, 122 loc) — CRUD de campañas de email marketing + precarga de destinatarios…
  symbols: class CampaignInSendingError; async def list_campaigns(tenant_id, db); async def _get_campaign(campaign_id, tenant_id, db); async def create_campaign(payload, tenant_id, db); async def update_campaign(campaign_id, payload, tenant_id, db); async def delete_campaign(campaign_id, tenant_id, db); async def get_sendable_campaign(campaign_id, tenant_id, db)
  imports: app, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/email_marketing.py, backend/app/services/email_marketing/recipients.py
`backend/app/services/email_marketing/recipients.py` (python, 35 loc) — Destinatarios de email marketing: clientes del tenant con consentimiento…
  symbols: def recipients_filter(tenant_id); async def count_recipients(tenant_id, db); async def list_recipients(tenant_id, db)
  imports: app, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/crm.py
`backend/app/services/email_marketing/sender.py` (python, 98 loc) — Envío de campañas de email marketing…
  symbols: def _render(template, recipient); async def send_campaign(campaign_id, tenant_id)
  imports: app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/email_marketing.py, backend/app/services/audit.py, backend/app/services/email/sender.py
`backend/app/services/email_marketing/templates.py` (python, 65 loc) — CRUD de plantillas de email marketing…
  symbols: async def list_templates(tenant_id, db); async def _get_template(template_id, tenant_id, db); async def create_template(payload, tenant_id, db); async def update_template(template_id, payload, tenant_id, db); async def delete_template(template_id, tenant_id, db)
  imports: app, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/email_marketing.py
`backend/app/services/encryption.py` (python, 87 loc) — Servicio de cifrado/descifrado de credenciales de integraciones por tenant…
  symbols: def _get_fernet(); def get_fernet(); def encrypt_credentials(credentials); def decrypt_credentials(encrypted); def encrypt_str(plaintext); def decrypt_str(token)
  imports: app, base64, cryptography, logging
  → usa: backend/app/core/config.py
`backend/app/services/event_bus.py` (python, 212 loc) — Event Bus — Sistema de eventos internos para disparar automatizaciones…
  symbols: async def emit_event(db, tenant_id, user_id, event_name, context); def _build_instruction(workflow); def _infer_domain(workflow, instruction)
  imports: __future__, app, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/models.py
`backend/app/services/events_catalog.py` (python, 39 loc) — Catálogo de eventos de negocio del event bus…
  imports: __future__
`backend/app/services/exec_log_store.py` (python, 45 loc) — Almacén en memoria para logs de ejecución de tareas
  symbols: def push(task_id, line); def get_all(task_id); def clear(task_id); def _evict_expired()
  imports: threading, time
`backend/app/services/execution_context.py` (python, 404 loc) — ExecutionContext: contexto compartido entre pasos de una ejecución multiagente…
  symbols: def _truncate_response_text(text); def _parse_markdown_entities(text); class ExecutionContext {from_state, _ingest_result, _extract_entities, build_enriched_intent, get_entity, has_step_from, last_result_from, to_dict}
  imports: __future__, dataclasses, logging, re, typing
`backend/app/services/health.py` (python, 90 loc) — Health checks adicionales: Redis, APScheduler, último backup…
  symbols: async def check_redis(timeout_seconds); def check_scheduler(); def check_last_backup()
  imports: __future__, app, asyncio, datetime, pathlib, time, typing
  → usa: backend/app/core/config.py
`backend/app/services/hr/__init__.py` (python, 6 loc) — HR domain services — re-exports for backwards compatibility
  imports: app
`backend/app/services/hr/_employee_docs.py` (python, 121 loc)
  symbols: def list_employee_documents(…); def upload_employee_document(…); def get_employee_document(…); def delete_employee_document(…); def read_document_file(…)
`backend/app/services/hr/_payroll.py` (python, 352 loc)
  symbols: def list_payrolls(…); def create_payroll(…); def create_payroll_auto(…); def preview_payroll(…); def approve_payroll(…); def update_payroll(…); def delete_payroll(…); def build_payroll_pdf(…); def generate_and_save_payroll_pdf(…); def download_payroll_pdf(…)
`backend/app/services/hr/_special_docs.py` (python, 130 loc) — Special HR document generators — finiquito, liquidacion, registro de jornada
  symbols: async def load_employee_and_tenant(employee_id, tenant_id, db); def generate_finiquito_pdf(emp, tenant, payload); def generate_liquidacion_pdf(emp, tenant, payload); def generate_registro_jornada(emp, tenant, payload)
  imports: app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/pdf/__init__.py
`backend/app/services/hr/commands.py` (python, 783 loc) — HR commands - write operations (CQRS-lite)…
  symbols: async def create_employee(data, tenant_id, db); async def update_employee(employee_id, payload, tenant_id, db); async def delete_employee(employee_id, tenant_id, db); async def generate_document(doc_type, instructions, employee_name, employee_id, tenant_id, db); async def _next_doc_number(db, tenant_id, year); async def approve_document(doc_id, tenant_id, db); def _render_hr_document_pdf(doc); async def get_document_pdf(doc_id, tenant_id, db); async def delete_document(doc_id, tenant_id, db); async def create_position(db, tenant_id, payload); async def upload_cv(db, tenant_id, position_id, file_name, file_obj); async def update_candidate_status(db, tenant_id, candidate_id, new_status) … (+17)
  imports: app, datetime, logging, os, shutil, sqlalchemy, uuid
  → usa: backend/app/db/models/hr.py, backend/app/db/models/hr_documents.py, backend/app/db/models/models.py, backend/app/services/event_bus.py, backend/app/services/hr/queries.py, backend/app/services/hr/_employee_docs.py, backend/app/services/hr/_payroll.py, backend/app/services/hr/_special_docs.py
`backend/app/services/hr/documents.py` (python, 31 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/hr/commands.py, backend/app/services/hr/queries.py
`backend/app/services/hr/finiquito.py` (python, 201 loc) — Cálculo de finiquito — liquidación al término de la relación laboral…
  symbols: def _parse_date(value); def _normalize_causa(causa); def calc_finiquito(); def calc_finiquito_for_employee(emp, fecha_baja, causa, vacaciones_pendientes_dias); async def create_settlement(db, tenant_id, employee_id, calc)
  imports: app, datetime, sqlalchemy
  → usa: backend/app/db/models/hr.py, backend/app/db/models/models.py, backend/app/services/hr/queries.py
`backend/app/services/hr/queries.py` (python, 842 loc) — HR queries — read-only operations (CQRS-lite)…
  symbols: def mei_trabajador(year); def base_maxima_cotizacion(year); def cuota_solidaridad_trabajador(base_salary, year); def it_days_overlap(leave_start, leave_end, period_start, period_end); def _prestacion_it(base_reguladora_diaria, dias_it, dia_inicio); def calc_payroll(base_salary, irpf_rate, year); def calc_payroll_for_employee(emp, base_salary, irpf_rate, year, period_start, period_end, horas_extra_importe); async def list_employees(tenant_id, db); async def get_employee(employee_id, tenant_id, db); def _load_sepe_logo_b64(); def _get_system_prompt(doc_type); async def _build_employee_context(employee_id, tenant_id, db) … (+17)
  imports: app, base64, logging, os, sqlalchemy, uuid
  → usa: backend/app/db/models/hr.py, backend/app/db/models/hr_documents.py, backend/app/db/models/models.py, backend/app/prompts/__init__.py, backend/app/services/hr/_employee_docs.py, backend/app/services/hr/_payroll.py, backend/app/services/hr/_special_docs.py
`backend/app/services/hr/recruitment.py` (python, 23 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/hr/commands.py, backend/app/services/hr/queries.py
`backend/app/services/hr/schedule_export.py` (python, 124 loc) — Export de horarios de trabajo a Excel (openpyxl) y PDF (reportlab)
  symbols: async def fetch_schedule_grid(db, tenant_id, employee_id); def build_schedules_xlsx(grid); def build_schedules_pdf(grid, company_name)
  imports: app, datetime, io, sqlalchemy
  → usa: backend/app/db/models/hr.py, backend/app/db/models/models.py
`backend/app/services/hr/service.py` (python, 113 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/hr/commands.py, backend/app/services/hr/queries.py
`backend/app/services/i18n/__init__.py` (python, 6 loc) — Helpers de i18n para resolver locale por tenant
  → usa: backend/app/services/i18n/tenant_locale.py
`backend/app/services/i18n/tenant_locale.py` (python, 78 loc) — Resolución de locale por tenant para PDFs y emails (I18N.PDF)…
  symbols: async def get_tenant_locale(db); def resolve_locale()
  imports: __future__, app, sqlalchemy, typing, uuid
  → usa: backend/app/i18n/pdf_strings.py
`backend/app/services/idempotency.py` (python, 149 loc) — Guard de idempotencia persistente en DB (tabla `idempotency_keys`)…
  symbols: def _make_key(operation, entity_id); def _evict_expired(); class IdempotencyGuard {__init__, already_executed, mark_executed, release, get_execution_info}; async def purge_expired_keys()
  imports: app, datetime, json, logging, sqlalchemy, threading, time
  → usa: backend/app/db/models/__init__.py
`backend/app/services/integration/__init__.py` (python, 71 loc) — Integration domain services — re-exports for backwards compatibility
  imports: app
  → usa: backend/app/services/integration/heartbeat.py, backend/app/services/integration/messaging.py, backend/app/services/integration/service.py
`backend/app/services/integration/heartbeat.py` (python, 304 loc) — Heartbeat Service — Ciclo vital de los AIEmployee…
  symbols: async def _ws_notify_budget(tenant_id, employee_id, event_type, budget); def get_scheduler(); def register_employee_heartbeat(employee_id, tenant_id); def unregister_employee_heartbeat(employee_id); async def run_employee_heartbeat(employee_id, tenant_id); async def bootstrap_employee_heartbeats()
  imports: app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/ai_employees.py, backend/app/db/models/tasks.py, backend/app/services/agent_budget.py
`backend/app/services/integration/messaging.py` (python, 320 loc) — Business logic for Telegram messaging integration…
  symbols: async def send_reply(chat_id, text, reply_to_message_id); async def find_integration_by_chat(db, chat_id); def verify_webhook_secret(secret_header); async def handle_link_command(db, chat_id, username, first_name, link_token); async def send_typing_indicator(chat_id); async def process_and_reply(tenant_id, chat_id, text, reply_to); async def connect_telegram(db, tenant_id); async def disconnect_telegram(db, tenant_id); async def get_telegram_status(db, tenant_id); async def setup_webhook()
  imports: app, asyncio, logging, secrets, sqlalchemy, uuid
  → usa: backend/app/core/config.py, backend/app/db/models/models.py, backend/app/integrations/telegram_client.py, backend/app/services/encryption.py
`backend/app/services/integration/service.py` (python, 404 loc) — Servicio de dominio para integraciones de terceros…
  symbols: def set_oauth_state(state, tenant_id, code_verifier); def pop_oauth_state(state); async def get_integration(tenant_id, integration_type, db); async def list_integrations(tenant_id, db); async def upsert_integration(tenant_id, integration_type, encrypted_creds, db); async def disconnect_integration(tenant_id, integration_type, db); async def get_status(tenant_id, integration_type, db); async def connect_psd2(secret_id, secret_key, tenant_id, db); async def connect_email(email_address, password, provider, imap_host, imap_port, smtp_host, smtp_port, tenant_id, db); async def email_status(tenant_id, db); async def handle_oauth_callback(code, state, provider, db); async def get_oauth_access_token(db, tenant_id, integration_type) … (+2)
  imports: app, logging, sqlalchemy, time
  → usa: backend/app/db/models/models.py, backend/app/services/encryption.py
`backend/app/services/inventory/__init__.py` (python, 2 loc) — Servicios de inventario: lotes y deducción FEFO
`backend/app/services/inventory/_fefo.py` (python, 72 loc) — Lógica pura de asignación FEFO (First Expired, First Out)…
  symbols: class LotLike; class LotAllocation; def _fefo_sort_key(lot); def plan_fefo_deduction(lots, quantity)
  imports: __future__, dataclasses, datetime, typing
`backend/app/services/inventory/analytics.py` (python, 248 loc) — Analítica de inventario: valoración, stock muerto y productos más movidos…
  symbols: async def _valuation(db, tenant_id); async def _top_movers(db, tenant_id, days, limit); async def _dead_stock(db, tenant_id, days); async def _bajas(db, tenant_id, days); async def _box_bajas_units(db, tenant_id, days); async def _below_min(db, tenant_id); async def inventory_overview(db, tenant_id, dead_days, top_days, merma_days)
  imports: __future__, app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py
`backend/app/services/inventory/batch_service.py` (python, 316 loc) — Operaciones de inventario por lotes (batch)…
  symbols: async def resolve_product(db, tenant_id, ref); def _to_int(value); async def batch_adjust_stock(db, tenant_id, items, op, reason, user_id, dry_run); def _coerce_field(field, value); async def batch_update_fields(db, tenant_id, items, dry_run)
  imports: __future__, app, decimal, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py
`backend/app/services/inventory/labels.py` (python, 103 loc) — Generación de etiquetas de producto con código de barras (PDF para imprimir)…
  symbols: def _draw_label(c, label, x, y_top, w, h, show_price); def build_labels_pdf(labels, show_price); async def generate_labels_pdf(db, tenant_id, items, show_price)
  imports: __future__, app, io, reportlab, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py
`backend/app/services/inventory/lot_service.py` (python, 340 loc) — Gestión de lotes de producto y deducción FEFO sobre la base de datos…
  symbols: async def _load_lots(db, product_id); def _lot_dict(lot); async def has_lots(db, product_id); async def add_lot(db); async def deduct_fefo(db); async def lot_summary(db, product_id); async def _get_product_owned(db, tenant_id, product_id); async def list_lots(db, tenant_id, product_id); async def update_lot_metadata(db, tenant_id, lot_id, fields); async def list_expiring_lots(db, tenant_id, days); async def create_lot(db)
  imports: __future__, app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py, backend/app/services/alerts/_expiry.py, backend/app/services/inventory/_fefo.py
`backend/app/services/inventory/reorder_service.py` (python, 173 loc) — Reposición automática: sugerencias de pedido y generación de pedidos de compra borrador cuando el stock baja del punto de pedido (`stock_min…
  symbols: def _suggest_qty(product); async def suggest_reorders(db, tenant_id); async def _products_in_open_pos(db, tenant_id); async def generate_draft_pos(db, tenant_id); async def run_auto_reorder()
  imports: __future__, app, collections, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/crm.py, backend/app/db/models/inventory.py, backend/app/db/models/orders.py
`backend/app/services/inventory/stock_service.py` (python, 211 loc) — Stock por almacén (multi-almacén, capa 2)…
  symbols: async def _default_warehouse_id(db, tenant_id); async def _global_stock(db, tenant_id, product_id); async def _row(db, product_id, warehouse_id); async def _nondefault_total(db, tenant_id, product_id, default_id); async def _set_nondefault(db); async def get_by_warehouse(db, tenant_id, product_id); async def _available_in(db, tenant_id, product_id, warehouse_id, default_id); async def add_to_warehouse(db); async def transfer(db)
  imports: __future__, app, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py, backend/app/services/inventory/_fefo.py
`backend/app/services/inventory/warehouse_service.py` (python, 95 loc) — Gestión de almacenes/tiendas (multi-almacén, capa 1)…
  symbols: def _wh_dict(w); async def list_warehouses(db, tenant_id); async def get_default_id(db, tenant_id); async def _unset_defaults(db, tenant_id); async def create_warehouse(db, tenant_id, data); async def update_warehouse(db, tenant_id, warehouse_id, fields)
  imports: __future__, app, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py
`backend/app/services/llm_cache.py` (python, 164 loc)
  symbols: def _make_key(tenant_id, intent, provider); def _evict_expired(); def _evict_oldest(); class LLMCache {__init__, get, set, invalidate, flush_prefix, flush_tenant}
  imports: __future__, hashlib, json, logging, threading, time
`backend/app/services/llm_usage_tracker.py` (python, 250 loc) — Tracker en memoria de uso LLM por tenant/agente/mes…
  symbols: def record(tenant_id, agent, provider, tokens_in, tokens_out); def estimate_cost(provider, tokens_in, tokens_out); def get_monthly_stats(tenant_id, months); def flush_tenant(tenant_id); def _snapshot(); async def persist_to_db(); async def load_from_db(months)
  imports: collections, datetime, logging, threading
`backend/app/services/marketing/__init__.py` (python, 1 loc)
`backend/app/services/marketing/image_generation.py` (python, 88 loc) — Generación de imágenes con IA vía OpenAI Images API…
  symbols: async def generate_image(prompt); async def _generate_openai(prompt)
  imports: __future__, app, httpx, logging
  → usa: backend/app/core/config.py
`backend/app/services/marketing/image_search.py` (python, 52 loc) — Búsqueda de imágenes de stock vía Unsplash API
  symbols: async def search_image(query)
  imports: __future__, app, httpx, logging
  → usa: backend/app/core/config.py
`backend/app/services/marketing/metrics.py` (python, 83 loc) — Analítica de posts de marketing — lectura/agregación de métricas locales…
  symbols: async def _upsert_metrics(db, post, metrics, day); async def get_campaign_metrics(db, tenant_id, campaign_id)
  imports: __future__, app, datetime, sqlalchemy
  → usa: backend/app/db/models/marketing.py
`backend/app/services/marketing/provider_config.py` (python, 90 loc) — Cuentas del proveedor de marketing social por tenant (BYO Zernio, multi-cuenta)…
  symbols: async def list_provider_configs(db, tenant_id); async def get_config(db, config_id, tenant_id); def decrypted_api_key(cfg); def client_for_config(cfg); async def add_provider_config(db, tenant_id, api_key, label, default_profile_id); async def set_default_profile_id(db, cfg, profile_id); async def delete_provider_config(db, config_id, tenant_id); async def client_for_account(db, account)
  imports: __future__, app, sqlalchemy
  → usa: backend/app/db/models/marketing.py, backend/app/services/encryption.py, backend/app/services/marketing/zernio_client.py
`backend/app/services/marketing/publisher_base.py` (python, 26 loc) — Interfaz común de publicación de marketing, independiente del proveedor…
  symbols: class MarketingPublisher {publish_post}
  imports: __future__, app, collections, sqlalchemy, typing
  → usa: backend/app/db/models/marketing.py
`backend/app/services/marketing/publishing.py` (python, 87 loc) — Selección del proveedor de publicación de marketing (seam intercambiable)…
  symbols: def get_publisher(); class PostAlreadyPublishedError; async def publish_single_post(post_id, tenant_id, db); async def publish_posts_batch(post_ids, tenant_id, db)
  imports: __future__, app, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/marketing.py, backend/app/services/marketing/publisher_base.py, backend/app/services/marketing/zernio_publisher.py
`backend/app/services/marketing/social_accounts.py` (python, 49 loc) — Cuentas sociales de marketing (Zernio): orquestación de desconexión…
  symbols: async def disconnect_account(account_id, tenant_id, db)
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/models/marketing.py, backend/app/services/marketing/provider_config.py, backend/app/services/marketing/zernio_client.py
`backend/app/services/marketing/zernio_client.py` (python, 154 loc) — Cliente REST fino para la API de Zernio (social / mensajería / ads)…
  symbols: class ZernioError {__init__}; class ZernioPost; class ZernioClient {__init__, _headers, _request, list_profiles, list_accounts, connect_url, disconnect_account, create_post}
  imports: __future__, app, dataclasses, httpx, logging
  → usa: backend/app/core/config.py
`backend/app/services/marketing/zernio_publisher.py` (python, 72 loc) — Publicación de posts vía Zernio (implementa `MarketingPublisher`)…
  symbols: class ZernioPublisher {publish_post, _do_publish}
  imports: __future__, app, datetime, logging, sqlalchemy
  → usa: backend/app/db/models/marketing.py, backend/app/services/marketing/provider_config.py, backend/app/services/marketing/publisher_base.py, backend/app/services/marketing/zernio_client.py
`backend/app/services/metrics/__init__.py` (python, 2 loc) — Métricas de valor para el centro de mando (tiempo ahorrado, actividad IA)
`backend/app/services/metrics/time_saved.py` (python, 98 loc) — Tiempo ahorrado por la IA — estimación a partir del AuditLog…
  symbols: async def time_saved_summary(db, tenant_id)
  imports: __future__, app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/tasks.py
`backend/app/services/migration/__init__.py` (python, 42 loc) — Importadores (MIG.* sprint 7)
  imports: app
  → usa: backend/app/services/migration/bulk_import.py, backend/app/services/migration/csv_importer.py, backend/app/services/migration/holded_importer.py, backend/app/services/migration/wizard.py
`backend/app/services/migration/bulk_import.py` (python, 464 loc) — Bulk CSV import for employees / clients / products…
  symbols: class BulkImportResult; def _coerce(value, typ); async def import_employees_rows(rows, tenant_id, db); async def import_clients_rows(rows, tenant_id, db); async def import_products_rows(rows, tenant_id, db); def _parse_dt(s); async def _resolve_employee(db, tenant_id, row); async def import_payrolls_rows(rows, tenant_id, db); async def _resolve_client(db, tenant_id, nif, name); async def import_invoices_rows(rows, tenant_id, db); async def import_bank_transactions_rows(rows, tenant_id, db)
  imports: __future__, app, calendar, dataclasses, datetime, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/db/models/inventory.py
`backend/app/services/migration/csv_importer.py` (python, 186 loc) — Importador CSV genérico (MIG.1)…
  symbols: class ImportRow; class ImportPreview; def _normalize_header(h); def _detect_separator(sample); def _decode_with_fallback(blob); def _build_header_mapping(csv_headers, kind); def _parse_decimal(value); def parse_csv(blob, kind)
  imports: __future__, csv, dataclasses, decimal, io, typing
`backend/app/services/migration/holded_client.py` (python, 230 loc) — Cliente HTTP paginado para Holded API (MIG.2)…
  symbols: class HoldedError; class HoldedAuthError; class HoldedRateLimitError; def _headers(creds); async def _get_page(); async def _iter_paginated(); async def iter_contacts(creds); async def iter_invoices(creds); async def fetch_all_contacts(creds); async def fetch_all_invoices(creds)
  imports: __future__, app, asyncio, collections, httpx, logging, typing
  → usa: backend/app/services/migration/holded_importer.py
`backend/app/services/migration/holded_importer.py` (python, 88 loc) — Importador Holded API (MIG.2)…
  symbols: class HoldedCredentials; def normalize_holded_contact(contact); def normalize_holded_invoice(doc)
  imports: __future__, app, dataclasses, datetime, decimal, typing
  → usa: backend/app/services/migration/csv_importer.py
`backend/app/services/migration/wizard.py` (python, 135 loc) — Wizard de importación (MIG.3) — orquesta preview → confirm → persist con rollback…
  symbols: class ImportResult; def _validate_preview_for_commit(preview, total_in_set); async def import_clients(db, tenant_id, rows)
  imports: __future__, app, dataclasses, sqlalchemy, uuid
  → usa: backend/app/db/models/crm.py, backend/app/services/migration/csv_importer.py
`backend/app/services/notifications.py` (python, 129 loc) — Servicio de notificaciones persistentes (UI.NOT)
  symbols: async def create_notification(db); async def list_notifications(db); async def count_unread(db); async def mark_read(db); async def mark_all_read(db); def to_dict(record)
  imports: __future__, app, datetime, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/notifications.py
`backend/app/services/observability/__init__.py` (python, 9 loc) — Observabilidad: trazas, métricas, logs estructurados
  imports: app
  → usa: backend/app/services/observability/agent_trace.py
`backend/app/services/observability/agent_trace.py` (python, 155 loc) — Helper para registrar trazas de ejecución de agentes (SEC.WORM + AI Act)…
  symbols: def _sha256_hex(text); async def record_agent_execution(db); async def record_task_cost_trace(db)
  imports: app, decimal, hashlib, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/tasks.py
`backend/app/services/ocr/__init__.py` (python, 10 loc) — OCR services — extracción estructurada de datos desde imágenes (tickets, facturas)
  imports: app
  → usa: backend/app/services/ocr/invoice_scanner.py, backend/app/services/ocr/receipt_scanner.py
`backend/app/services/ocr/invoice_scanner.py` (python, 470 loc) — Extracción estructurada de facturas RECIBIDAS desde imagen o PDF…
  symbols: class InvoiceLineExtracted {to_dict}; class InvoiceExtracted {to_dict}; class InvoiceExtractionError; def _parse_json_loose(text); def _parse_date(s); def _build_invoice(payload); async def _resolve_vision_credentials(tenant_id, db); async def _extract_anthropic(api_key, model, mime_type, image_b64, user_text); async def _extract_openai(api_key, model, mime_type, image_b64, user_text); def _extract_text_from_pdf(image_bytes); def _regex_candidates(text); async def _extract_via_text(text, candidates, tenant_id, db, few_shot_hint) … (+1)
  imports: __future__, app, base64, dataclasses, datetime, json, logging, re
  → usa: backend/app/core/config.py
`backend/app/services/ocr/receipt_scanner.py` (python, 195 loc) — Extracción de datos estructurados desde imágenes de tickets/recibos…
  symbols: class ReceiptData {to_dict}; class ReceiptExtractionError; def _parse_json_loose(text); def _build_receipt(payload); async def extract_receipt_data(image_bytes, mime_type)
  imports: __future__, app, base64, dataclasses, datetime, json, logging, re
  → usa: backend/app/core/config.py
`backend/app/services/ocr/supplier_learning.py` (python, 320 loc) — Aprendizaje por proveedor para reducir consumo LLM en escaneos OCR (F2.5)…
  symbols: def file_sha256(image_bytes); async def lookup_cached(db, tenant_id, file_hash); async def save_to_cache(db, tenant_id, file_hash, file_size, mime_type, extracted_data); async def get_template(db, tenant_id, supplier_nif); def apply_template_overrides(extraction, template); def build_few_shot_block(template); async def record_extraction(db, tenant_id, extraction); def diff_corrections(original, corrected); async def save_correction(db, tenant_id, supplier_nif, original, corrected)
  imports: __future__, app, datetime, decimal, hashlib, json, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/supplier_learning.py
`backend/app/services/onboarding/__init__.py` (python, 2 loc) — Servicios de onboarding del cliente (PRES.REG y siguientes)
`backend/app/services/onboarding/regap.py` (python, 200 loc) — Servicio del wizard REGAP (PRES.REG) — apoderamiento AEAT…
  symbols: def _settings_apoderado(); async def get_regap_status(db); async def start_identification(db); async def mark_power_granted(db); async def _call_regap_consulta(nif_cliente, nif_apoderado); async def verify_regap_consulta(db); async def reset_regap(db)
  imports: __future__, app, datetime, json, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/auth.py
`backend/app/services/onboarding/seed.py` (python, 244 loc) — Seed de datos de ejemplo del onboarding (UI.ONB)…
  symbols: async def _demo_counts(db, tenant_id); async def _build_demo_invoice(db); async def seed_demo_data(db); async def clear_demo_data(db); async def demo_status(db)
  imports: __future__, app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/core/tenant_context.py, backend/app/db/models/crm.py, backend/app/db/models/inventory.py, backend/app/db/models/models.py, backend/app/services/billing/queries.py, backend/app/services/onboarding/wizard.py
`backend/app/services/onboarding/simulate_303.py` (python, 125 loc) — Simulador del Modelo 303 con datos ejemplo (UI.SIM)…
  symbols: class SampleLine; def _round2(value); def simulate_modelo_303(quarter, year)
  imports: __future__, dataclasses, decimal, typing
`backend/app/services/onboarding/wizard.py` (python, 132 loc) — Servicio del wizard onboarding focado (UI.ONB)
  symbols: async def get_state(db); def _maybe_complete(record); async def sync_llm_config_step(db); async def set_step(db); async def skip_to_end(db); async def reset(db); def to_dict(record)
  imports: __future__, app, datetime, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/tenant.py
`backend/app/services/orchestration/__init__.py` (python, 44 loc) — Servicios de orquestación (capa Coordinador)…
  imports: app
  → usa: backend/app/services/orchestration/context.py, backend/app/services/orchestration/executor.py, backend/app/services/orchestration/summaries.py
`backend/app/services/orchestration/context.py` (python, 272 loc) — Persistencia compartida de la orquestación: documentos generados por IA, bloqueo de documentos y creación centralizada de PendingApproval
  symbols: async def lock_document(db, doc_id, task_id); async def unlock_document(db, doc_id, task_id); def response_indicates_approval(text); async def ensure_pending_approval(tenant_id, task_id, agent_results, execution_id); def messages_already_generated_pdf(messages); async def save_ai_result_as_document(tenant_id, task_id, category, title, content, reference_name); async def save_ai_result_as_csv(tenant_id, task_id, category, filename, data)
  imports: logging, uuid
`backend/app/services/orchestration/executor.py` (python, 99 loc) — Instrumentación de la ejecución de agentes: resultados de error, auditoría, broadcast de progreso por WebSocket y liberación de employees…
  symbols: def make_error_result(subtask, agent_name, action, error, summary); async def release_employee(db, employee); async def audit_log_result(state, result, subtask, agent_name, action_str); async def broadcast_progress(state, result, agent_name, step_num, total_steps)
  imports: app, asyncio, logging, uuid
  → usa: backend/app/db/base.py, backend/app/services/audit.py
`backend/app/services/orchestration/summaries.py` (python, 214 loc) — Formateo de resúmenes de agentes y extracción de fechas en español
  symbols: def _summary_from_response(output, prefix); def format_summary(agent, output, success, error); def extract_month_year(intent)
  imports: datetime, re
`backend/app/services/pdf/__init__.py` (python, 69 loc) — PDF generation subpackage…
  symbols: def __getattr__(name)
  imports: app
  → usa: backend/app/services/pdf/albaranes.py, backend/app/services/pdf/hr.py, backend/app/services/pdf/invoices.py, backend/app/services/pdf/parser.py, backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/_finiquito.py` (python, 185 loc) — Generacion de PDF de finiquito con formato oficial espanol
  symbols: def generate_finiquito_pdf(finiquito_data)
  imports: app, io
  → usa: backend/app/services/pdf/_hr_common.py, backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/_hr_common.py` (python, 60 loc) — Helpers compartidos por los generadores de PDF de RRHH
  symbols: def _make_hr_doc(buffer); def _parse_date(date_str); def _info_row(label, value, sty_lbl, sty_val); def _eur(v); def _generate_simple_text(doc_type, data)
  imports: app, datetime
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/_invoice_sections.py` (python, 405 loc) — Helpers internos de construcción de secciones PDF para facturas…
  symbols: def _invoice_lines_table(lines, header_sty, body_sty, right_sty, theme, locale); def _simple_header(company, data, s, accent, doc_title); def _generate_simple_text_pdf(invoice_data); def _themed_header(invoice_data, company, th, styles, title_sty, body_sty, right_sty, bold, font, acc); def _verifactu_qr_block(verifactu)
  imports: app
  → usa: backend/app/i18n/__init__.py, backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/_liquidacion.py` (python, 204 loc) — Generacion de PDF de liquidacion y finiquito con formato oficial espanol
  symbols: def generate_liquidacion_finiquito_pdf(liquidacion_data)
  imports: app, io
  → usa: backend/app/services/pdf/_hr_common.py, backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/_payroll.py` (python, 415 loc) — Generacion de PDF de nomina (recibo de salario) con formato oficial espanol
  symbols: def _period_label(start_str, end_str); def generate_payroll_pdf(payroll_data, theme_config); def _generate_simple_payroll_text(payroll_data)
  imports: app, io
  → usa: backend/app/services/pdf/_hr_common.py, backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/_registro_jornada.py` (python, 163 loc) — Generacion de PDF de registro mensual de jornada
  symbols: def generate_registro_jornada_pdf(registro_data)
  imports: app, calendar, datetime, io
  → usa: backend/app/services/pdf/_hr_common.py, backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/albaranes.py` (python, 271 loc) — PDF generation for albaranes (delivery notes)…
  symbols: def generate_albaran_pdf(albaran_data, theme_config)
  imports: app, io
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/hr.py` (python, 16 loc) — Generacion de PDFs de RRHH con formato oficial espanol…
  imports: app
  → usa: backend/app/services/pdf/_finiquito.py, backend/app/services/pdf/_liquidacion.py, backend/app/services/pdf/_payroll.py, backend/app/services/pdf/_registro_jornada.py
`backend/app/services/pdf/invoices.py` (python, 477 loc) — Generación de PDFs de facturación: factura estándar, rectificativa y con retención
  symbols: def generate_invoice_pdf(invoice_data, theme_config); def generate_rectificative_invoice_pdf(data, theme_config); def generate_retention_invoice_pdf(data, theme_config)
  imports: app, io
  → usa: backend/app/services/pdf/_invoice_sections.py, backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf/parser.py` (python, 202 loc) — Servicio de parsing de PDFs con OpenDataLoader…
  symbols: class ParsedElement; class ParsedDocument; def _ensure_java(); def _parse_with_opendataloader(file_path); def _parse_with_pypdf(file_path, file_bytes); def parse_pdf(file_path, file_bytes)
  imports: dataclasses, io, json, logging, os, pathlib, shutil, tempfile
`backend/app/services/pdf/pdf_base.py` (python, 480 loc) — Utilidades compartidas para la generación de PDFs…
  symbols: def _common_styles(); def _fmt_eur(v); def _make_doc(buffer); def _table_header_style(); def build_theme(config); def table_style_commands(theme, num_data_rows); def _format_date(date_str); def _month_name_es(month); def _traditional_styles(); def _trad_table_style(has_header, grid); def _signature_block(labels, width_mm); def _client_block(client, header_style, body_style, bold_font, slate_color) … (+1)
  imports: datetime
`backend/app/services/pdf_reports/__init__.py` (python, 51 loc) — pdf_reports package — re-exports all public generate_* functions for backward compatibility with ``from app.services.pdf_reports import ...`…
  imports: app
  → usa: backend/app/services/pdf_reports/_fiscal.py, backend/app/services/pdf_reports/_operational.py, backend/app/services/pdf_reports/_snapshot.py, backend/app/services/pdf_reports/_snapshot_monthly.py
`backend/app/services/pdf_reports/_aeat_layout.py` (python, 188 loc) — Helpers de maquetación tipo formulario AEAT (casillas numeradas)…
  symbols: def _draft_badge(s, C); def _section_banner(text, s); def _identificacion_table(tenant, quarter, year, s); def _casilla_code_style(s); def _fmt_casilla(c, pct_codes); def _casillas_table(cmap, codes, s, C, emphasis, pct_codes); def _resultado_badge(resultado, s, pos_label, neg_label)
  imports: __future__, app
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf_reports/_fiscal.py` (python, 41 loc) — Generación de PDFs fiscales — re-export facade…
  imports: app
  → usa: backend/app/services/pdf_reports/_fiscal_modelo303.py, backend/app/services/pdf_reports/_fiscal_modelos.py, backend/app/services/pdf_reports/_fiscal_report.py
`backend/app/services/pdf_reports/_fiscal_modelo303.py` (python, 151 loc) — Generación de PDF: Modelo 303 — Autoliquidación IVA trimestral…
  symbols: def generate_modelo_303_pdf(data)
  imports: app, datetime, io, logging
  → usa: backend/app/services/aeat/casillas_303.py, backend/app/services/pdf/pdf_base.py, backend/app/services/pdf_reports/_aeat_layout.py
`backend/app/services/pdf_reports/_fiscal_modelos.py` (python, 527 loc) — Generación de PDF borrador imprimible para los modelos AEAT 130/111/115/190/ 347/349/390/200/100…
  symbols: def _eur(v); def _footer(s, C); def _kv_table(rows, s, C); def _build(elements); def generate_modelo_130_pdf(data); def generate_modelo_111_pdf(data); def generate_modelo_190_pdf(data); def generate_modelo_347_pdf(data); def generate_modelo_390_pdf(data); def generate_modelo_115_pdf(data); def generate_modelo_349_pdf(data); def _q(periodo) … (+2)
  imports: __future__, app, datetime, io, logging
  → usa: backend/app/services/aeat/casillas_100.py, backend/app/services/aeat/casillas_111.py, backend/app/services/aeat/casillas_115.py, backend/app/services/aeat/casillas_130.py, backend/app/services/aeat/casillas_190.py, backend/app/services/aeat/casillas_200.py, backend/app/services/aeat/casillas_347.py, backend/app/services/aeat/casillas_390.py, backend/app/services/pdf/pdf_base.py, backend/app/services/pdf_reports/_aeat_layout.py
`backend/app/services/pdf_reports/_fiscal_report.py` (python, 632 loc) — Generación de PDF: Informe Fiscal (IVA + IRPF + IS) y persistencia en BD
  symbols: def _fc(); def _fiscal_styles(); def _fiscal_header(company_name, period_label, st); def _fiscal_resumen(resumen, st); def _fiscal_kpis(iva, irpf, is_, st); def _fiscal_iva_section(iva, st); def _fiscal_irpf_section(irpf, st); def _fiscal_is_section(is_, st); def _fiscal_footer(st); def generate_fiscal_report_pdf(snap, company_name, period); async def save_fiscal_report_to_db(pdf_bytes, period, resumen_ejecutivo, tenant_id, uploaded_by, db)
  imports: app, datetime, io, logging, os, uuid
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf_reports/_markdown.py` (python, 254 loc) — Render de informes PDF desde markdown (markdown-it → HTML → xhtml2pdf)…
  symbols: def _classify_blockquotes(html_body); def render_markdown_report(title, body, author, subtitle, tenant_name, logo_path)
  imports: __future__, html, io, os, re
`backend/app/services/pdf_reports/_operational.py` (python, 20 loc) — Generación de PDFs operativos: RGPD, tesorería y morosidad…
  imports: app
  → usa: backend/app/services/pdf_reports/_operational_rgpd.py, backend/app/services/pdf_reports/_operational_treasury.py
`backend/app/services/pdf_reports/_operational_rgpd.py` (python, 161 loc) — Generación de PDF: Registro de Actividades de Tratamiento (Art…
  symbols: def generate_rgpd_registry_pdf(data)
  imports: app, datetime, io, logging
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf_reports/_operational_treasury.py` (python, 505 loc) — Generación de PDFs: informe de tesorería (cash flow) y morosidad
  symbols: def generate_cashflow_report_pdf(data); def generate_delinquency_report_pdf(data)
  imports: app, datetime, io, logging
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf_reports/_snapshot.py` (python, 16 loc) — Generación de PDFs: informe de texto genérico y snapshot mensual de gestión…
  imports: app
  → usa: backend/app/services/pdf_reports/_snapshot_monthly.py, backend/app/services/pdf_reports/_snapshot_text.py
`backend/app/services/pdf_reports/_snapshot_monthly.py` (python, 506 loc) — Generación de PDF: informe mensual de gestión (snapshot)
  symbols: def generate_snapshot_pdf(snap, company_name, month); def _snapshot_text_fallback(snap, company_name, month)
  imports: app, datetime, io, logging
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf_reports/_snapshot_text.py` (python, 117 loc) — Generación de PDF: informe de texto genérico
  symbols: def generate_text_report_pdf(title, content, category)
  imports: app, datetime, io, logging
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf_reports/_structured.py` (python, 549 loc) — Renderer de informes PDF generados por agentes IA…
  symbols: class Kpi; class TableData; class Callout; class ChartSeries; class ChartData; class Section; class Report; def _logo_flowable(logo_path, max_w_mm, max_h_mm); def _build_cover(story, report, st, tenant_name, logo_path); def _build_kpis(kpis, st); def _build_table(td, st); def _build_callout(c, st) … (+5)
  imports: __future__, app, datetime, io, logging, os, pydantic, typing
  → usa: backend/app/services/pdf/pdf_base.py
`backend/app/services/pdf_reports/agent_report.py` (python, 31 loc) — Fachada del renderer de informes PDF (compatibilidad de imports)…
  imports: app
  → usa: backend/app/services/pdf_reports/_markdown.py, backend/app/services/pdf_reports/_structured.py
`backend/app/services/presentacion/__init__.py` (python, 2 loc) — Servicios de presentación telemática y asistida AEAT
`backend/app/services/presentacion/asistida.py` (python, 127 loc) — PRES.ASS — Presentación asistida AEAT para Modelos 131 y 200…
  symbols: class TenantSummary; def _xml_escape(value); def _now_iso(); def build_modelo_131_xml(tenant); def build_modelo_200_xml(tenant); def build_xml(modelo, tenant); def get_sede_link(modelo)
  imports: __future__, dataclasses, datetime, typing, xml
`backend/app/services/project_service.py` (python, 112 loc)
  symbols: def list_projects(…); def create_project(…); def update_project(…); def delete_project(…); def list_tasks(…); def create_task(…); def update_task(…); def delete_task(…)
`backend/app/services/reports/__init__.py` (python, 34 loc) — Reports domain services — aggregation, fiscal, cashflow, delinquency
  imports: app
  → usa: backend/app/services/reports/aggregation.py, backend/app/services/reports/cashflow.py, backend/app/services/reports/delinquency.py, backend/app/services/reports/fiscal.py, backend/app/services/reports/summaries.py
`backend/app/services/reports/_schemas.py` (python, 97 loc) — Pydantic schemas for the reports service layer
  symbols: class SnapshotSectionInvoices; class SnapshotSectionBanking; class SnapshotSectionHR; class SnapshotSectionClients; class CompanySnapshot; class FiscalIVA; class FiscalIRPF; class FiscalIS; class FiscalSnapshot; class ReportOut
  imports: datetime, pydantic, uuid
`backend/app/services/reports/aggregation.py` (python, 326 loc) — Aggregation logic for company snapshots and period parsing…
  symbols: def parse_month(month); def parse_period(period); def build_report_text(snap, company_name); async def aggregate(db, tenant_id, start, end)
  imports: app, calendar, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/analytics/__init__.py, backend/app/services/reports/_schemas.py
`backend/app/services/reports/cashflow.py` (python, 139 loc) — Cashflow / treasury analysis logic…
  symbols: async def build_cashflow_data(db, tenant_id, start_date, end_date)
  imports: app, collections, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/app/services/reports/delinquency.py` (python, 113 loc) — Delinquency / aging bucket analysis logic…
  symbols: async def build_delinquency_data(db, tenant_id)
  imports: app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/app/services/reports/fiscal.py` (python, 418 loc) — Fiscal aggregation logic: IVA, IRPF, IS, libro registro, modelo 303…
  symbols: def _d(x); def _round2(d); def _period_invoices_stmt(tenant_id); def vat_breakdown_by_rate(invoices); async def aggregate_fiscal(db, tenant_id, start, end, period, label); async def build_modelo_303_data(db, tenant_id, quarter, year); async def build_libro_registro_csv(db, tenant_id, year, invoice_type_label)
  imports: app, calendar, csv, datetime, decimal, io, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/reports/_schemas.py
`backend/app/services/reports/modelos_aeat.py` (python, 1081 loc) — Agregación de datos para modelos AEAT 130, 347 y 390 (MOD.130 / MOD.347 / MOD.390)…
  symbols: async def _get_tenant_info(db, tenant_id); async def _invoices_in_period(db, tenant_id); async def build_modelo_130_data(db, tenant_id, quarter, year); async def build_modelo_347_data(db, tenant_id, year); async def _payrolls_in_period(db, tenant_id); async def build_modelo_111_data(db, tenant_id, quarter, year); async def build_modelo_190_data(db, tenant_id, year); async def build_modelo_390_data(db, tenant_id, year); def _is_alquiler(text); async def build_modelo_115_data(db, tenant_id, quarter, year); def _detect_pais_ue(nif); async def build_modelo_349_data(db, tenant_id, quarter, year) … (+3)
  imports: app, calendar, datetime, decimal, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/db/models/models.py
`backend/app/services/reports/summaries.py` (python, 188 loc) — AI-powered executive summaries with deterministic fallback…
  symbols: def _build_deterministic_resumen(month_str, ingresos, gastos, margen, margen_pct, fact_section, hr_section, bank_section, coste_nominas, total_clients, new_clients, top_client_name, top_amount); async def generate_resumen_ejecutivo(month_str, ingresos, gastos, margen, margen_pct, fact_section, hr_section, bank_section, coste_nominas, total_clients, new_clients, top_client_name, top_amount); async def generate_resumen_fiscal(period, label, iva, irpf, is_)
  imports: app, asyncio, logging
  → usa: backend/app/services/reports/_schemas.py
`backend/app/services/sales/__init__.py` (python, 82 loc) — Sales domain services — re-exports for backwards compatibility
  imports: app
  → usa: backend/app/services/sales/commands.py, backend/app/services/sales/queries.py
`backend/app/services/sales/albaran.py` (python, 17 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/sales/commands.py, backend/app/services/sales/queries.py
`backend/app/services/sales/client.py` (python, 6 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/sales/commands.py, backend/app/services/sales/queries.py
`backend/app/services/sales/commands.py` (python, 850 loc) — Sales domain â€” write commands (CQRS-lite)…
  symbols: async def create_client(db, tenant_id, user_id, data); async def update_client(db, tenant_id, client_id, data); async def delete_client(db, tenant_id, client_id); async def create_product(db, tenant_id, data); async def update_product(db, tenant_id, product_id, data); async def delete_product(db, tenant_id, product_id); async def create_stock_movement(db, tenant_id, product_id, data); async def create_quote(db, tenant_id, data); async def update_quote(db, quote_id, tenant_id, update_data); async def delete_quote(db, quote_id, tenant_id); async def convert_to_invoice(db, quote_id, tenant_id, user_id); async def _next_albaran_number(tenant_id, db) … (+13)
  imports: __future__, app, datetime, decimal, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/models.py, backend/app/services/sales/queries.py
`backend/app/services/sales/pos.py` (python, 312 loc) — TPV (Punto de Venta) — servicio…
  symbols: def _pos_stock_reference(session_id); async def _get_open_session(db, tenant_id, user_id); async def _get_session_for_user(db, tenant_id, session_id); def _line_total(quantity, unit_price, tax_pct); async def get_current_session(db, tenant_id, user_id); async def open_session(db, tenant_id, user_id); async def _reload_with_lines(db, tenant_id, session_id); async def add_line(db, tenant_id, session_id, data); async def update_line_quantity(db, tenant_id, session_id, line_id, quantity); async def remove_line(db, tenant_id, session_id, line_id); async def checkout(db, tenant_id, session_id, user_id, payment_method, notes); async def cancel_session(db, tenant_id, session_id) … (+1)
  imports: __future__, app, decimal, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py, backend/app/db/models/pos.py
`backend/app/services/sales/product.py` (python, 25 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/sales/commands.py, backend/app/services/sales/queries.py
`backend/app/services/sales/purchase_order.py` (python, 10 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/sales/commands.py, backend/app/services/sales/queries.py
`backend/app/services/sales/purchase_receiving.py` (python, 112 loc) — Recepción de mercancía contra pedido de compra…
  symbols: async def receive(db)
  imports: __future__, app, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py, backend/app/db/models/orders.py, backend/app/services/inventory/__init__.py
`backend/app/services/sales/queries.py` (python, 376 loc) — Sales domain — read-only queries (CQRS-lite)…
  symbols: async def list_clients(db, tenant_id); async def list_client_invoices(db, tenant_id, client_id); async def list_products(db, tenant_id, skip, limit); async def get_product_by_barcode(db, tenant_id, barcode); async def get_stock_valuation(db, tenant_id); async def list_stock_movements(db, tenant_id, product_id); def _quote_query_with_rels(); async def _get_quote_or_raise(db, quote_id, tenant_id); async def list_quotes(db, tenant_id); async def get_quote(db, quote_id, tenant_id); async def list_albaranes(tenant_id, db); async def get_albaran(albaran_id, tenant_id, db) … (+3)
  imports: __future__, app, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/models.py
`backend/app/services/sales/quote.py` (python, 6 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/sales/commands.py, backend/app/services/sales/queries.py
`backend/app/services/sales/sales_order.py` (python, 6 loc) — Backward-compatibility shim — implementation in queries.py / commands.py
  imports: app
  → usa: backend/app/services/sales/commands.py, backend/app/services/sales/queries.py
`backend/app/services/scheduler.py` (python, 207 loc) — APScheduler — tareas periódicas…
  symbols: def register_jobs(); async def start_scheduler(); async def stop_scheduler()
  imports: __future__, apscheduler, asyncio, logging
`backend/app/services/signing/__init__.py` (python, 41 loc) — Firma electrónica eIDAS con AutoFirma del Estado (F3.11)…
  imports: app
  → usa: backend/app/services/signing/autofirma.py, backend/app/services/signing/sessions.py
`backend/app/services/signing/autofirma.py` (python, 180 loc) — Constructor de URI `afirma://` y parser de respuesta (F3.11)…
  symbols: class AutoFirmaError; class SignatureFormat {autofirma_code}; def file_sha256(data); def build_autofirma_uri(document_bytes); def parse_autofirma_response(payload); def extract_signature_metadata(signed_bytes, fmt)
  imports: __future__, base64, enum, hashlib, json, typing, urllib
`backend/app/services/signing/sessions.py` (python, 186 loc) — Persistencia de sesiones de firma AutoFirma (F3.11)…
  symbols: def _new_session_token(); async def start_signing_session(db, tenant_id); async def process_signed_callback(db, session_token, payload); async def get_signing_status(db, tenant_id, session_token); def _signed_doc_to_dict(sd)
  imports: __future__, app, datetime, secrets, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/signed_document.py, backend/app/services/signing/autofirma.py
`backend/app/services/state_machine.py` (python, 156 loc) — Máquinas de estado para entidades críticas del sistema…
  symbols: class InvalidTransitionError {__init__}; def validate_transition(entity, current_status, new_status); def can_transition(entity, current_status, new_status); def allowed_next_states(entity, current_status); def is_terminal(entity, status)
  imports: __future__
`backend/app/services/system/__init__.py` (python, 7 loc) — System health + precondiciones legales
  imports: app
  → usa: backend/app/services/system/diagnostic_bundle.py, backend/app/services/system/preconditions.py
`backend/app/services/system/diagnostic_bundle.py` (python, 89 loc) — Bundle de diagnóstico (CONT.LOG)…
  symbols: async def build_diagnostic_bundle(db)
  imports: app, datetime, io, json, logging, os, platform, sqlalchemy, sys, zipfile
  → usa: backend/app/core/config.py, backend/app/core/structured_logging.py, backend/app/services/system/preconditions.py
`backend/app/services/system/preconditions.py` (python, 41 loc) — Healthcheck de precondiciones legales para facturación (CONT.KILL)…
  symbols: async def check_invoice_preconditions(db)
  imports: sqlalchemy
`backend/app/services/template_service.py` (python, 399 loc)
  symbols: def _get_or_raise(…); def _clear_default(…); def list_templates(…); def create_template(…); def update_template(…); def delete_template(…); def set_default(…); def seed_defaults(…); def generate_preview(…); def _generate_invoice_sample(…); def _generate_payroll_sample(…); def _generate_albaran_sample(…) … (+2)
`backend/app/services/tenant/__init__.py` (python, 14 loc) — Tenant — servicios de dominio…
  imports: app
  → usa: backend/app/services/tenant/certificates.py
`backend/app/services/tenant/certificates.py` (python, 84 loc) — Instalación de certificados digitales PKCS#12 (.p12 / .pfx) por tenant…
  symbols: class CertificateError; class CertificateInfo; async def install_certificate(file_bytes, password, tenant_id, db)
  imports: __future__, app, dataclasses, datetime, pathlib, sqlalchemy, uuid
  → usa: backend/app/db/models/auth.py, backend/app/services/billing/xades_signer.py
`backend/app/services/tenant_service.py` (python, 376 loc) — Business logic for tenant management
  symbols: async def get_tenant(db, tenant_id); async def update_tenant(db, tenant_id); def _decrypt_keys(cfg); def _build_providers_out(keys); def evaluate_ai_readiness(active_provider, keys, environment, cli_available); async def get_llm_config(db, tenant_id); async def update_llm_config(db, tenant_id); def _run_cmd(args, timeout); def _find_claude_bin(); async def _ensure_claude_installed(); async def claude_code_setup(); async def claude_code_login() … (+1)
  imports: __future__, app, asyncio, json, os, shutil, sqlalchemy, subprocess, typing, uuid
  → usa: backend/app/core/config.py, backend/app/db/models/models.py, backend/app/services/_tenant_schemas.py, backend/app/services/encryption.py
`backend/app/services/treasury/__init__.py` (python, 48 loc) — Servicios de tesorería (F2.7 — Beta → Producción)…
  imports: app
  → usa: backend/app/services/treasury/projection.py, backend/app/services/treasury/remittances.py, backend/app/services/treasury/sepa.py
`backend/app/services/treasury/projection.py` (python, 271 loc) — Cashflow proyectado — F2.7…
  symbols: class CashflowEvent; class CashflowDay {to_dict}; class CashflowAlert {to_dict}; async def _current_balance(db, tenant_id); def _payroll_pay_date(p); def _last_day_of_month(d); async def project_cashflow(db, tenant_id, days_ahead)
  imports: __future__, app, collections, dataclasses, datetime, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/hr.py, backend/app/db/models/models.py
`backend/app/services/treasury/remittances.py` (python, 220 loc) — Remesas SEPA persistidas: creación, historial y ciclo de estados…
  symbols: class RemittanceError; def _ensure_e2e(orders); async def create_transfer_remittance(db, tenant_id, debtor, execution_date, orders); async def create_direct_debit_remittance(db, tenant_id, creditor, collection_date, orders); async def _persist(db, tenant_id, remittance_type, xml_str, summary); async def list_remittances(db, tenant_id); async def get_remittance(db, tenant_id, remittance_id); async def update_remittance_status(db, tenant_id, remittance_id, new_status)
  imports: app, datetime, sqlalchemy, uuid
  → usa: backend/app/db/models/treasury.py, backend/app/services/treasury/sepa.py
`backend/app/services/treasury/sepa.py` (python, 372 loc) — Generación de fichero SEPA pain.001.001.03 para remesas de transferencias salientes (pagos a proveedores) — F2.7…
  symbols: class Pain001Error; class Pain008Error; class TransferOrder; class DebtorParty; def _norm_iban(iban); def _validate_iban(iban); def _validate_amount(amount); def _sanitize_txt(s, maxlen); def build_pain001(debtor, execution_date, orders); def _element(tag, text); class DirectDebitOrder; class CreditorParty … (+1)
  imports: __future__, dataclasses, datetime, decimal, re, uuid, xml
`backend/app/services/user_service.py` (python, 171 loc)
  symbols: def _hash_token(…); def list_users(…); def get_user(…); def create_user(…); def update_user(…); def delete_user(…); def create_invitation(…); def list_invitations(…); def get_invitation(…); def revoke_invitation(…); def get_invitation_by_token(…); def accept_invitation(…)
`backend/app/services/workflow/__init__.py` (python, 100 loc) — Workflow domain services — re-exports for backward compatibility
  imports: app
  → usa: backend/app/services/workflow/activity.py, backend/app/services/workflow/approval.py, backend/app/services/workflow/scheduler.py, backend/app/services/workflow/service.py, backend/app/services/workflow/task.py, backend/app/services/workflow/task_dispatch.py, backend/app/services/workflow/task_runner.py
`backend/app/services/workflow/_execution.py` (python, 422 loc) — Funciones de ejecucion de workflows: run, dispatch, cancel, resume, steps
  symbols: def _build_ai_instruction(workflow); def _infer_domain(workflow); async def _dispatch_deterministic(db, workflow, execution, tenant_id, user_id, intent_prefix, extra_meta); async def _dispatch_reasoning(db, workflow, execution, tenant_id, user_id, intent, extra_meta); async def run_workflow(workflow_id, tenant_id, user_id, db); async def run_workflow_with_context(workflow_id, context_msg, tenant_id, user_id, db); async def cancel_execution(execution_id, workflow_id, tenant_id, db); async def resume_execution(execution_id, workflow_id, tenant_id, db); def _run_deterministic_step(step, idx, prev_output, tenant_id); async def _run_reasoning_step(step, idx, prev_output, base_state); async def execute_deterministic_steps(steps, tenant_id, user_id, task_id)
  imports: app, datetime, logging, sqlalchemy, typing, uuid
  → usa: backend/app/agents/orchestrator/__init__.py, backend/app/agents/tool_registry.py, backend/app/db/models/__init__.py, backend/app/services/workflow/task_dispatch.py
`backend/app/services/workflow/_nlp.py` (python, 146 loc) — Funciones NLP: parsing de lenguaje natural y disparo de eventos
  symbols: async def _load_tenant_employees(tenant_id); async def parse_natural_language(text, tenant_id); async def fire_event(event_name, context, tenant_id, user_id, db)
  imports: app, json, langchain_core, logging, sqlalchemy
  → usa: backend/app/core/llm_factory.py, backend/app/db/base.py, backend/app/db/models/__init__.py, backend/app/db/models/ai_employees.py, backend/app/prompts/__init__.py, backend/app/services/workflow/_ui_graph.py, backend/app/services/workflow/conditions.py
`backend/app/services/workflow/_ui_graph.py` (python, 342 loc) — Funciones de generacion de grafos UI (nodos/aristas ReactFlow) para workflows
  symbols: def _per_domain_instruction(agent, master, multi); def plan_to_ui_graph(plan, trigger_type); def _pick_employee(domain, employees); def _skill_data(default_label, agent, instruction, employees); def generate_preview_nodes(payload, employees)
  imports: collections
`backend/app/services/workflow/activity.py` (python, 46 loc) — Helper para escribir entradas en el activity_feed…
  symbols: async def log_activity(db, tenant_id, category, message, employee_id, task_id, icon, metadata)
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/models/ai_employees.py
`backend/app/services/workflow/approval.py` (python, 163 loc) — Servicio de aprobaciones — lógica de negocio pura (sin HTTPException)
  symbols: async def list_pending(db, tenant_id); async def decide(db, tenant_id, user_id, approval_id, approved, rejection_reason); async def cleanup_all(db, tenant_id); async def _resume_after_approval(approval, db)
  imports: app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/core/datetime_utils.py, backend/app/db/models/models.py, backend/app/services/audit.py
`backend/app/services/workflow/approval_actions.py` (python, 389 loc) — Ejecución de acciones financieras retenidas tras aprobación humana…
  symbols: def register_action(kind); def is_registered(kind); async def execute_approved_action(payload, db, tenant_id); async def create_action_approval(); async def _exec_create_journal_entry(params, db, tenant_id); async def _exec_approve_payroll(params, db, tenant_id); async def _exec_create_invoice(params, db, tenant_id); async def _exec_inventory_batch_adjust(params, db, tenant_id); async def _exec_gated_tool_call(params, db, tenant_id); async def _exec_send_email(params, db, tenant_id); async def _exec_reconcile_transaction(params, db, tenant_id); async def _exec_inventory_batch_update(params, db, tenant_id)
  imports: __future__, app, collections, datetime, decimal, logging, sqlalchemy, uuid
  → usa: backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/accounting.py, backend/app/db/models/hr.py, backend/app/db/models/models.py
`backend/app/services/workflow/conditions.py` (python, 102 loc) — Evaluador de condiciones para workflows…
  symbols: def _get_field(context, field); def _eval_leaf(condition, context); def evaluate_conditions(condition, context)
  imports: __future__, logging, typing
`backend/app/services/workflow/db_conditions.py` (python, 96 loc) — Pre-fetch de condiciones basadas en BD para workflows…
  symbols: def _collect_provider_leaves(condition); async def resolve_db_conditions(condition, tenant_id, db, context)
  imports: __future__, app, logging, sqlalchemy, uuid
  → usa: backend/app/services/workflow/db_query_providers.py
`backend/app/services/workflow/db_query_providers.py` (python, 116 loc) — Registro de query providers para condiciones de workflow basadas en BD…
  symbols: async def _billing_invoice_count_by_status(tenant_id, db, params); async def _billing_unpaid_total(tenant_id, db, params); async def _billing_overdue_count(tenant_id, db, params); async def _hr_payrolls_this_month(tenant_id, db, params); async def _hr_employee_count(tenant_id, db, params); async def _hr_draft_payroll_count(tenant_id, db, params)
  imports: __future__, app, collections, datetime, logging, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/models.py
`backend/app/services/workflow/default_routines.py` (python, 145 loc) — Rutinas de oficio — workflows event_based sembrados por defecto en cada tenant…
  symbols: async def seed_default_routines(db, tenant_id, user_id)
  imports: __future__, app, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/workflows.py, backend/app/services/__init__.py
`backend/app/services/workflow/fiscal_approval.py` (python, 236 loc) — Aprobación humana obligatoria para actos fiscales AEAT (SEC.APR)…
  symbols: def compute_payload_hash(payload); def build_expected_approval_text(model_aeat, period); async def request_fiscal_approval(db); def _validate_approval_text(provided, expected); async def approve_fiscal(db); async def reject_fiscal(db); async def has_valid_fiscal_approval(db)
  imports: app, datetime, hashlib, json, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/tasks.py
`backend/app/services/workflow/recovery.py` (python, 136 loc) — Startup recovery — limpia zombies dejados por reinicios del backend…
  symbols: async def recover_stale_executions()
  imports: __future__, app, datetime, logging, sqlalchemy
  → usa: backend/app/core/datetime_utils.py, backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/services/workflow/scheduler.py` (python, 114 loc) — Scheduler-layer DB helpers for workflow execution…
  symbols: async def get_active_scheduled_workflows(db); async def has_active_execution(db, workflow_id); async def get_last_execution(db, workflow_id); async def create_execution(db, workflow, trigger_payload); async def create_task_for_execution(db, workflow, execution, domain, user_intent, initial_status, meta); async def get_stuck_executions(db, cutoff); async def mark_executions_failed(db, executions, note)
  imports: __future__, app, datetime, logging, sqlalchemy
  → usa: backend/app/db/models/models.py
`backend/app/services/workflow/service.py` (python, 199 loc)
  symbols: def list_workflows(…); def create_workflow(…); def get_workflow(…); def update_workflow(…); def delete_workflow(…); def recent_completions(…); def get_execution(…); def list_executions(…); def get_execution_logs(…)
`backend/app/services/workflow/task.py` (python, 255 loc) — Business logic for task management
  symbols: async def _build_conversation_history(db, parent_task_id, tenant_id, max_turns); async def _enqueue_task(task_id); async def create_task(db); async def list_tasks(db); async def get_task(db); async def cancel_task(db); async def cleanup_tasks(db); async def get_task_audit(db)
  imports: app, logging, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/app/services/workflow/task_dispatch.py` (python, 87 loc) — Dispatch de tareas…
  symbols: def _celery_available(); async def dispatch_orchestrator(task_id, tenant_id); async def dispatch_resume_orchestrator(task_id, tenant_id); async def dispatch_node_engine(execution_id, tenant_id); async def dispatch_resume_node_engine(execution_id, from_node_id, delay_seconds, tenant_id); async def cancel_task(task_id)
  imports: app, logging
  → usa: backend/app/core/config.py, backend/app/services/workflow/task_runner.py
`backend/app/services/workflow/task_event_hub.py` (python, 99 loc) — Pub/sub in-process por `task_id` para SSE streaming (UI.AGT)…
  symbols: class TaskEventHub {__init__, subscribe, unsubscribe, publish, signal_end, stream}
  imports: __future__, asyncio, collections, logging, typing
`backend/app/services/workflow/task_runner.py` (python, 102 loc) — In-process async task runner…
  symbols: class TaskRunner {__init__, submit, submit_delayed, cancel, is_running, active_count, shutdown}
  imports: asyncio, collections, logging, typing
`backend/app/services/workflow_marketplace/__init__.py` (python, 39 loc) — Marketplace de workflows (F3.10) — catálogo + import/export YAML…
  imports: app
  → usa: backend/app/services/workflow_marketplace/catalog.py, backend/app/services/workflow_marketplace/io_yaml.py, backend/app/services/workflow_marketplace/seed.py
`backend/app/services/workflow_marketplace/catalog.py` (python, 127 loc) — Catálogo de plantillas + instalación en el tenant (F3.10)
  symbols: def _template_to_dict(t); async def list_templates(db); async def get_template(db, slug); async def install_template(db, tenant_id, slug); async def _ensure_unique_name(db, tenant_id, base_name)
  imports: __future__, app, sqlalchemy, typing, uuid
  → usa: backend/app/db/models/workflow_template.py, backend/app/db/models/workflows.py
`backend/app/services/workflow_marketplace/io_yaml.py` (python, 127 loc) — Import/export YAML de workflows (F3.10)…
  symbols: class WorkflowYamlError; def export_workflow_to_yaml(workflow); def _parse_yaml(yaml_str); async def import_yaml_as_workflow(db, tenant_id, yaml_str)
  imports: __future__, app, sqlalchemy, typing, uuid, yaml
  → usa: backend/app/db/models/workflows.py
`backend/app/services/workflow_marketplace/seed.py` (python, 116 loc) — Seed de plantillas oficiales del marketplace (F3.10)…
  symbols: async def seed_official_templates(db)
  imports: __future__, app, sqlalchemy
  → usa: backend/app/db/models/workflow_template.py
`backend/app/services/ws_relay.py` (python, 76 loc) — Redis pub/sub → WebSocket relay…
  symbols: async def start_ws_relay(); async def stop_ws_relay(); async def _run(redis_url)
  imports: __future__, asyncio, json, logging
`backend/app/skills/__init__.py` (python, 13 loc) — Skills modulares del orquestador (OOP, BaseSkill.run())…
  → usa: backend/app/skills/base.py, backend/app/skills/registry.py
`backend/app/skills/base.py` (python, 51 loc)
  symbols: class SkillInput; class BaseSkill {name, description, input_schema, run}
  imports: abc, pydantic, typing
`backend/app/skills/hello_world.py` (python, 51 loc)
  symbols: class HelloWorldInput; class HelloWorldSkill {name, description, input_schema, run}
  imports: app, logging, pydantic, typing
  → usa: backend/app/skills/base.py
`backend/app/skills/registry.py` (python, 58 loc)
  symbols: class SkillRegistry {register, get_skill, get_all_skills, load_builtins}
  imports: app, importlib, inspect, logging, pathlib
  → usa: backend/app/skills/base.py
`backend/app/workers/__init__.py` (python, 1 loc)
`backend/app/workers/_orchestrator_context.py` (python, 457 loc) — Sub-módulo del orquestador: funciones que construyen contexto de ejecución (estado inicial, carga de tarea, contexto de tenant, streaming, a…
  symbols: async def _build_tenant_context(tenant_id, db); async def _load_and_start_task(task_id, db); async def _build_initial_state(task, task_id, db); async def _broadcast(tenant_id, message); async def _stream_and_log(task_id, initial_state, orchestrator, usage_callback); async def _load_task_and_approval(task_id, db); async def _create_invoice_from_approval(task, payload_data, db); async def _execute_from_approval(task, payload_data, db)
  imports: app, asyncio, datetime, decimal, logging, sqlalchemy, traceback, uuid
  → usa: backend/app/db/models/auth.py, backend/app/db/models/models.py, backend/app/services/exec_log_store.py
`backend/app/workers/_orchestrator_state.py` (python, 141 loc) — Sub-módulo del orquestador: funciones que actualizan estado en BD (Task, Workflow, WorkflowExecution, TenantDocument)
  symbols: async def _mark_task_failed(task_id, error_msg); def _plan_to_ui_graph(plan, trigger_type); async def _save_final_state(task, final_state, db); async def _update_workflow_topology(task, plan_list, db); async def _update_workflow_execution(task, db); async def _update_linked_document(task, final_state, db); async def _sync_workflow_artifacts(task, final_state, db)
  imports: app, datetime, logging, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/app/workers/backfill_alerts.py` (python, 65 loc) — Job APScheduler — detección diaria de tenants pendientes de backfill (A.5)…
  symbols: async def check_pending_verifactu_backfills()
  imports: __future__, app, logging
  → usa: backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/services/billing/backfill_verifactu.py
`backend/app/workers/celery_tasks.py` (python, 96 loc) — Celery task wrappers for the orchestrator…
  imports: __future__, app, asyncio, logging
  → usa: backend/app/celery_app.py
`backend/app/workers/tasks_node_engine.py` (python, 167 loc) — Tareas del motor de nodos (workflows visuales con condicionales, delays, etc.)…
  symbols: async def run_node_engine(execution_id, tenant_id); async def resume_node_engine(execution_id, from_node_id, tenant_id); async def _run_node_engine(execution_id, tenant_id); async def _resume_node_engine(execution_id, from_node_id, tenant_id)
  imports: app, asyncio, logging
  → usa: backend/app/services/idempotency.py
`backend/app/workers/tasks_orchestrator.py` (python, 440 loc) — Tareas del orquestador LangGraph…
  symbols: def _is_transient_error(exc); async def _retry(label, task_id, fn, guard); async def execute_orchestrator(task_id, tenant_id); async def resume_orchestrator(task_id, tenant_id); async def _set_agent_status(db, employee_id, tenant_id, status); async def _log_task_completion(db, task, final_state, employee_id, tenant_id); async def _broadcast(manager, tenant_id, payload); async def _record_run_usage(db); async def _execute_orchestrator(task_id, tenant_id_hint); async def _resume_orchestrator(task_id, tenant_id_hint)
  imports: app, asyncio, logging
  → usa: backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/services/exec_log_store.py, backend/app/services/idempotency.py, backend/app/workers/_orchestrator_context.py, backend/app/workers/_orchestrator_state.py
`backend/app/workers/tasks_scheduler.py` (python, 656 loc) — Tareas periodicas: workflows programados, facturas recurrentes, limpieza de ejecuciones…
  symbols: def _next_due_run(config, now); def _infer_domain_from_text(text); def _calc_line_totals(line); async def _dispatch_workflow(db, wf, execution, trigger_source, guard, idempotency_key); async def check_scheduled_workflows(); async def _check_scheduled_workflows(); async def catchup_missed_workflows(); async def _catchup_missed_workflows(); async def process_recurring_invoices(); async def _process_recurring_invoices(); async def cleanup_stuck_executions(); async def _cleanup_stuck_executions() … (+9)
  imports: app, croniter, datetime, logging, sqlalchemy, zoneinfo
  → usa: backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/idempotency.py, backend/app/services/workflow/__init__.py, backend/app/services/workflow/conditions.py, backend/app/services/workflow/db_conditions.py, backend/app/services/workflow/scheduler.py, backend/app/services/workflow/task_dispatch.py
`backend/pyproject.toml` (toml, 189 loc)
  symbols: [tool.poetry]; [tool.poetry.dependencies]; [tool.poetry.extras]; [tool.poetry.group.dev.dependencies]; [tool.poetry.group.cloud.dependencies]; [tool.poetry.group.localml.dependencies]; [build-system]; [tool.ruff]; [tool.ruff.lint]; [tool.mypy]; [[tool.mypy.overrides]; [[tool.mypy.overrides] … (+3)
`backend/scripts/audit_aiemployees_contract.py` (python, 95 loc) — Audit del contrato del AIEmployee custom sobre la BD actual…
  symbols: async def main()
  imports: __future__, app, asyncio, pathlib, sqlalchemy, sys
  → usa: backend/app/db/base.py, backend/app/db/models/ai_employees.py, backend/app/services/ai/employee_contract.py
`backend/scripts/audit_domain_completeness.py` (python, 113 loc) — Audit de exhaustividad del Coordinador…
  symbols: def _extract_set_literal(src, name); def _extract_dispatcher_keys(src); def _extract_dict_keys(src, name); def main()
  imports: __future__, pathlib, re, sys
`backend/scripts/check_migration.py` (python, 142 loc) — Pre-commit hook: exige migración si el commit toca `db/models/` (ALB.6)…
  symbols: def _staged_files(diff_filter); def _staged_diff(path); def _commit_message_marker_present(); def check_staged(); def main()
  imports: __future__, argparse, os, pathlib, re, subprocess, sys
`backend/scripts/ci_init_db.py` (python, 33 loc) — Inicializa el schema de BD para CI: create_all desde modelos + stamp head…
  imports: alembic, app, os, sqlalchemy, sys
  → usa: backend/app/main.py, backend/app/db/base.py
`backend/scripts/create_demo_workflows.py` (python, 247 loc) — Crea tres workflows de demostración: 1…
  symbols: def _nodes_reasoning(); def _edges_reasoning(); def _nodes_deterministic(); def _edges_deterministic(); def _nodes_parallel(); def _edges_parallel(); async def main()
  imports: app, asyncio, sqlalchemy
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/scripts/create_user.py` (python, 20 loc)
  symbols: async def test()
  imports: asyncio, httpx
`backend/scripts/db_drift.py` (python, 151 loc) — Detección de drift entre BD viva y Base.metadata (ALB.2)…
  symbols: class DriftReport {has_drift, format}; async def detect_drift(db_url); async def _main(args); def main()
  imports: __future__, app, argparse, asyncio, dataclasses, os, sqlalchemy, sys
  → usa: backend/app/db/models/__init__.py, backend/app/db/base.py
`backend/scripts/db_sync.py` (python, 14 loc)
  symbols: async def init_models()
  imports: app, asyncio
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/scripts/full_system_test.py` (python, 1411 loc) — ╔══════════════════════════════════════════════════════════════════════════════╗ ║ [DEPRECATED] AUTOMATIZAPYME — TEST INTEGRAL DEL SISTEMA ║…
  symbols: def ok(section, detail); def fail(section, detail); def info(msg); def section(title); async def poll_task(client, task_id, max_wait); async def test_auth(client); async def test_clientes(client); async def test_productos(client); async def test_facturas(client, client_id, prod_id); async def test_presupuestos(client, client_id); async def test_pedidos_venta(client, client_id, prod_id); async def test_pedidos_compra(client, supplier_id, prod_id) … (+15)
  imports: asyncio, datetime, httpx
`backend/scripts/gen_contrato.py` (python, 69 loc)
  symbols: def s(text); def p(text, style); def h(text)
  imports: reportlab
`backend/scripts/gen_key.py` (python, 8 loc)
  imports: cryptography, secrets
`backend/scripts/inject_demo_credentials.py` (python, 51 loc)
  symbols: async def inject_demo_credentials()
  imports: app, asyncio, os, sqlalchemy, sys
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/encryption.py
`backend/scripts/llm_log_tail.py` (python, 110 loc) — Inspector ligero del trace JSONL escrito por LLMTraceCallback…
  symbols: def _load(file); def _print_grouped(items); def main()
  imports: __future__, argparse, collections, datetime, json, pathlib, sys
`backend/scripts/seed_advanced_workflow.py` (python, 257 loc)
  symbols: def seed(…)
`backend/scripts/seed_demo.py` (python, 382 loc) — Seed de datos demo para AutomatizaCore…
  symbols: def d(days_ago); def inv_total(base, tax); async def reset_tenant_data(db, tenant_id); async def seed(reset); async def clear_only()
  imports: app, asyncio, datetime, os, sqlalchemy, sys, uuid
  → usa: backend/app/core/config.py, backend/app/db/models/models.py
`backend/scripts/seed_user_data.py` (python, 537 loc) — Seed script — populates ALL sections with realistic demo data via HTTP API…
  symbols: def url(path); def headers(); def post(path, data, label); def login(email, password); def iso(dt); def date_str(dt); def seed_clients(); def seed_products(); def seed_invoices(client_ids, product_ids); def seed_quotes(client_ids, product_ids); def seed_purchase_orders(client_ids); def seed_sales_orders(client_ids) … (+8)
  imports: argparse, datetime, httpx, sys, time
`backend/scripts/smoke_demo.py` (python, 181 loc)
  symbols: async def main()
  imports: asyncio, datetime, httpx
`backend/scripts/smoke_orchestrator.py` (python, 503 loc) — Smoke end-to-end del Coordinador (agents/orchestrator)…
  symbols: async def _create_task_row(prompt_text); def _initial_state(prompt_text, task_id); async def run_one(orchestrator, prompt_id, prompt_text, comment); def _preview(output); def _verdict(r); def _format_row(r); def _write_report(results, sent_emails); async def main()
  imports: __future__, argparse, asyncio, datetime, dotenv, json, os, pathlib, sys, time, unittest, uuid
`backend/scripts/smoke_tasks_workflows.py` (python, 151 loc)
  symbols: async def main()
  imports: asyncio, httpx
`backend/scripts/test_agents.py` (python, 242 loc) — [DEPRECATED] Harness de testeo de agentes individuales (sin orchestrator)…
  symbols: def _initial_state(prompt); def _extract_tools_called(messages); def _extract_final_response(messages); async def _run_one(agent_name, label, prompt, graph, timeout); async def main()
  imports: argparse, asyncio, dotenv, json, os, pathlib, sys, time, uuid
`backend/scripts/test_all.py` (python, 494 loc) — [DEPRECATED] test_all.py -- Test integral del sistema AutomatizaCore con MockLLM…
  symbols: def ok(msg); def fail(msg, detail); def section(title); def api(method, path, token); def wait_task(task_id, token, max_wait)
  imports: argparse, requests, sys, time
`backend/scripts/test_prompts.py` (python, 293 loc) — [DEPRECATED] Harness de testeo del orquestador y sus agentes por prompts…
  symbols: def _initial_state(prompt, metadata); async def _create_task_row(state); async def _delete_task_row(task_id); async def _run_one(case, timeout); def _extract_response_preview(results); def _print_row(r); def _summary(results); async def main()
  imports: app, argparse, asyncio, dotenv, json, pathlib, sys, time, traceback, uuid
  → usa: backend/app/agents/orchestrator/__init__.py, backend/app/agents/orchestrator/state.py, backend/app/db/base.py, backend/app/db/models/tasks.py
`backend/scripts/test_security.py` (python, 273 loc) — [DEPRECATED] Harness de seguridad / adversarial…
  symbols: def _state(intent, task_id); async def _create_task(conn, task_id, intent); async def _delete_task(conn, task_id); def _check_leak(text, markers); async def _run_attack(conn, attack, timeout); async def main()
  imports: app, asyncio, asyncpg, dotenv, json, os, pathlib, sys, time, uuid
  → usa: backend/app/agents/orchestrator/__init__.py
`backend/scripts/update_aeat_xsd.py` (python, 76 loc) — Descarga/actualiza los XSD oficiales de AEAT VeriFactu…
  symbols: def _download(client, url, dest); def main()
  imports: __future__, httpx, pathlib, sys
`backend/scripts/update_prompt_snapshots.py` (python, 45 loc) — Regenera la baseline de snapshots de prompts (QA.PRM)…
  symbols: def collect(); def main()
  imports: __future__, hashlib, json, pathlib
`backend/tasks/reports/erp_seed_recon.md` (markdown, 167 loc) — ERP Seed / Function-Test Recon
  symbols: # ERP Seed / Function-Test Recon; ## 1. EXISTING SEEDERS; ## 2. TEST / SMOKE SCRIPTS; ## 3. DOMAIN → ENTITY MAP (`app/db/models/*.py`); ## 4. SERVICE-LAYER CREATE FUNCTIONS (call directly to bulk-populate, no LLM); ## 5. CURRENT DB STATE (live, read-only); ## BLOCKERS / FLAGS for the mass-seed script
`backend/tests/__init__.py` (python, 1 loc)
`backend/tests/conftest.py` (python, 227 loc) — Fixtures compartidas para todos los tests…
  symbols: def _visit_JSONB(self, type_); async def setup_db(); async def _override_get_db(); async def db(); async def client(); async def seed_tenant_and_user(db); async def auth_client(client, seed_tenant_and_user); async def seed_second_tenant_and_user(db); async def auth_client_b(seed_second_tenant_and_user)
  imports: app, collections, cryptography, os, pytest_asyncio, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/core/security.py, backend/app/main.py, backend/app/middleware/rate_limit.py
`backend/tests/fixtures/prompt_snapshots.json` (json, 34 loc)
  symbols: key: app/agents/accounting/prompts.py; key: app/agents/banking/prompts.py; key: app/agents/billing/prompts.py; key: app/agents/compliance/prompts.py; key: app/agents/crm/prompts.py; key: app/agents/documents/prompts.py; key: app/agents/email/prompts.py; key: app/agents/excel/prompts.py; key: app/agents/hr/prompts.py; key: app/agents/inventory/prompts.py; key: app/agents/marketing/prompts.py; key: app/agents/rag/prompts.py … (+8)
`backend/tests/integration/__init__.py` (python, 1 loc)
`backend/tests/integration/test_orchestrator_dispatch.py` (python, 134 loc) — Smoke de integración del path Coordinador → dispatch de agentes…
  symbols: async def _seed_tenant_and_task(user_intent); def _initial_state(tenant_id, task_id, user_intent); async def _run_dispatch(user_intent); async def test_orchestrator_dispatch_returns_structured_state(); async def test_dispatch_results_follow_agentresult_contract(); async def test_dispatch_does_not_leave_task_pending_without_trace()
  imports: app, asyncio, unittest, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py
`backend/tests/test_accounting_agent.py` (python, 173 loc) — Tests for the accounting agent: graph structure, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_graph_entry_point(); def test_seven_tools_registered(); def test_tool_names(); def test_tools_have_docstrings(); def test_finalize_node_extracts_last_message_content(); def test_finalize_node_handles_non_string_content(); async def test_agent_node_builds_initial_messages(); async def test_agent_node_continues_existing_messages(); async def test_agent_node_accumulates_agent_results()
  imports: langchain_core, pytest, unittest
`backend/tests/test_aeat_certificate_key.py` (python, 39 loc) — La custodia de certificados AEAT debe funcionar con la clave del desktop…
  symbols: def _desktop_style_key(); def test_fernet_works_with_desktop_base64url_key(monkeypatch); def test_fernet_still_works_with_valid_fernet_key(monkeypatch)
  imports: app, base64, os
  → usa: backend/app/services/aeat/__init__.py
`backend/tests/test_agent_execution_trace.py` (python, 149 loc) — Tests para AgentExecutionTrace (SEC.WORM + AI Act compliance)
  symbols: class TestAgentExecutionTrace {test_traza_minima_se_persiste, test_prompt_y_output_se_hashean, test_tokens_y_coste_se_persisten, test_tool_calls_json_se_persiste, test_status_error_con_error_class, test_execution_id_link, test_prompt_none_devuelve_hash_none, test_multiples_trazas_misma_execution}
  imports: app, decimal, hashlib, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/tasks.py, backend/app/services/observability/agent_trace.py
`backend/tests/test_agent_invoice_barrier.py` (python, 164 loc) — Regresión de la barrera fiscal del agente de facturación (B2 / B11, 2026-06-25)…
  symbols: async def _seed_client(db, tenant_id); def _invoice(tenant_id, client_id); def _verifactu_record(tenant_id, invoice_id); async def _reload(db, invoice_id); async def test_agente_no_edita_importes_con_registro_verifactu(db, seed_tenant_and_user); async def test_agente_si_edita_notas_con_registro_verifactu(db, seed_tenant_and_user); async def test_agente_recalcula_importes_con_decimal_sin_registro(db, seed_tenant_and_user); async def test_agente_no_cancela_factura_pagada(db, seed_tenant_and_user); async def test_agente_admite_transicion_a_sent(db, seed_tenant_and_user)
  imports: app, datetime, decimal, pytest, sqlalchemy
  → usa: backend/app/agents/billing/_invoice_write_tools.py, backend/app/db/models/billing.py, backend/app/db/models/crm.py
`backend/tests/test_agent_metrics.py` (python, 81 loc) — Tests del wrapper de métricas en invoke_dispatcher…
  symbols: def captured_runs(); async def test_records_success_when_result_success_true(captured_runs, monkeypatch); async def test_records_failed_when_result_success_false(captured_runs, monkeypatch); async def test_records_timeout_and_reraises(captured_runs, monkeypatch); async def test_records_error_and_reraises(captured_runs, monkeypatch)
  imports: app, asyncio, pytest, unittest
  → usa: backend/app/agents/orchestrator/__init__.py
`backend/tests/test_ai_readiness.py` (python, 74 loc) — Tests del estado de configuración de IA (BYOK)…
  symbols: def test_claude_code_no_listo_en_produccion(); def test_claude_code_si_en_desarrollo(); def test_claude_code_si_en_testing(); def test_claude_code_listo_si_cli_disponible(); def test_claude_code_no_listo_si_cli_ausente(); def test_anthropic_con_clave_y_activado_listo(); def test_anthropic_sin_clave_no_listo(); def test_anthropic_desactivado_no_listo(); def test_proveedor_vacio_no_listo(); def test_openai_con_clave_listo()
  imports: app
  → usa: backend/app/services/tenant_service.py
`backend/tests/test_analytics_dashboard.py` (python, 64 loc) — El dashboard de analítica abre por defecto en el último mes CON datos…
  symbols: async def _seed_tenant(invoice_dt); async def test_latest_period_returns_month_of_last_invoice(); async def test_latest_period_none_when_no_invoices()
  imports: app, datetime, decimal, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/analytics/__init__.py
`backend/tests/test_analytics_events.py` (python, 78 loc) — Tests para `track_event` (OPS.MET)
  symbols: class TestTrackEvent {test_evento_canonico_devuelve_true, test_evento_no_canonico_devuelve_false, test_properties_pii_se_scrubean, test_distinct_id_es_hash_no_uuid_plano, test_excepcion_interna_no_propaga, test_lista_canonica_incluye_hitos_funnel}
  imports: app, pytest, uuid
  → usa: backend/app/services/analytics/__init__.py
`backend/tests/test_api_accounting.py` (python, 205 loc) — Tests para endpoints Accounting /api/v1/accounting/*
  symbols: class TestAccountingNoAuth {test_list_journal_no_auth, test_list_assets_no_auth}; class TestJournalEntries {test_list_journal_empty, test_create_journal_entry, test_create_journal_entry_missing_description, test_create_journal_entry_missing_lines, test_create_journal_entry_unbalanced, test_delete_journal_entry, test_delete_journal_entry_not_found, test_list_journal_after_create}; class TestFixedAssets {test_list_assets_empty, test_create_fixed_asset, test_create_fixed_asset_minimal, test_create_fixed_asset_missing_name, test_create_fixed_asset_missing_purchase_date, test_update_fixed_asset, test_update_fixed_asset_not_found, test_delete_fixed_asset}
  imports: datetime, httpx, pytest, uuid
`backend/tests/test_api_admin.py` (python, 44 loc) — Tests para endpoints Admin /api/v1/admin/*
  symbols: class TestAdmin {test_backup_fails_in_test_env, test_restore_requires_sql_file, test_restore_empty_sql_file, test_backup_requires_auth, test_restore_requires_auth}
  imports: httpx, pytest
`backend/tests/test_api_ai_employees.py` (python, 212 loc) — Tests for AI Employees API — full CRUD, error paths, budget enforcement
  symbols: class TestAIEmployeesNoAuth {test_list_requires_auth, test_create_requires_auth, test_get_by_id_requires_auth}; class TestAIEmployees {_create, test_list_empty, test_create_returns_employee, test_create_missing_fields_returns_422, test_get_by_id_returns_employee, test_get_nonexistent_returns_404, test_list_shows_created_employee, test_delete_returns_204}
  imports: httpx, pytest, uuid
`backend/tests/test_api_albaranes.py` (python, 357 loc) — Tests para endpoints Albaranes /api/v1/albaranes/*
  symbols: class TestAlbaranesNoAuth {test_list_albaranes_no_auth, test_create_albaran_no_auth}; class TestAlbaranes {_create_client, test_list_albaranes_empty, test_create_albaran, test_create_albaran_no_client, test_create_albaran_empty, test_get_albaran, test_get_albaran_not_found, test_update_albaran_status}; class TestAlbaranesStockDeduction {_create_product, _create_albaran_with_product, test_confirm_deducts_stock, test_confirm_is_idempotent, test_insufficient_stock_blocks_confirm, test_delivered_after_confirmed_no_double_deduction, test_line_without_product_id_skips_deduction, test_downgrade_to_draft_reverts_stock}
  imports: httpx, pytest, uuid
`backend/tests/test_api_approvals.py` (python, 63 loc) — Tests para endpoints Approvals /api/v1/approvals/*
  symbols: class TestApprovals {test_list_pending_approvals_empty, test_decide_approval_not_found, test_decide_approval_reject_not_found, test_decide_approval_missing_approved_field, test_cleanup_approvals_empty, test_approvals_require_auth, test_cleanup_requires_auth, test_decide_requires_auth}
  imports: httpx, pytest, uuid
`backend/tests/test_api_auth.py` (python, 219 loc) — Tests para los endpoints de autenticación /api/v1/auth/*
  symbols: class TestRegister {test_register_success, test_register_duplicate_email, test_register_duplicate_nif, test_register_invalid_nif_format, test_register_short_password}; class TestRegisterRemoteBlocked {test_register_blocked_through_proxy, test_register_blocked_with_forwarded_for}; class TestLogin {test_login_success, test_login_wrong_password, test_login_nonexistent_email}; class TestRefresh {test_refresh_success, test_refresh_invalid_token, test_refresh_with_access_token_fails}
  imports: httpx, pytest
`backend/tests/test_api_banking.py` (python, 55 loc) — Tests para endpoints Banking /api/v1/banking/*
  symbols: class TestBankingSummary {test_get_summary, test_summary_requires_auth}; class TestTransactions {test_list_transactions_empty, test_transactions_require_auth}; class TestSync {test_sync_sin_psd2_devuelve_409, test_sync_con_flag_demo_genera_movimientos}
  imports: httpx, pytest
`backend/tests/test_api_clients.py` (python, 115 loc) — Tests para endpoints Clients /api/v1/clients/*
  symbols: class TestClientsNoAuth {test_list_clients_no_auth, test_create_client_no_auth}; class TestClients {test_list_clients_empty, test_create_client, test_create_client_minimal, test_create_client_missing_name, test_list_clients_after_create, test_update_client, test_update_client_not_found, test_delete_client}
  imports: httpx, pytest, uuid
`backend/tests/test_api_crm.py` (python, 91 loc) — Tests para endpoints CRM /api/v1/crm/*
  symbols: class TestOpportunities {test_list_opportunities_empty, test_create_opportunity, test_create_opportunity_missing_title, test_opportunities_require_auth}; class TestActivities {test_list_activities_empty, test_create_activity}; class TestEvents {test_list_events_empty, test_create_event}
  imports: httpx, pytest, uuid
`backend/tests/test_api_documents_search.py` (python, 82 loc) — Tests para el endpoint de búsqueda semántica GET /api/v1/documents/search
  symbols: class _FakeEmbedder {aembed_query}; class TestDocumentsSearch {test_empty_query_returns_400, test_no_embedder_returns_503, test_returns_ranked_hits, test_filters_by_tenant}
  imports: httpx, pytest, unittest, uuid
`backend/tests/test_api_email.py` (python, 64 loc) — Tests for email agent routes — POST /messaging/email/send|instruct, GET /messaging/email/status
  symbols: class TestEmailStatus {test_status_returns_configured_false_without_credentials}; class TestEmailSend {test_send_without_credentials_returns_result, test_send_invalid_email_returns_422}; class TestEmailInstruct {test_instruct_returns_success_with_mock_llm, test_instruct_with_task_id}
  imports: httpx, pytest
`backend/tests/test_api_fiscal_payroll.py` (python, 347 loc) — Tests de API: libro registro AEAT (CSV) y nómina determinista (preview + auto)
  symbols: async def test_libro_registro_emitidas_csv(auth_client, seed_tenant_and_user, db); async def test_libro_registro_recibidas_filters_type(auth_client, seed_tenant_and_user, db); async def test_libro_registro_excludes_cancelled_invoices(auth_client, seed_tenant_and_user, db); async def test_libro_registro_respects_year_window(auth_client, seed_tenant_and_user, db); async def test_libro_registro_excludes_following_calendar_year(auth_client, seed_tenant_and_user, db); async def test_libro_registro_only_current_tenant(auth_client, seed_tenant_and_user, db); async def test_libro_registro_empty_year_has_header(auth_client, seed_tenant_and_user); async def test_payroll_preview_requires_base_salary(auth_client, seed_tenant_and_user, db); async def test_payroll_preview_and_auto_match(auth_client, seed_tenant_and_user, db); async def test_payroll_auto_rejects_other_tenant_employee(auth_client, seed_tenant_and_user, db); async def test_payroll_preview_404_unknown_employee(auth_client, seed_tenant_and_user)
  imports: app, datetime, decimal, httpx, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/tests/test_api_health.py` (python, 36 loc) — Tests para endpoints de sistema (/health, /)
  symbols: class TestHealth {test_health_returns_response, test_health_up_reports_latency, test_root_returns_info}
  imports: httpx, pytest
`backend/tests/test_api_hr_coverage.py` (python, 88 loc) — Tests for HR API — validates real responses (replaces != 500 fakes)
  symbols: class TestHrAuth {test_list_employees_unauth}; class TestHrEmployees {test_list_employees_returns_array, test_payroll_preview_nonexistent_employee_returns_404, test_create_employee_with_minimal_fields, test_create_employee_missing_required_fields_returns_422, test_employee_lifecycle_create_then_appears_in_list}; class TestHrPayrolls {test_list_payrolls_returns_array, test_create_payroll_for_unknown_employee_returns_4xx}
  imports: httpx, pytest, uuid
`backend/tests/test_api_hr_document_pdf.py` (python, 33 loc) — Tests para el PDF server-side de documentos de gestoría (2.9 — base de firma)
  symbols: class TestHRDocumentPdf {test_pdf_unknown_returns_404, test_pdf_renders_bytes}
  imports: httpx, pytest, uuid
`backend/tests/test_api_hr_documents.py` (python, 103 loc) — Tests para endpoints HR Documents /api/v1/hr/documents/*
  symbols: class TestHRDocuments {test_list_hr_documents_empty, test_generate_hr_document, test_generate_hr_document_missing_doc_type, test_generate_hr_document_minimal, test_get_hr_document_not_found, test_approve_hr_document_not_found, test_delete_hr_document_not_found, test_list_hr_documents_with_filters}
  imports: httpx, pytest, unittest, uuid
`backend/tests/test_api_hr_full.py` (python, 91 loc) — Tests para endpoints HR /api/v1/hr/*
  symbols: class TestEmployees {test_list_employees_empty, test_create_employee, test_create_employee_minimal, test_create_employee_missing_name, test_update_employee, test_employees_require_auth}; class TestPayrolls {test_list_payrolls_empty, test_create_payroll}
  imports: httpx, pytest
`backend/tests/test_api_integrations.py` (python, 43 loc) — Tests for Integrations API
  symbols: class TestIntegrations {test_list_integrations_unauthorized, test_list_integrations_empty, test_get_integration_not_found, test_create_integration_minimal, test_delete_integration_not_found}
  imports: httpx, pytest
`backend/tests/test_api_invoice_series.py` (python, 128 loc) — Tests de numeración correlativa de facturas (InvoiceSeries) y validación de IVA
  symbols: def _invoice_payload(); async def test_invoice_auto_number_sequential(auth_client, seed_tenant_and_user, db); async def test_invoice_invalid_vat_rejected(auth_client, seed_tenant_and_user, db); async def test_invoice_manual_number_does_not_consume_series_counter(auth_client, seed_tenant_and_user, db)
  imports: app, datetime, httpx, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/tests/test_api_invoices.py` (python, 140 loc) — Tests para endpoints Invoices /api/v1/invoices/* and /api/v1/clients/{id}/invoices
  symbols: class TestInvoicesNoAuth {test_list_invoices_no_auth, test_create_invoice_no_auth}; class TestInvoices {_create_client, test_list_invoices_empty, test_create_invoice, test_create_invoice_no_lines, test_create_invoice_missing_date, test_get_invoice, test_get_invoice_not_found, test_update_invoice_status}
  imports: datetime, httpx, pytest, uuid
`backend/tests/test_api_pos.py` (python, 228 loc) — Tests para endpoints TPV /api/v1/pos/*
  symbols: class TestPosNoAuth {test_current_no_auth, test_open_no_auth}; class TestPosSessions {_create_product, test_current_empty, test_open_session, test_cannot_open_two_sessions, test_add_line_with_product, test_add_line_freetext, test_update_line_quantity, test_remove_line}
  imports: httpx, pytest, uuid
`backend/tests/test_api_products.py` (python, 186 loc) — Tests para endpoints Products /api/v1/products/*
  symbols: class TestProductsNoAuth {test_list_products_no_auth, test_create_product_no_auth}; class TestProducts {test_list_products_empty, test_create_product, test_create_product_minimal, test_create_product_missing_name, test_create_service, test_list_products_after_create, test_update_product, test_update_product_not_found}; class TestStockValuation {test_valuation_empty, test_valuation_sums_quantity_times_cost, test_valuation_flags_missing_cost_price, test_valuation_excludes_inactive}
  imports: httpx, pytest, uuid
`backend/tests/test_api_projects.py` (python, 83 loc) — Tests para endpoints Projects /api/v1/projects/*
  symbols: class TestProjects {test_list_projects_empty, test_create_project, test_create_project_minimal, test_create_project_missing_name, test_projects_require_auth}; class TestProjectTasks {test_list_tasks_empty, test_create_task_standalone, test_create_task_in_project, test_create_task_missing_title}
  imports: httpx, pytest
`backend/tests/test_api_purchase_orders.py` (python, 125 loc) — Tests para endpoints Purchase Orders /api/v1/purchase-orders/*
  symbols: class TestPurchaseOrders {test_list_purchase_orders_empty, test_create_purchase_order, test_create_purchase_order_no_lines, test_create_purchase_order_missing_supplier, test_update_purchase_order, test_update_purchase_order_not_found, test_delete_purchase_order, test_delete_purchase_order_not_found}
  imports: httpx, pytest, tests, uuid
  → usa: backend/tests/conftest.py
`backend/tests/test_api_quotes.py` (python, 128 loc) — Tests para endpoints Quotes /api/v1/quotes/*
  symbols: class TestQuotesNoAuth {test_list_quotes_no_auth, test_create_quote_no_auth}; class TestQuotes {_create_client, test_list_quotes_empty, test_create_quote, test_create_quote_no_lines, test_create_quote_missing_client_id, test_get_quote, test_get_quote_not_found, test_update_quote}
  imports: httpx, pytest, uuid
`backend/tests/test_api_recruitment.py` (python, 90 loc) — Tests para endpoints Recruitment /api/v1/recruitment/*
  symbols: class TestRecruitmentPositions {test_list_positions_empty, test_create_position, test_create_position_minimal, test_create_position_missing_title, test_list_positions_after_create, test_positions_require_auth}; class TestRecruitmentCandidates {test_list_candidates_empty, test_list_candidates_invalid_position, test_candidates_require_auth}
  imports: httpx, pytest, uuid
`backend/tests/test_api_recurring_invoices.py` (python, 150 loc) — Tests para endpoints Recurring Invoices /api/v1/recurring-invoices/*
  symbols: class TestRecurringInvoices {test_list_recurring_invoices_empty, test_create_recurring_invoice, test_create_recurring_invoice_minimal, test_create_recurring_invoice_missing_name, test_create_recurring_invoice_missing_date, test_update_recurring_invoice, test_update_recurring_invoice_not_found, test_delete_recurring_invoice}
  imports: httpx, pytest, tests, uuid
  → usa: backend/tests/conftest.py
`backend/tests/test_api_reports.py` (python, 86 loc) — Tests for Reports API — uses the actual routes (company-snapshot, fiscal, cashflow, delinquency) instead of the non-existent paths the previ…
  symbols: class TestReportsAuth {test_list_unauth}; class TestReportsList {test_list_returns_array}; class TestCompanySnapshot {test_company_snapshot_default_month, test_company_snapshot_invoices_section_shape, test_company_snapshot_with_explicit_month}; class TestFiscalSnapshot {test_fiscal_snapshot_returns_iva_irpf_is}; class TestSpecializedReports {test_cashflow_runs, test_delinquency_runs, test_rgpd_registry_runs}; class TestReportDownload {test_download_nonexistent_report_returns_404}
  imports: httpx, pytest, uuid
`backend/tests/test_api_sales_orders.py` (python, 125 loc) — Tests para endpoints Sales Orders /api/v1/orders/*
  symbols: class TestSalesOrders {test_list_sales_orders_empty, test_create_sales_order, test_create_sales_order_no_lines, test_create_sales_order_missing_client_id, test_update_sales_order, test_update_sales_order_not_found, test_delete_sales_order, test_delete_sales_order_not_found}
  imports: httpx, pytest, tests, uuid
  → usa: backend/tests/conftest.py
`backend/tests/test_api_signing_status.py` (python, 47 loc) — Test del endpoint de estado de firma AutoFirma (F3.11 — polling)
  symbols: class TestSigningStatus {test_unknown_session_returns_404, test_returns_status, test_status_scoped_by_tenant}
  imports: httpx, pytest, uuid
`backend/tests/test_api_tasks_agents.py` (python, 30 loc)
  symbols: async def test_create_task_and_run_mock(client, seed_tenant_and_user)
  imports: httpx, pytest
`backend/tests/test_api_tenant.py` (python, 60 loc)
  symbols: async def test_tenant_me_and_update(client)
  imports: httpx, pytest
`backend/tests/test_api_users.py` (python, 57 loc) — Tests for Users API
  symbols: class TestUsers {test_list_users_unauthorized, test_list_users_empty, test_create_user, test_get_user_me, test_get_user_not_found, test_update_user_not_found, test_delete_user_not_found}
  imports: httpx, pytest
`backend/tests/test_api_workflows.py` (python, 87 loc) — Tests para endpoints Workflows /api/v1/workflows/*
  symbols: class TestWorkflows {test_list_workflows_empty, test_create_workflow, test_create_workflow_missing_name, test_get_workflow_by_id, test_update_workflow, test_delete_workflow, test_workflows_require_auth}
  imports: httpx, pytest
`backend/tests/test_autonomy_gate.py` (python, 174 loc) — Tests del autonomy_gate (AI.AGT wiring)
  symbols: class TestEvaluate {test_default_banking_write_es_manual, test_default_accounting_es_confirm, test_default_crm_es_auto, test_override_policy_se_respeta}; class TestPersistPendingApproval {_task, test_persiste_approval_en_modo_confirm, test_rechaza_persistir_si_mode_no_confirm, test_requiere_task_id}; class TestResponses {test_suggestion_response_manual, test_pending_response_confirm}; class TestSerialize {test_serialize_payload_acepta_uuid}
  imports: app, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/tasks.py, backend/app/services/autonomy.py, backend/app/services/autonomy_gate.py
`backend/tests/test_autonomy_gated_tool.py` (python, 147 loc) — Tests del decorator `gated_tool` (AI.AGT wiring)
  symbols: class TestGatedTool {_patched_session, test_auto_ejecuta_la_tool_real, test_confirm_devuelve_pendiente_y_no_ejecuta, test_manual_devuelve_sugerencia, test_sin_tenant_id_ejecuta_sin_gate, test_tenant_id_no_uuid_ejecuta_sin_gate, test_summary_default_menciona_tool_y_dominio, test_dominio_crm_default_auto_ejecuta}
  imports: app, pytest, unittest
  → usa: backend/app/services/autonomy.py, backend/app/services/autonomy_gate.py
`backend/tests/test_autonomy_policy.py` (python, 135 loc) — Tests del servicio de autonomía por dominio (SEC.AUT)
  symbols: class TestDefaults {test_banking_write_es_manual, test_accounting_es_confirm, test_marketing_es_confirm, test_recruitment_es_confirm, test_resto_es_auto}; class TestServiceCRUD {test_check_autonomy_devuelve_default_sin_fila, test_set_policy_persiste, test_set_policy_upsert, test_set_policy_rechaza_dominio_desconocido, test_set_policy_rechaza_modo_invalido, test_reset_vuelve_al_default, test_list_policies_marca_is_default, test_policies_aisladas_entre_tenants}; class TestKnownDomains {test_dominios_minimos_presentes, test_defaults_solo_para_dominios_conocidos}
  imports: app, pytest
  → usa: backend/app/services/autonomy.py
`backend/tests/test_backfill_verifactu.py` (python, 170 loc) — Tests del backfill histórico Verifactu (A.5)
  symbols: def _mk_invoice(tenant_id, client_id); class TestBackfillVerifactu {_seed, test_backfill_vacio_si_no_hay_facturas, test_backfill_genera_cadena_cronologica, test_backfill_es_idempotente, test_backfill_marca_is_backfilled_true, test_backfill_continua_cadena_existente, test_list_tenants_pending_backfill_detecta, test_list_tenants_pending_backfill_vacio_tras_backfill}
  imports: app, datetime, decimal, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/billing/backfill_verifactu.py, backend/app/services/billing/verifactu_chain.py
`backend/tests/test_backup.py` (python, 249 loc) — Tests del módulo de backup automático…
  symbols: def test_parse_db_url_postgresql_asyncpg_format(); def test_parse_db_url_plain_postgresql_format(); def test_parse_db_url_falls_back_to_defaults(); def test_rotate_backups_deletes_old_dumps(tmp_path); def test_rotate_backups_skips_non_dump_files(tmp_path); def test_rotate_backups_returns_zero_on_missing_dir(tmp_path); async def test_run_backup_job_skips_when_disabled(monkeypatch); async def test_create_backup_returns_none_when_pg_dump_missing(monkeypatch, tmp_path); async def test_create_backup_invokes_pg_dump_with_correct_flags(monkeypatch, tmp_path); def test_list_backups_returns_sorted_desc(monkeypatch, tmp_path); def test_list_backups_returns_empty_when_dir_missing(monkeypatch, tmp_path); def test_resolve_safe_rejects_path_traversal(monkeypatch, tmp_path) … (+7)
  imports: app, datetime, os, pathlib, pytest, time, unittest
  → usa: backend/app/services/backup/__init__.py
`backend/tests/test_backup_b2.py` (python, 128 loc) — Tests para cifrado E2E y retención de backup B2 (BAK.B2)
  symbols: class TestCrypto {test_round_trip_basico, test_password_incorrecto_falla, test_blob_corrupto_falla, test_dos_cifrados_mismo_input_distinto_blob, test_blob_demasiado_corto, test_derive_key_determinista_misma_sal, test_derive_key_password_vacio_lanza, test_derive_key_salt_invalido}; class TestRollingRetention {test_vacio_devuelve_vacio, test_backup_de_hoy_se_conserva, test_backup_de_hace_60_dias_es_purgado_si_no_es_mensual, test_snapshot_mensual_de_hace_5_meses, test_snapshot_de_hace_2_anos_se_purga, test_combina_diario_y_mensual_sin_duplicar}
  imports: app, datetime, pytest
  → usa: backend/app/services/backup/__init__.py
`backend/tests/test_backup_b2_transport.py` (python, 257 loc) — Tests del cliente HTTPS Backblaze B2 (BAK.B2 transport)
  symbols: def _resp(status, json_data, content); def _client_mock(); class TestAuthorize {test_devuelve_session_si_200, test_lanza_si_status_no_200, test_error_no_contiene_credenciales}; class TestGetUploadUrl {test_devuelve_tuple}; class TestUploadFile {test_envia_sha1_y_metadata}; class TestListAndDownload {test_list_devuelve_lista_files, test_list_pasa_prefix_en_payload, test_download_devuelve_content}; class TestDeleteFileVersion {test_no_lanza_si_200}; class TestRetry {test_retry_devuelve_resultado_si_exito_tras_fallos, test_retry_agota_y_lanza}; class TestUploadEncrypted {test_cifra_y_sube}; class TestDownloadAndDecrypt {test_descarga_y_descifra_roundtrip}
  imports: app, pytest, unittest
  → usa: backend/app/services/backup/__init__.py
`backend/tests/test_backup_local.py` (python, 214 loc) — Tests para registro de backups locales (BAK.LOC + BAK.VF + BAK.UI)
  symbols: class TestRecordBackup {test_record_full_backup, test_record_verifactu_backup}; class TestGetLastBackup {test_devuelve_none_sin_backups, test_devuelve_el_mas_reciente, test_filtra_por_kind}; class TestComputeFileSha256 {test_sha256_determinista}; class TestBackupStatusForBanner {test_sin_backups_muestra_banner, test_backup_reciente_no_muestra_banner, test_backup_viejo_es_stale}; class TestBackupEndpoints {test_record_endpoint_requiere_auth, test_record_endpoint_persiste, test_record_rechaza_hash_invalido, test_status_endpoint_devuelve_show_banner_true_sin_backups}
  imports: app, datetime, httpx, pytest
  → usa: backend/app/db/models/backup.py, backend/app/main.py, backend/app/services/backup_local.py
`backend/tests/test_bank_migration_import.py` (python, 65 loc) — Migración de movimientos bancarios (carga de extracto histórico)…
  symbols: async def _seed(db); def _row(concepto, importe, fecha, saldo); async def _count(db, tenant_id); class TestBankMigration {test_carga_con_signo_y_sin_conciliar, test_idempotente_recargar_extracto, test_falta_campo_obligatorio_error}
  imports: app, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/accounting.py, backend/app/db/models/models.py, backend/app/services/migration/bulk_import.py
`backend/tests/test_banking_agent.py` (python, 74 loc) — Smoke tests for the banking agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_banking_tools_registered(); async def test_banking_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_banking_auto_reconcile.py` (python, 184 loc) — Tests de auto_reconcile y del pre-filtro SQL de get_reconciliation_suggestions…
  symbols: async def _seed_client(db, tenant_id, name); def _invoice(tenant_id, client_id); def _tx(tenant_id); async def test_auto_reconcile_concilia_match_claro(db, seed_tenant_and_user); async def test_auto_reconcile_ambigua_no_concilia(db, seed_tenant_and_user); async def test_auto_reconcile_respeta_pares_rechazados(db, seed_tenant_and_user); async def test_auto_reconcile_marca_factura_pagada(db, seed_tenant_and_user); async def test_prefiltro_sql_rango_min_max(db, seed_tenant_and_user); async def test_suggestions_sin_txs_devuelve_vacio(db, seed_tenant_and_user)
  imports: app, datetime, decimal, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/models.py, backend/app/services/banking/service.py
`backend/tests/test_billing_agent.py` (python, 70 loc) — Smoke tests for the billing agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_billing_tools_registered(); async def test_billing_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_billing_commands.py` (python, 295 loc) — Tests dirigidos de app/services/billing/commands.py — gaps de cobertura…
  symbols: async def _seed_client(db, tenant_id, name); def _line(unit_price, quantity, tax); async def _seed_invoice(db, tenant_id, client_id); async def test_total_negativo_rechazado_y_no_consume_numero(db, seed_tenant_and_user); async def test_update_status_paid_a_draft_deberia_rechazarse(db, seed_tenant_and_user); async def test_delete_bloqueado_si_hay_registro_verifactu(db, seed_tenant_and_user); async def test_delete_borra_asientos_vinculados(db, seed_tenant_and_user); async def test_delete_bloqueado_si_factura_emitida_numerada(db, seed_tenant_and_user); async def test_journal_entry_descuadrado_rechazado(db, seed_tenant_and_user); async def test_journal_entry_tolera_un_centimo_pero_no_dos(db, seed_tenant_and_user); async def test_run_recurring_genera_factura(db, seed_tenant_and_user); async def test_run_recurring_inexistente_devuelve_none(db, seed_tenant_and_user)
  imports: app, datetime, decimal, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/models.py, backend/app/services/billing/commands.py
`backend/tests/test_billing_validators.py` (python, 256 loc) — Tests unitarios de los validadores deterministas de facturación…
  symbols: def test_nif_validos(nif); def test_nif_invalidos(nif); def test_nif_none_no_revienta(); def test_iban_validos(iban); def test_iban_invalidos(iban); def test_vat_rate_validos(rate); def test_vat_rate_invalidos(rate); def test_vat_rate_normaliza_float_entero(); def test_amount_validos(amount); def test_amount_formato_espanol_se_interpreta_bien(); def test_amount_fuera_de_rango(amount); def test_amount_negativo_mensaje_claro() … (+10)
  imports: app, datetime, decimal, pytest
  → usa: backend/app/agents/shared/validators/billing.py
`backend/tests/test_cache.py` (python, 118 loc) — Tests del wrapper de caché Redis con degradación silenciosa…
  symbols: def _reset_redis_state(monkeypatch); async def test_cache_get_returns_none_without_redis(monkeypatch); async def test_cache_set_returns_false_without_redis(monkeypatch); async def test_cached_json_calls_original_when_no_cache(monkeypatch); async def test_cached_json_uses_cached_value_on_hit(monkeypatch); async def test_cached_json_writes_on_miss(monkeypatch); async def test_cached_json_handles_redis_failure_gracefully(monkeypatch)
  imports: app, pytest
  → usa: backend/app/services/__init__.py
`backend/tests/test_casillas_100.py` (python, 44 loc) — Tests del mapeo de casillas clave del Modelo 100 (IRPF, Renta 2024/2025)
  symbols: def _cmap(data); def test_set_completo(); def test_mapeo_de_la_liquidacion(); def test_editables_marcados(); def test_tolera_datos_ausentes()
  imports: app, decimal
  → usa: backend/app/services/aeat/casillas_100.py
`backend/tests/test_casillas_130.py` (python, 71 loc) — Tests de `build_casillas_130`: mapeo del cálculo a las casillas oficiales 130…
  symbols: def _cmap(data); def test_casilla_03_es_ingresos_menos_gastos(); def test_casilla_04_es_20_pct_del_rendimiento(); def test_casilla_04_nunca_es_negativa(); def test_casilla_07_resta_pagos_y_retenciones(); def test_casilla_19_resultado_final_sin_deducciones(); def test_casillas_editables_marcadas(); def test_set_completo_de_casillas(); def test_tolera_datos_ausentes()
  imports: app, decimal
  → usa: backend/app/services/aeat/casillas_130.py
`backend/tests/test_casillas_190.py` (python, 47 loc) — Tests del mapeo de casillas del Modelo 190 (hoja-resumen: 01/02/03)
  symbols: def _cmap(data); def test_set_completo(); def test_recuento_y_totales_desde_lista(); def test_totales_explicitos_priorizan_sobre_la_lista(); def test_recuento_se_formatea_como_numero(); def test_tolera_datos_ausentes()
  imports: app, decimal
  → usa: backend/app/services/aeat/casillas_190.py
`backend/tests/test_casillas_200.py` (python, 44 loc) — Tests del mapeo de casillas clave del Modelo 200 (Impuesto sobre Sociedades)
  symbols: def _cmap(data); def test_set_completo(); def test_mapeo_de_la_liquidacion(); def test_tipo_de_gravamen_es_porcentaje(); def test_cuota_liquida_coincide_con_integra_y_es_editable(); def test_tolera_datos_ausentes()
  imports: app, decimal
  → usa: backend/app/services/aeat/casillas_200.py
`backend/tests/test_casillas_347.py` (python, 42 loc) — Tests del mapeo de casillas del Modelo 347 (hoja-resumen: 01-04)
  symbols: def _cmap(data); def test_set_completo(); def test_recuento_e_importe_desde_lista(); def test_num_declarables_explicito_prioriza(); def test_arrendamientos_local_negocio_editables_a_cero(); def test_recuento_se_formatea_como_numero()
  imports: app, decimal
  → usa: backend/app/services/aeat/casillas_347.py
`backend/tests/test_casillas_modelos.py` (python, 58 loc) — Tests de los builders de casillas oficiales: 111, 115, 390…
  symbols: def _m(builder, data); def test_111_total_liquidacion(); def test_111_complementaria_resta(); def test_115_resultado_es_casilla_03(); def test_390_devengado_deducible_resultado()
  imports: app, decimal
  → usa: backend/app/services/aeat/casillas_111.py, backend/app/services/aeat/casillas_115.py, backend/app/services/aeat/casillas_390.py
`backend/tests/test_check_migration.py` (python, 101 loc) — Tests del pre-commit hook ALB.6
  symbols: class TestCheckStaged {test_sin_cambios_en_modelos_pasa, test_modelo_con_column_y_sin_migration_falla, test_modelo_con_migration_acompanante_pasa, test_modelo_solo_docstring_no_exige_migration, test_override_env_var, test_relationship_es_significativo, test_foreign_key_es_significativo}
  imports: check_migration, pathlib, sys, unittest
  → usa: backend/scripts/check_migration.py
`backend/tests/test_classifier_custom_contract.py` (python, 83 loc) — Guard de contrato en `_resolve_custom_employee`…
  symbols: def _emp(scope, mem, know, wf); def test_meets_contract_cuenta_capacidades(); class TestResolveCustomContract {test_perfil_no_intercepta, test_empleado_real_si_intercepta, test_seleccion_explicita_se_respeta_aunque_sea_perfil}
  imports: pytest, sqlalchemy, unittest, uuid
`backend/tests/test_classifier_keyword_routing.py` (python, 68 loc) — Routing determinista por keywords (sin LLM)…
  symbols: def test_keyword_routing(intent, expected)
  imports: app, pathlib, pytest, sys
  → usa: backend/app/agents/orchestrator/classifier.py
`backend/tests/test_claude_code_tool_elicitation.py` (python, 153 loc) — Guardia DETERMINISTA de la elicitación de tools del provider `claude_code`…
  symbols: class _T {__init__}; def _model(); def _scripted(monkeypatch, outputs); def test_mention_then_emit_retry_fires_tool(monkeypatch); def test_mention_twice_degrades_to_text(monkeypatch); def test_summary_after_write_no_retry(monkeypatch); def test_read_only_then_mention_write_retries(monkeypatch); def test_refusal_persists_raises(monkeypatch); def test_valid_block_parses_first_try(monkeypatch); def test_malformed_json_literal_newline_recovers(); def test_write_name_detection(); def test_real_cli_action_does_not_crash()
  imports: app, langchain_core, os, pytest, shutil
  → usa: backend/app/core/__init__.py
`backend/tests/test_claude_code_usage.py` (python, 56 loc) — Captura de tokens del provider claude_code → modal de consumo de IA…
  symbols: def test_parse_json_envelope_extracts_text_and_usage(); def test_parse_plain_text_is_fallback_without_usage(); def test_parse_json_without_result_key_is_text_fallback(); def test_parse_envelope_zero_usage_yields_no_meta(); def test_process_response_attaches_usage_metadata_to_message(); def test_process_response_without_usage_leaves_metadata_unset()
  imports: app
  → usa: backend/app/core/__init__.py
`backend/tests/test_clients_unique_constraint.py` (python, 66 loc) — Tests para la constraint UNIQUE(tenant_id, nif) en clients…
  symbols: async def _tenant(db); class TestClientUniqueConstraint {test_no_se_pueden_insertar_dos_clients_mismo_nif_mismo_tenant, test_mismo_nif_distinto_tenant_OK, test_nif_None_permite_multiples, test_nif_vacio_permite_multiples}
  imports: app, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py
`backend/tests/test_collections.py` (python, 266 loc) — Tests de inteligencia de cobros (F3.9)
  symbols: def _inv(tenant_id, client_id); def test_compute_risk_cliente_perfecto(); def test_compute_risk_cliente_con_factura_vencida(); def test_compute_risk_multiples_facturas_vencidas_da_high(); def test_compute_risk_mix_paga_tarde_sin_vencidas(); def test_build_reminder_schedule_4_pasos(); def test_reminder_d30_calcula_intereses_demora(); def test_factura_pagada_no_genera_recordatorios(); def test_factura_sin_due_date_no_genera_recordatorios(); async def test_rank_tenant_collections_ordena_por_score(db, seed_tenant_and_user); async def test_invoices_due_for_reminder_devuelve_solo_fire_date(db, seed_tenant_and_user)
  imports: app, datetime, decimal, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/collections/reminders.py, backend/app/services/collections/risk.py
`backend/tests/test_compliance_agent.py` (python, 69 loc) — Smoke tests for the compliance agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_compliance_tools_registered(); async def test_compliance_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_compliance_business.py` (python, 61 loc) — Tests de negocio del agente compliance…
  symbols: async def test_preventive_rejects_bad_tenant_uuid(); async def test_preventive_rejects_invalid_quarter(); async def test_deadlines_stale_calendar_does_not_invent_dates(); async def test_deadlines_empty_calendar_message()
  imports: app, pytest, unittest
  → usa: backend/app/agents/compliance/tools.py
`backend/tests/test_compliance_tools_signatures.py` (python, 38 loc) — Las tools de compliance deben aceptar tenant_id como kwarg en su args_schema (lo que el LLM ve), aunque no usen el valor — el LLM se lo pasa…
  symbols: class TestComplianceToolsAcceptTenantId {test_check_fiscal_deadlines_args_schema_has_tenant_id, test_check_boe_news_args_schema_has_tenant_id, test_tenant_id_is_optional_in_both}
  imports: __future__, app
  → usa: backend/app/agents/compliance/tools.py
`backend/tests/test_contracts_interview.py` (python, 60 loc) — Tests del asistente conversacional de contratos (Feature 3)
  symbols: class _FakeLLM {__init__, ainvoke}; class TestContractsInterview {test_returns_question_when_not_done, test_extracts_final_contract, test_invalid_type_raises, test_endpoint_invalid_type_422}
  imports: app, httpx, pytest, unittest
  → usa: backend/app/services/documents/contracts_interview.py
`backend/tests/test_core_config.py` (python, 112 loc) — Tests para app.core.config — Settings y validadores
  symbols: class TestSettings {test_settings_is_valid_instance, test_app_name_default, test_app_version_default, test_algorithm_default, test_access_token_expire_minutes, test_refresh_token_expire_days, test_secret_key_loaded_from_env, test_environment_is_testing}; class TestSettingsValidation {test_rejects_default_secret_key, test_rejects_default_encryption_key, test_current_settings_not_defaults}; class TestGetSettings {test_get_settings_returns_same_instance}
  imports: os, pytest
`backend/tests/test_core_datetime_utils.py` (python, 65 loc) — Tests para app.core.datetime_utils.as_aware…
  symbols: class TestAsAware {test_none_devuelve_none, test_naive_se_marca_como_utc, test_aware_no_se_modifica, test_aware_con_otro_tz_no_se_modifica, test_default_tz_alternativo, test_idempotente, test_permite_comparar_con_now_utc}
  imports: app, datetime
  → usa: backend/app/core/datetime_utils.py
`backend/tests/test_core_dependencies.py` (python, 95 loc) — Tests para app.core.dependencies — Inyección de dependencias FastAPI
  symbols: def _mock_request(path); class TestGetCurrentUser {test_valid_token_returns_user, test_invalid_token_raises_401, test_nonexistent_user_raises_401, test_inactive_user_raises_401, test_token_without_sub_raises_401}; class TestRequireRole {test_matching_role_passes, test_non_matching_role_raises_403}
  imports: app, fastapi, pytest, sqlalchemy, unittest, uuid
  → usa: backend/app/core/dependencies.py, backend/app/core/security.py
`backend/tests/test_core_exceptions.py` (python, 133 loc) — Tests para app.core.exceptions — Jerarquía de excepciones
  symbols: class TestAppException {test_default_message, test_custom_message, test_status_code, test_error_type, test_is_exception, test_str_representation}; class TestNotFoundError {test_default_message, test_custom_message, test_status_code, test_error_type, test_inherits_app_exception}; class TestValidationError {test_default_message, test_custom_message, test_status_code, test_error_type, test_inherits_app_exception}; class TestConflictError {test_default_message, test_status_code, test_error_type}; class TestForbiddenError {test_default_message, test_status_code, test_error_type}; class TestExternalServiceError {test_default_message, test_custom_message, test_status_code, test_error_type, test_inherits_app_exception}; class TestExceptionHierarchy {test_all_subclass_app_exception, test_all_are_catchable_as_exception}
  imports: app, pytest
  → usa: backend/app/core/exceptions.py
`backend/tests/test_crm_agent.py` (python, 75 loc) — Smoke tests for the crm agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_crm_tools_registered(); async def test_crm_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_crm_business.py` (python, 85 loc) — Tests de negocio del agente CRM…
  symbols: async def test_create_opportunity_rejects_negative_value(); async def test_create_opportunity_rejects_non_numeric_value(); async def test_create_opportunity_rejects_unknown_stage(); async def test_update_opportunity_stage_rejects_unknown_stage(); async def test_create_and_update_share_same_stage_vocabulary(); def test_valid_stages_matches_frontend_funnel()
  imports: app, pytest
  → usa: backend/app/agents/crm/tools.py
`backend/tests/test_db_drift.py` (python, 66 loc) — Tests del script de drift detection BD vs modelos (ALB.2)
  symbols: class TestDriftReport {test_sin_drift, test_drift_tablas_faltantes, test_drift_tablas_huerfanas, test_drift_columnas_faltantes, test_columnas_ordenadas_deterministicamente}; class TestDetectDrift {test_devuelve_report_vacio_si_bd_es_consistente_con_modelos}
  imports: db_drift, pathlib, pytest, sys
  → usa: backend/scripts/db_drift.py
`backend/tests/test_default_routines.py` (python, 57 loc) — Rutinas de oficio: seed idempotente y wiring con el catálogo de eventos
  symbols: async def test_seed_crea_todas_las_rutinas(db, seed_tenant_and_user); async def test_seed_es_idempotente(db, seed_tenant_and_user); async def test_eventos_de_rutinas_estan_en_catalogo(); async def test_registro_siembra_rutinas(db)
  imports: app, pytest, sqlalchemy
  → usa: backend/app/db/models/workflows.py, backend/app/services/__init__.py, backend/app/services/workflow/default_routines.py
`backend/tests/test_dispatcher_outcome.py` (python, 122 loc) — Tests del detector estructurado de fallo de dispatchers (_outcome.detect_failure)…
  symbols: class _AIMsg {__init__}; def _msgs(tool); def test_empty_text_is_failure(); def test_error_prefix_is_failure(); def test_fail_phrase_is_failure(); def test_tool_refusal_is_failure(); def test_action_intent_without_tool_is_failure(); def test_action_intent_with_tool_is_success(); def test_query_intent_without_tool_is_success(); def test_not_found_is_query_ok_but_action_fails(); def test_normal_success(); def test_tool_was_invoked() … (+6)
  imports: app
  → usa: backend/app/agents/orchestrator/dispatchers/_outcome.py
`backend/tests/test_documents_agent.py` (python, 74 loc) — Smoke tests for the documents agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_documents_tools_registered(); async def test_documents_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_e2e_accounting.py` (python, 104 loc) — E2E Contabilidad — flujo asiento → libro diario → cuentas anuales (Balance + P&G)…
  symbols: def _balance(lines); class TestContabilidadE2E {test_flujo_asiento_a_cuentas_anuales, test_asiento_descuadrado_se_rechaza}
  imports: datetime, httpx, pytest
`backend/tests/test_e2e_agent_flows.py` (python, 244 loc) — E2E con grafo de agente real + LLM mockeado…
  symbols: def _mock_llm_with_responses(responses); class TestHRAgentE2E {test_list_employees_flow}; class TestBillingAgentE2E {test_list_invoices_flow}; class TestBankingAgentE2E {test_check_balances_flow}
  imports: __future__, langchain_core, pytest, sqlalchemy, unittest, uuid
`backend/tests/test_e2e_banking.py` (python, 122 loc) — E2E Banca — flujo importar N43 → listar/resumen → conciliar movimiento ↔ factura…
  symbols: def _line(code, body); def _mov22(fecha, dh, cents, doc); def _build_n43(movs, saldo_inicial_cents); class TestBancaE2E {test_import_n43_y_conciliacion}
  imports: datetime, httpx, io, pytest
`backend/tests/test_e2e_crm.py` (python, 64 loc) — E2E CRM — flujo cliente → oportunidad → avance en el embudo → actividad…
  symbols: class TestCrmE2E {test_cliente_oportunidad_actividad}
  imports: httpx, pytest
`backend/tests/test_e2e_happy_path.py` (python, 160 loc) — E2E Happy Path — flujos completos multi-endpoint…
  symbols: class TestAuthHappyPath {test_register_login_use_refresh}; class TestInvoiceLifecycle {test_full_invoice_lifecycle}; class TestHROnboarding {test_employee_onboarding_and_first_payroll}
  imports: datetime, httpx, pytest
`backend/tests/test_e2e_inventory.py` (python, 56 loc) — E2E Inventario — producto → entrada por lote (con caducidad) → salida bajo mínimo → reposición…
  symbols: class TestInventarioE2E {test_producto_lote_salida_reorder}
  imports: httpx, pytest
`backend/tests/test_e2e_marketing_happy.py` (python, 77 loc) — E2E Marketing — happy path: crear post → publicar OK → queda 'published'…
  symbols: class _FakePublisher {publish_post}; class TestMarketingPublishHappyPath {test_crear_y_publicar_ok}
  imports: app, datetime, httpx, pytest, sqlalchemy
  → usa: backend/app/db/models/marketing.py, backend/app/services/marketing/publisher_base.py
`backend/tests/test_e2e_marketing_publish.py` (python, 51 loc) — E2E Marketing — una publicación que FALLA debe devolver error, no 200…
  symbols: class TestMarketingPublishFalla {test_publish_sin_token_devuelve_error_no_200}
  imports: app, httpx, pytest, sqlalchemy
  → usa: backend/app/db/models/marketing.py
`backend/tests/test_e2e_onboarding.py` (python, 58 loc) — E2E Onboarding — wizard de alta → simulación del Modelo 303 → verificación REGAP (mock)…
  symbols: class TestOnboardingE2E {test_wizard_simulacion303_regap}
  imports: httpx, pytest
`backend/tests/test_e2e_treasury_sepa.py` (python, 94 loc) — E2E Tesorería + SEPA — cashflow → remesa de adeudos (pain.008) y transferencias (pain.001)…
  symbols: class TestTesoreriaSepaE2E {test_cashflow_y_remesas_sepa}
  imports: datetime, httpx, pytest, xml
`backend/tests/test_e2e_verifactu.py` (python, 124 loc) — E2E Veri*factu — flujo de usuario real (simulación local, sin AEAT)…
  symbols: async def _enable_voluntary(db); async def _emit_invoice(ac, client_id); async def _records(db); class TestVerifactuFlujoReal {test_emision_api_genera_huella_verificable, test_cadena_enlaza_dos_facturas, test_no_remission_no_crea_cadena}
  imports: app, datetime, httpx, pytest, sqlalchemy
  → usa: backend/app/db/models/auth.py, backend/app/db/models/billing.py, backend/app/services/billing/verifactu_mode.py
`backend/tests/test_email_attachment_ids_schema.py` (python, 61 loc) — send_email.attachment_ids must accept either a list[str] or a single string ID…
  symbols: class TestSendEmailAttachmentIdsAcceptsBothShapes {test_args_schema_accepts_list, test_args_schema_accepts_single_string, test_args_schema_accepts_none}
  imports: __future__, app
  → usa: backend/app/agents/email/tools.py
`backend/tests/test_email_campaign_worker.py` (python, 164 loc) — Campañas de email: envío por servicio, worker de programadas y opt-in RGPD
  symbols: def _patched_session(db); async def _make_campaign(db, tenant_id); async def test_send_campaign_envia_y_marca(db, seed_tenant_and_user); async def test_send_campaign_marca_fallos(db, seed_tenant_and_user); async def test_send_campaign_sin_credenciales_cuenta_fallos(db, seed_tenant_and_user); async def test_worker_envia_solo_vencidas(db, seed_tenant_and_user); async def test_campaign_solo_clientes_con_consentimiento(db, auth_client, seed_tenant_and_user)
  imports: app, contextlib, datetime, pytest, sqlalchemy, unittest
  → usa: backend/app/db/models/crm.py, backend/app/db/models/email_marketing.py
`backend/tests/test_email_reply_markread.py` (python, 58 loc) — Tools reply_email_real y mark_read_real del agente email (Gmail/Outlook)
  symbols: def _tools(providers); async def test_reply_sin_confirm_devuelve_borrador(); async def test_reply_confirm_llama_cliente_gmail(); async def test_mark_read_outlook(); async def test_imap_no_soporta_reply_ni_markread(); def test_build_tools_list_incluye_extra_solo_en_real()
  imports: app, pytest, unittest
  → usa: backend/app/agents/email/_provider_tools.py, backend/app/agents/email/tools.py
`backend/tests/test_employee_contract.py` (python, 65 loc) — Tests del validador del contrato AIEmployee (≥2 de 4 capacidades)
  symbols: def test_count_capabilities(kwargs, expected_count); def test_empty_containers_count_as_absent(); def test_scope_only_with_falsy_values_does_not_count(); def test_contract_fails_below_minimum(); def test_contract_passes_at_minimum(); def test_minimum_constant_is_two()
  imports: app, pytest
  → usa: backend/app/services/ai/employee_contract.py
`backend/tests/test_encryption.py` (python, 47 loc) — Tests para app.services.encryption
  symbols: class TestEncryption {test_encrypt_and_decrypt_roundtrip, test_encrypted_string_is_not_plaintext, test_different_encryptions_differ, test_empty_dict, test_complex_nested_data, test_invalid_token_raises, test_unicode_values}
  imports: app, pytest
  → usa: backend/app/services/encryption.py
`backend/tests/test_erp_import.py` (python, 79 loc) — Tests del servicio erp_import: Excel/CSV → entidades del ERP (preview + commit)
  symbols: async def _make_doc(db, tenant_id, csv_text, name); async def test_preview_detects_products_and_counts(db, seed_tenant_and_user); async def test_apply_creates_products_with_coerced_numbers(db, seed_tenant_and_user); async def test_apply_clients_target_override(db, seed_tenant_and_user); async def test_preview_missing_document_raises(db, seed_tenant_and_user)
  imports: app, os, pytest, sqlalchemy, tempfile, uuid
  → usa: backend/app/db/models/crm.py, backend/app/db/models/inventory.py, backend/app/db/models/tenant.py, backend/app/services/documents/erp_import.py
`backend/tests/test_excel_agent.py` (python, 75 loc) — Smoke tests for the excel agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_excel_tools_registered(); async def test_excel_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_execution_context.py` (python, 271 loc) — Tests para app.services.execution_context…
  symbols: def _state_with_result(output, agent, success); def test_extracts_structured_keys_into_entities_and_keydata(); def test_extracts_from_nested_extracted_data(); def test_response_preview_uses_larger_cap_than_400(); def test_response_preview_truncates_beyond_cap(); def test_truncate_helper_short_text_unchanged(); def test_build_enriched_intent_includes_response_when_no_keydata(); def test_markdown_parser_extracts_invoice_and_client(); def test_markdown_parser_handles_bold(); def test_markdown_parser_extracts_uuid_as_document_id(); def test_markdown_parser_empty_text_returns_empty(); def test_markdown_parser_does_not_override_structured_entities() … (+8)
  imports: app
  → usa: backend/app/services/__init__.py, backend/app/services/execution_context.py
`backend/tests/test_expiry_alert.py` (python, 24 loc) — Tests de la clasificación pura de caducidad de lotes (sin base de datos)
  symbols: def test_already_expired_is_error(); def test_expires_today_is_warning(); def test_expires_soon_is_warning_with_days_left()
  imports: app, datetime
  → usa: backend/app/services/alerts/_expiry.py
`backend/tests/test_financial_caps.py` (python, 249 loc) — Caps de aprobación en tools de escritura financiera (#8 consejo 2026-06-02)…
  symbols: async def _seed_tenant(); def _balanced_lines(amount); async def _count_journal_entries(tenant_id); async def test_journal_entry_over_threshold_blocked(); async def test_journal_entry_under_threshold_created(); async def _seed_payroll(tenant_id, net, status); async def _payroll_status(payroll_id); async def test_approve_payroll_over_threshold_blocked(); async def test_approve_payroll_under_threshold_ok(); async def _pending_for_task(task_id); async def test_cap_creates_structured_approval(); async def test_execute_approved_journal_creates_entry() … (+3)
  imports: app, datetime, decimal, sqlalchemy, uuid
  → usa: backend/app/agents/accounting/tools.py, backend/app/agents/hr/_payroll_crud.py, backend/app/agents/shared/validators/billing.py, backend/app/core/tenant_context.py, backend/app/db/base.py, backend/app/db/models/accounting.py, backend/app/db/models/hr.py, backend/app/db/models/models.py, backend/app/services/workflow/__init__.py, backend/app/services/workflow/approval_actions.py
`backend/tests/test_fiscal_approval.py` (python, 277 loc) — Tests para SEC.APR — MANDATORY_HUMAN_FISCAL + FiscalApprovalLog
  symbols: async def _seed_task(db, tenant_id); class TestComputePayloadHash {test_hash_determinista, test_cambio_payload_cambia_hash}; class TestRequestFiscalApproval {test_crea_pending_approval_con_risk_level}; class TestApproveFiscal {test_aprobacion_correcta_crea_log, test_texto_incorrecto_lanza_value_error, test_texto_sin_acentos_es_aceptado, test_aprobacion_doble_falla}; class TestRejectFiscal {test_rechazo_crea_log_y_marca_pending}; class TestHasValidFiscalApproval {test_aprobacion_misma_payload_es_valida, test_aprobacion_payload_distinto_no_es_valida, test_rechazo_no_cuenta_como_aprobacion}
  imports: app, pytest
  → usa: backend/app/db/models/tasks.py, backend/app/services/workflow/fiscal_approval.py
`backend/tests/test_fiscal_idempotency_dryrun.py` (python, 135 loc) — Regresión de los arreglos fiscales de 2026-06-24…
  symbols: async def _seed_client(db, tenant_id, name); def _invoice(tenant_id, client_id); async def _count_payment_entries(db, tenant_id, invoice_id); async def test_invoice_payment_entry_no_duplica(db, seed_tenant_and_user); async def test_auto_reconcile_genera_asiento_de_cobro(db, seed_tenant_and_user); class _FakePres {__init__}; def test_acuse_simulado_se_marca_sin_validez(); def test_acuse_aceptado_real_es_verificable()
  imports: app, datetime, decimal, pytest, sqlalchemy
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/models.py, backend/app/services/aeat/presentation_service.py, backend/app/services/banking/service.py, backend/app/services/billing/auto_accounting.py
`backend/tests/test_fiscal_lockdown.py` (python, 66 loc) — Blindaje fiscal: Verifactu/AEAT nunca se auto-presenta…
  symbols: async def test_fiscal_forced_manual_default(); async def test_set_policy_fiscal_auto_rejected(db, seed_tenant_and_user); async def test_fiscal_manual_even_with_persisted_row(db, seed_tenant_and_user); async def test_put_policy_fiscal_auto_rejected_via_api(auth_client); async def test_sede_real_submission_requires_confirmation(); async def test_submit_presentation_requires_confirmed_user(db, seed_tenant_and_user)
  imports: app, pytest, uuid
  → usa: backend/app/services/autonomy.py
`backend/tests/test_fiscal_n3_n4_n5.py` (python, 113 loc) — Regresión de la tanda fiscal N3/N4/N5 (auditoría 2026-06-25)…
  symbols: async def test_asiento_nomina_incluye_cuota_patronal_642(db, seed_tenant_and_user); async def test_modelo_130_resta_retenciones_soportadas(db, seed_tenant_and_user); def test_detalles_verifactu_resta_descuento_de_linea()
  imports: app, datetime, decimal, sqlalchemy, types
  → usa: backend/app/db/models/accounting.py, backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/services/aeat/casillas_130.py, backend/app/services/billing/auto_accounting.py, backend/app/services/billing/registro_facturacion.py, backend/app/services/reports/modelos_aeat.py
`backend/tests/test_fiscal_status_rectificativa.py` (python, 137 loc) — Regresión N1/N2 (auditoría 2026-06-25): los modelos AEAT excluyen las facturas anuladas, incluyen las rectificativas y mantienen los borrado…
  symbols: async def _add_invoice(db, tenant_id, client_id, number, inv_type, status, lines); async def _seed(); async def test_303_excluye_anuladas_minora_rectificativas_y_mantiene_borradores(); async def test_libro_emitidas_cuadra_con_el_303(); async def _seed_347(); async def test_modelo_347_minora_rectificativas()
  imports: app, csv, datetime, decimal, io, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/aeat/casillas_303.py, backend/app/services/reports/fiscal.py, backend/app/services/reports/modelos_aeat.py
`backend/tests/test_generate_sbom.py` (python, 160 loc) — Tests del generador SBOM (DIS.SBOM)
  symbols: class TestBuildSbom {test_estructura_cyclonedx, test_metadata_incluye_version_y_supplier, test_incluye_componentes_de_distintas_fuentes, test_componentes_tienen_purl_o_hash, test_components_no_vacio}; class TestParsers {test_parse_requirements_strip_comments, test_parse_package_json, test_parse_package_json_marca_devdep_como_optional, test_parse_embedded, test_parse_embedded_sin_hash_omite_hashes, test_parse_archivos_inexistentes_devuelven_lista_vacia}; class TestEmbeddedManifest {test_manifest_existe, test_manifest_es_json_valido, test_cada_binario_tiene_campos_minimos}
  imports: generate_sbom, json, pathlib, sys
  → usa: scripts/generate_sbom.py
`backend/tests/test_google_oauth_pkce.py` (python, 119 loc) — PKCE (S256) en el flujo OAuth de Google — regresión…
  symbols: def test_generate_auth_url_emits_s256_challenge(); def test_two_calls_produce_distinct_verifiers(); async def test_exchange_code_forwards_verifier(monkeypatch); def test_state_store_roundtrips_verifier(); async def test_duplicate_callback_is_idempotent(monkeypatch)
  imports: app, base64, hashlib, pytest, urllib
  → usa: backend/app/integrations/__init__.py, backend/app/services/integration/__init__.py
`backend/tests/test_health_checks.py` (python, 110 loc) — Tests de los health checks adicionales (redis, scheduler, last_backup)
  symbols: async def test_check_redis_disabled_when_no_url(monkeypatch); async def test_check_redis_up_with_fake_client(monkeypatch); async def test_check_redis_down_when_ping_fails(monkeypatch); def test_check_scheduler_reports_running_jobs(); def test_check_scheduler_down_when_not_running(); def test_check_last_backup_disabled(monkeypatch); def test_check_last_backup_never_when_dir_empty(monkeypatch, tmp_path); def test_check_last_backup_returns_metadata_of_latest(monkeypatch, tmp_path)
  imports: app, importlib, os, pytest, time, unittest
  → usa: backend/app/services/__init__.py
`backend/tests/test_holded_client.py` (python, 207 loc) — Tests del cliente HTTP paginado Holded (MIG.2)
  symbols: def _resp(status, json_data, headers); def _client_mock(); def _creds(); class TestGetPage {test_pasa_api_key_en_header, test_401_lanza_auth_error_sin_credencial_en_msg, test_429_lanza_rate_limit_con_retry_after, test_otros_status_lanzan_holded_error, test_acepta_payload_lista_plana, test_acepta_payload_dict_items}; class TestPagination {test_para_cuando_pagina_vacia, test_para_cuando_pagina_parcial, test_respeta_max_pages, test_fetch_all_aplana}; class TestEndpoints {test_iter_contacts_apunta_a_contacts, test_iter_invoices_apunta_a_documents_invoice}; class TestRateLimitRetry {test_back_off_y_reintento_tras_429, test_se_rinde_tras_3_rate_limits_consecutivos}
  imports: app, pytest, unittest
  → usa: backend/app/services/migration/__init__.py, backend/app/services/migration/holded_importer.py
`backend/tests/test_hr_document_numbering.py` (python, 57 loc) — Tests para el folio correlativo de documentos de gestoría (2.8)
  symbols: def _doc(tenant_id, status); class TestHRDocNumbering {test_approve_assigns_correlative_folio, test_reapprove_keeps_same_number, test_numbering_is_per_tenant}
  imports: app, datetime, pytest, uuid
  → usa: backend/app/db/models/hr_documents.py, backend/app/services/hr/commands.py
`backend/tests/test_hr_schedule_propose_export.py` (python, 128 loc) — Tool `propose_schedule` (gate hr) y export de horarios a Excel/PDF
  symbols: def _patched_sessions(db); async def _seed_employee(db, tenant_id, name); def _days(); async def test_propose_schedule_auto_aplica(db, seed_tenant_and_user); async def test_propose_schedule_confirm_por_defecto_no_aplica(db, seed_tenant_and_user); async def test_propose_schedule_validaciones(db, seed_tenant_and_user); async def test_export_schedules_endpoint(db, auth_client, seed_tenant_and_user)
  imports: app, contextlib, pytest, sqlalchemy, unittest, uuid
  → usa: backend/app/agents/hr/_schedule_tools.py, backend/app/db/models/hr.py, backend/app/db/models/models.py, backend/app/services/autonomy.py
`backend/tests/test_i18n_pdf_strings.py` (python, 105 loc) — Tests de internacionalización de strings PDF (I18N.PDF)
  symbols: class TestGetLocaleOrDefault {test_none_devuelve_default, test_string_vacio_devuelve_default, test_locale_soportado, test_locale_con_region, test_locale_uppercase, test_no_soportado_fallback_default}; class TestTranslate {test_existe_en_es, test_existe_en_en, test_stub_ca_tiene_prefijo, test_stub_eu_tiene_prefijo, test_stub_gl_tiene_prefijo, test_key_inexistente_devuelve_missing, test_locale_none_usa_default, test_locale_invalido_usa_default}; class TestCoverage {test_es_es_la_fuente_completa, test_en_cubre_todas_las_keys, test_stubs_cubren_todas_las_keys}
  imports: app
  → usa: backend/app/i18n/__init__.py, backend/app/i18n/pdf_strings.py
`backend/tests/test_i18n_tenant_locale.py` (python, 84 loc) — Tests del resolver de locale por tenant (I18N.PDF wiring)
  symbols: async def test_get_tenant_locale_devuelve_default(db, seed_tenant_and_user); async def test_get_tenant_locale_tenant_inexistente_devuelve_default(db); class TestResolveLocale {test_explicit_gana, test_cookie_si_no_hay_explicit, test_accept_language_si_no_cookie, test_accept_language_primer_soportado, test_accept_language_solo_no_soportado, test_tenant_default, test_sin_inputs_devuelve_es, test_explicit_invalido_cae_al_siguiente}; def test_invoice_lines_table_acepta_locale()
  imports: app, pytest, uuid
  → usa: backend/app/services/i18n/tenant_locale.py
`backend/tests/test_idempotency.py` (python, 218 loc) — Tests de idempotencia de tools críticas (QA.IDM)…
  symbols: def _invoice(tenant_id, client_id); class TestVerifactuIdempotency {_seed, test_doble_append_no_duplica, test_cadena_intacta_tras_reintento, test_reintento_con_nif_distinto_no_corrompe, test_payload_y_huella_son_inmutables}; class TestNumberingNonIdempotent {test_dos_llamadas_consecutivas_dan_numeros_distintos, test_aislamiento_entre_tenants}; class TestCombinedFlowIdempotency {test_reintento_completo_secuencia}
  imports: app, datetime, decimal, pytest, sqlalchemy
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/billing/numbering.py, backend/app/services/billing/verifactu_chain.py
`backend/tests/test_idempotency_guard.py` (python, 85 loc) — IdempotencyGuard persistente en DB — sobrevive 'reinicios' (memoria limpia)
  symbols: def _clean_memory(); def _patched(db); async def test_mark_executed_persiste_y_sobrevive_reinicio(db); async def test_release_borra_la_clave(db); async def test_clave_expirada_no_cuenta(db); async def test_fallback_a_memoria_si_db_falla()
  imports: app, contextlib, datetime, pytest, sqlalchemy, unittest
  → usa: backend/app/services/idempotency.py, backend/app/db/models/__init__.py
`backend/tests/test_inventory_agent.py` (python, 177 loc) — Tests del agente de stock: estructura del grafo, registro de tools y validación de entrada de las tools de escritura (ramas previas a la BD)…
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_core_tools_registered(); def test_tools_have_descriptions(); async def test_adjust_rejects_invalid_op(); async def test_adjust_rejects_bad_json(); async def test_adjust_rejects_empty_list(); async def test_update_rejects_bad_tenant(); def test_format_adjust_preview_shows_confirm_hint(); def _decision(mode); async def test_confirm_mode_queues_approval_not_apply(); async def test_manual_mode_only_suggests() … (+1)
  imports: pytest, unittest
`backend/tests/test_inventory_bajas_analytics.py` (python, 144 loc) — Tests de analítica de bajas/mermas y stock bajo mínimo (BD SQLite de test)…
  symbols: async def _add_product(db, tenant_id); async def _add_movement(db, tenant_id, product_id); async def test_bajas_by_reason_and_value(db, seed_tenant_and_user); async def test_bajas_excludes_old_movements(db, seed_tenant_and_user); async def test_box_bajas_reported_separately(db, seed_tenant_and_user); async def test_below_min(db, seed_tenant_and_user); async def test_top_movers_excludes_writeoffs_and_boxes(db, seed_tenant_and_user)
  imports: app, datetime, pytest
  → usa: backend/app/db/models/inventory.py, backend/app/services/inventory/__init__.py
`backend/tests/test_inventory_batch_service.py` (python, 180 loc) — Tests del servicio batch de inventario (con BD SQLite de test)…
  symbols: async def _add_product(db, tenant_id); async def test_resolve_by_sku_and_name(db, seed_tenant_and_user); async def test_resolve_ambiguous_name_returns_none(db, seed_tenant_and_user); async def test_adjust_set_preview_does_not_persist(db, seed_tenant_and_user); async def test_adjust_set_apply_persists_and_logs_movement(db, seed_tenant_and_user); async def test_entrada_logs_magnitude_not_total(db, seed_tenant_and_user); async def test_adjust_remove_below_zero_is_skipped(db, seed_tenant_and_user); async def test_adjust_unknown_ref_is_skipped(db, seed_tenant_and_user); async def test_update_fields_preview_then_apply(db, seed_tenant_and_user); async def test_update_rejects_unknown_field(db, seed_tenant_and_user); async def test_update_rejects_negative_price(db, seed_tenant_and_user)
  imports: app, pytest, sqlalchemy
  → usa: backend/app/db/models/inventory.py, backend/app/services/inventory/__init__.py
`backend/tests/test_inventory_fefo.py` (python, 91 loc) — Tests de la lógica pura FEFO (sin base de datos)
  symbols: class FakeLot; def _dt(y, m, d); def test_deducts_from_earliest_expiry_first(); def test_spans_multiple_lots_in_fefo_order(); def test_lots_without_expiry_go_last(); def test_tie_on_expiry_uses_earliest_received(); def test_reports_shortage_when_insufficient(); def test_skips_empty_lots(); def test_non_positive_quantity_is_noop()
  imports: app, dataclasses, datetime
  → usa: backend/app/services/inventory/_fefo.py
`backend/tests/test_invoice_amount_parse.py` (python, 57 loc) — Tests del parseo de importes de factura (formato español)…
  symbols: def test_formato_ingles_simple(); def test_formato_espanol_miles_y_decimales(); def test_formato_espanol_solo_decimales(); def test_formato_espanol_millones(); def test_miles_sin_decimales(); def test_entero_simple(); def test_con_espacios(); def test_no_numerico_devuelve_error_y_cero(); def test_vacio_devuelve_error()
  imports: app, decimal
  → usa: backend/app/agents/billing/_invoice_validators.py
`backend/tests/test_invoice_import.py` (python, 115 loc) — Tests del servicio invoice_import: factura de compra + asiento + stock seguro
  symbols: def _draft(apply_stock, line_desc, qty, unit); async def test_import_creates_received_invoice_and_journal_entry(db, seed_tenant_and_user); async def test_import_applies_stock_for_matched_product(db, seed_tenant_and_user); async def test_import_unmatched_line_does_not_touch_stock(db, seed_tenant_and_user); async def test_import_without_apply_stock_skips_inventory(db, seed_tenant_and_user)
  imports: app, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/inventory.py, backend/app/db/models/models.py, backend/app/services/billing/invoice_import.py
`backend/tests/test_invoice_import_dedup.py` (python, 107 loc) — Idempotencia del import de facturas recibidas (anti-duplicado)…
  symbols: async def _seed_tenant(db); def _draft(numero); async def _count_received(db, tenant_id); class TestImportDedup {test_primera_importacion_crea, test_reimportar_mismo_no_duplica, test_distinto_numero_si_crea_segunda, test_borrar_recibida_con_asiento_no_falla, test_mismo_numero_distinto_proveedor_si_crea}
  imports: app, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/models.py, backend/app/services/billing/invoice.py, backend/app/services/billing/invoice_import.py
`backend/tests/test_invoice_migration_import.py` (python, 88 loc) — Migración de facturas históricas (import masivo desde otro programa)…
  symbols: async def _seed(db); def _row(numero); async def _count(db, tenant_id); class TestInvoiceMigration {test_importa_preserva_numero_e_importes, test_idempotente_emitida, test_total_derivado_de_base_mas_iva, test_cliente_inexistente_error, test_falta_numero_error}
  imports: app, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/models.py, backend/app/services/migration/bulk_import.py
`backend/tests/test_invoice_numbering.py` (python, 71 loc) — Tests para `next_invoice_number` — numeración correlativa (FAC.NUM)
  symbols: class TestNextInvoiceNumber {test_primera_factura_emite_0001, test_correlativa_sin_gaps, test_series_distintas_son_independientes, test_anos_distintos_son_independientes, test_tenants_distintos_son_independientes, test_no_emite_uuid}
  imports: app, pytest, uuid
  → usa: backend/app/services/billing/numbering.py
`backend/tests/test_invoice_totals.py` (python, 108 loc) — Tests del cálculo de importes de factura (compute_invoice_totals)…
  symbols: def test_linea_simple(); def test_descuento(); def test_multilinea_iva_mixto(); def test_redondeo_decimal_no_float(); def test_iva_invalido_lanza(); def test_total_negativo_lanza(); def test_lineas_vacias(); def test_total_por_linea_presente_y_redondeado(); def test_iva_por_defecto_21(); def test_total_negativo_permitido_con_flag(); def test_negativo_sigue_validando_iva(); def test_rectificativa_anula_factura_a_cero()
  imports: app, pytest
  → usa: backend/app/services/billing/queries.py
`backend/tests/test_langfuse_callback.py` (python, 65 loc) — Tests del helper get_langfuse_callback()…
  symbols: def test_returns_none_when_keys_empty(monkeypatch); def test_returns_none_when_only_one_key(monkeypatch); def test_returns_none_when_package_missing(monkeypatch); def test_returns_handler_when_keys_and_package_present(monkeypatch)
  imports: app, importlib, pytest
  → usa: backend/app/core/__init__.py
`backend/tests/test_license_enforcement.py` (python, 65 loc) — Tests de endurecimiento de licencia: middleware fail-closed + sin bypass
  symbols: def _mk_app(); class TestMiddlewareFailClosed {test_protected_blocked_when_flag_unset, test_health_always_allowed, test_protected_allowed_when_valid}; class TestNoBypass {test_no_license_is_invalid}; class TestPeriodicRevalidation {test_refresh_updates_app_state}
  imports: app, pytest, starlette
  → usa: backend/app/core/__init__.py, backend/app/core/license.py, backend/app/middleware/license_check.py
`backend/tests/test_llm_callbacks.py` (python, 129 loc) — Unit tests for UsageTrackingCallback and token extraction logic
  symbols: def clean(); def test_detects_anthropic_from_serialized(); def test_detects_openai_from_serialized(); def test_detects_groq_from_serialized(); def test_detects_via_id_list(); def _make_result_with_token_usage(prompt_tokens, completion_tokens); def _make_result_with_usage_metadata(input_tokens, output_tokens); def _make_result_with_anthropic_usage(input_tokens, output_tokens); def test_extract_tokens_from_token_usage(); def test_extract_tokens_from_usage_metadata(); def test_extract_tokens_from_anthropic_usage(); def test_extract_tokens_returns_zero_on_empty() … (+3)
  imports: app, langchain_core, pytest, unittest
  → usa: backend/app/core/llm_callbacks.py, backend/app/services/__init__.py
`backend/tests/test_llm_factory.py` (python, 91 loc) — Tests para app.core.llm_factory — Fábrica centralizada de LLMs
  symbols: def clear_api_keys(monkeypatch); class TestGetLlm {test_returns_mock_in_testing_without_keys, test_explicit_mock_provider, test_unknown_provider_returns_mock, test_temperature_parameter_accepted, test_groq_without_key_returns_mock, test_anthropic_without_key_returns_mock, test_openai_without_key_returns_mock, test_openrouter_without_key_returns_mock}; class TestGetLlmWithFallback {test_delegates_to_get_llm, test_accepts_temperature}; class TestTenantLlmContext {test_set_and_get_context, test_explicit_provider_ignores_context, test_context_default_is_none}
  imports: app, pytest
  → usa: backend/app/core/__init__.py, backend/app/core/llm_factory.py
`backend/tests/test_llm_factory_caching.py` (python, 116 loc) — Unit tests for make_cached_system_message and _resolve_active_provider
  symbols: def reset_ctx(); def test_resolve_returns_anthropic_for_anthropic_module(); def test_resolve_returns_other_for_openai_module(); def test_resolve_returns_other_for_groq_module(); def test_resolve_falls_back_to_settings_when_no_ctx(monkeypatch); def test_resolve_falls_back_to_settings_anthropic(monkeypatch); def test_cached_message_with_anthropic_provider(); def test_cached_message_with_openai_provider(); def test_cached_message_no_ctx_openai_default(monkeypatch); def test_cached_message_no_ctx_anthropic_default(monkeypatch); def test_cached_message_preserves_full_text()
  imports: app, langchain_core, pytest, unittest
  → usa: backend/app/core/llm_factory.py
`backend/tests/test_llm_mock.py` (python, 207 loc) — Tests para app.core.llm.mock — MockChatModel para testing
  symbols: class TestMockChatModelBasics {test_llm_type, test_generate_returns_chat_result, test_agenerate_returns_chat_result, test_invoke_returns_ai_message, test_ainvoke_returns_ai_message}; class TestMockChatModelFallback {test_fallback_generic_response, test_tool_message_triggers_completion}; class TestMockChatModelDomainDetection {test_coordinator_plan, test_billing_extraction, test_billing_query_detection, test_compliance_alerts, test_compliance_boe, test_compliance_fiscal_query}; class TestMockChatModelClassifyDomain {test_classify_hr, test_classify_billing, test_classify_crm, test_classify_compliance, test_classify_documents, test_classify_email, test_classify_banking, test_classify_fallback}; class TestMockChatModelMultiAgentPlan {test_hr_plan, test_billing_plan, test_compliance_plan, test_fallback_plan}; class TestMockChatModelBindTools {test_bind_tools_returns_runnable, test_with_structured_output_returns_runnable}; class TestMockChatModelExtractTenantId {test_extracts_uuid_from_message, test_returns_default_when_no_uuid}
  imports: app, json, langchain_core, pytest
  → usa: backend/app/core/__init__.py
`backend/tests/test_llm_usage_tracker.py` (python, 100 loc) — Unit tests for llm_usage_tracker — no DB, no fixtures needed
  symbols: def clean_tracker(); def test_record_increments_calls(clean_tracker); def test_record_accumulates_multiple_calls(clean_tracker); def test_record_multiple_agents(clean_tracker); def test_estimate_cost_anthropic(); def test_estimate_cost_openai(); def test_estimate_cost_zero_for_mock(); def test_estimate_cost_in_stats(clean_tracker); def test_get_monthly_stats_empty(clean_tracker); def test_flush_removes_data(clean_tracker); def test_zero_tokens_not_recorded(clean_tracker); def test_by_agent_sorted_by_tokens(clean_tracker) … (+1)
  imports: app, pytest
  → usa: backend/app/services/__init__.py
`backend/tests/test_marketing_agent.py` (python, 71 loc) — Smoke tests for the marketing agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_marketing_tools_registered(); async def test_marketing_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_marketing_create_campaign.py` (python, 121 loc) — Tool `create_campaign` del agente marketing: gate + programación de posts
  symbols: def _patched_sessions(db); async def _seed_account(db, tenant_id); def _posts(account_id); async def test_auto_programa_campania_y_posts(db, seed_tenant_and_user); async def test_confirm_por_defecto_no_programa(db, seed_tenant_and_user); async def test_valida_campos_y_cuentas(db, seed_tenant_and_user)
  imports: app, contextlib, pytest, sqlalchemy, unittest
  → usa: backend/app/agents/marketing/tools.py, backend/app/db/models/marketing.py, backend/app/services/autonomy.py
`backend/tests/test_marketing_metrics.py` (python, 124 loc) — Tests para la analítica de marketing — scheduled_post_metrics (5.1)
  symbols: def _social_account(tenant_id, platform); def _post(tenant_id, account_id, campaign_id, status); class TestMarketingMetrics {test_upsert_is_idempotent_per_day, test_get_campaign_metrics_aggregates_latest, test_endpoint_unknown_campaign_404, test_endpoint_returns_totals}
  imports: datetime, httpx, pytest, sqlalchemy, uuid
`backend/tests/test_marketing_publish.py` (python, 58 loc) — Tests de la política de reintentos del scheduler (transitorio/permanente, backoff)…
  symbols: class TestHandlePublishResult {_post, test_published, test_transient_reschedules_with_backoff, test_backoff_doubles, test_retries_exhausted_fails, test_permanent_fails_without_retry}
  imports: app, datetime, types
  → usa: backend/app/services/marketing/publisher_base.py, backend/app/workers/__init__.py
`backend/tests/test_memory_tools.py` (python, 267 loc) — Tests de las tools `remember` / `recall` / `recall_all` del AIEmployee (F1.2)…
  symbols: async def _seed_employee(db, tenant); async def test_remember_falla_si_memory_disabled(db, seed_tenant_and_user); async def test_recall_falla_si_memory_disabled(db, seed_tenant_and_user); async def test_remember_recall_roundtrip_string(db, seed_tenant_and_user); async def test_remember_recall_roundtrip_json_object(db, seed_tenant_and_user); async def test_recall_not_found_devuelve_marker(db, seed_tenant_and_user); async def test_recall_all_devuelve_ordenado(db, seed_tenant_and_user); async def test_remember_upsert_no_duplica(db, seed_tenant_and_user); async def test_remember_rechaza_uuid_invalido(db, seed_tenant_and_user); async def test_remember_rechaza_key_vacia(db, seed_tenant_and_user); async def test_remember_rechaza_key_demasiado_larga(db, seed_tenant_and_user); async def test_remember_empleado_inexistente(db, seed_tenant_and_user)
  imports: app, json, pytest, uuid
  → usa: backend/app/db/models/ai_employees.py
`backend/tests/test_metering.py` (python, 177 loc) — Tests para metered billing (OPS.OVR + OPS.CRON)
  symbols: class TestComputeCronCap {test_pro_es_200_flat, test_gestoria_escala_por_empresas, test_gestoria_topa_a_2000, test_solo_no_tiene_cron, test_constantes_consensuadas}; class TestRecordInteraction {test_primera_interaccion_pro_count_1, test_warning_a_partir_de_450, test_overage_a_500, test_cobro_overage_por_extra, test_hard_cap_a_1000_extras, test_gestoria_sin_cap}; class TestRecordCronExecution {test_pro_incrementa_hasta_cap, test_pro_rechaza_si_ya_en_cap, test_gestoria_escala_con_empresas}
  imports: app, decimal, pytest
  → usa: backend/app/services/billing/metering.py
`backend/tests/test_metrics_time_saved.py` (python, 44 loc) — Métrica de tiempo ahorrado: cálculo desde AuditLog y endpoint
  symbols: async def test_time_saved_cuenta_solo_success(db, seed_tenant_and_user); async def test_time_saved_excluye_fontaneria(db, seed_tenant_and_user); async def test_endpoint_time_saved(auth_client)
  imports: app, pytest
  → usa: backend/app/services/audit.py, backend/app/services/metrics/time_saved.py
`backend/tests/test_migration.py` (python, 175 loc) — Tests para importadores MIG.1 (CSV) + MIG.2 (Holded) + MIG.3 (wizard)
  symbols: class TestCsvImporter {test_detect_separator_coma, test_detect_separator_punto_coma, test_parse_decimal_formato_es, test_parse_decimal_formato_us, test_parse_decimal_solo_coma, test_parse_decimal_invalido, test_parse_decimal_vacio, test_parse_csv_clientes_basico}; class TestHoldedNormalizers {test_normalize_contact_basico, test_normalize_contact_sin_nif_marca_error_si_tampoco_nombre, test_normalize_invoice_centimos_a_euros, test_normalize_invoice_sin_docnumber_marca_error}; class TestImportClients {test_insert_clientes_nuevos, test_upsert_actualiza_existente, test_filas_con_errores_se_skipean}
  imports: app, datetime, decimal, pytest
  → usa: backend/app/services/migration/csv_importer.py, backend/app/services/migration/holded_importer.py, backend/app/services/migration/wizard.py
`backend/tests/test_migrations.py` (python, 143 loc) — Tests para verificar integridad de migraciones Alembic…
  symbols: class TestAlembicMigrations {test_alembic_check_no_pending, test_migration_history_has_single_head}; class TestMigrationFiles {_migration_files, test_hay_al_menos_una_migracion, test_cada_migracion_define_upgrade_y_downgrade, test_cada_migracion_declara_revision_y_down_revision, test_revisions_son_unicas, test_downgrade_no_es_pass_vacio}
  imports: pytest, subprocess, sys
`backend/tests/test_modelo_100.py` (python, 71 loc) — Tests del Modelo 100 (IRPF Renta, preview) — datos + escala + PDF
  symbols: def test_irpf_cuota_escala_progresiva(); async def test_build_modelo_100_preview(db, seed_tenant_and_user); async def test_build_modelo_100_sin_actividad(db, seed_tenant_and_user); def test_modelo_100_pdf_renders()
  imports: app, datetime, decimal, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/pdf_reports/__init__.py, backend/app/services/reports/modelos_aeat.py
`backend/tests/test_modelo_200.py` (python, 154 loc) — Tests del Modelo 200 — Impuesto sobre Sociedades (F2.8)
  symbols: def _inv(tenant_id, client_id); async def test_modelo_200_estructura_minima(db, seed_tenant_and_user); async def test_modelo_200_calculo_basico_sin_nominas(db, seed_tenant_and_user); async def test_modelo_200_aplica_tipo_general_cuando_cifra_supera_umbral(db, seed_tenant_and_user); async def test_modelo_200_resultado_negativo_da_cuota_cero(db, seed_tenant_and_user); async def test_modelo_200_descuenta_pagos_fraccionados(db, seed_tenant_and_user); async def test_modelo_200_acepta_tipo_impositivo_override(db, seed_tenant_and_user)
  imports: app, datetime, decimal, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/reports/modelos_aeat.py
`backend/tests/test_modelo_200_pdf.py` (python, 34 loc) — Test del PDF del Modelo 200 (Impuesto sobre Sociedades, preview)
  symbols: def _data(); def test_modelo_200_pdf_renders_valid_pdf(); def test_modelo_200_pdf_tolerates_missing_fields()
  imports: app
  → usa: backend/app/services/pdf_reports/__init__.py
`backend/tests/test_modelo_303.py` (python, 154 loc) — Tests deterministas del cálculo del Modelo 303 (liquidación trimestral IVA)…
  symbols: async def _add_invoice(db, tenant_id, client_id, number, inv_type, lines); async def _seed_quarter(); async def test_modelo_303_casillas_regimen_general(); async def test_modelo_303_empty_quarter_is_zero(); async def test_expediente_303_bundle(); def test_303_tipo_no_estandar_no_se_pierde_en_la_27(); def test_303_tipos_estandar_sin_nota_en_la_27()
  imports: app, datetime, decimal, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/services/aeat/__init__.py, backend/app/services/aeat/casillas_303.py, backend/app/services/reports/fiscal.py
`backend/tests/test_modelo_303_pdf.py` (python, 44 loc) — Tests del PDF oficial del Modelo 303 (casillas numeradas AEAT)
  symbols: def _data(); def test_modelo_303_pdf_renders_valid_pdf(); def test_modelo_303_pdf_with_recargo_and_intra(); def test_modelo_303_pdf_empty_quarter()
  imports: app
  → usa: backend/app/services/pdf_reports/__init__.py
`backend/tests/test_modelo_303_regimenes.py` (python, 223 loc) — Tests M1: regímenes especiales 303 (intra/ISP/recargo), retención Art.95 en el 111, 390 con autoliquidación y validación XSD pre-firma
  symbols: async def _mk_client(db, tenant_id, name, nif); async def _mk_invoice(db, tenant_id, client_id); def _casilla(casillas, codigo); class TestModelo303Regimenes {test_intracomunitario_casillas_10_11_36_37, test_isp_casillas_12_13_y_deducible_interior, test_recargo_equivalencia_casillas_22_24, test_regresion_sin_regimenes_casillas_nuevas_a_cero}; class TestModelo111Profesionales {test_retencion_profesional_art95, test_sin_retencion_no_aparece}; class TestModelo390Autoliquidacion {test_390_incluye_intra_e_isp}; class TestXsdValidation {test_xml_bien_formado_sin_xsd_pasa, test_xml_mal_formado_devuelve_error}
  imports: app, datetime, decimal, pytest, uuid
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/aeat/casillas_303.py, backend/app/services/aeat/xsd_validation.py, backend/app/services/reports/fiscal.py, backend/app/services/reports/modelos_aeat.py
`backend/tests/test_modelo_iva_breakdown.py` (python, 90 loc) — Tests del desglose de IVA por tipo (modelos 303 trimestral y 390 anual)…
  symbols: class _Line {__init__}; class _Invoice {__init__}; def _rate(m, r); def test_linea_simple(); def test_descuento(); def test_multitipo(); def test_decimal_sin_arrastre_float(); def test_iva_por_defecto_21_si_falta(); def test_tipo_cero_no_genera_cuota(); def test_303_y_390_usan_la_misma_logica(); def test_agrega_varias_facturas_por_tipo()
  imports: app, decimal
  → usa: backend/app/services/reports/fiscal.py
`backend/tests/test_modelos_aeat.py` (python, 190 loc) — Tests para los modelos AEAT 130, 347 y 390 (MOD.* sprint 4)
  symbols: def _make_invoice(tenant_id, client_id); def _make_line(); class TestModelo130 {test_pago_fraccionado_20_pct_del_beneficio, test_pago_fraccionado_no_negativo, test_quarter_invalido_raises}; class TestModelo347 {test_solo_se_declaran_los_que_superan_umbral, test_agrupa_emitidas_y_recibidas_por_nif}; class TestModelo390 {test_agrega_iva_anual_por_tipo, test_sin_facturas_devuelve_ceros}
  imports: app, datetime, decimal, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/reports/modelos_aeat.py
`backend/tests/test_modelos_aeat_retenciones.py` (python, 213 loc) — Tests para los Modelos AEAT 111 (trimestral) y 190 (anual) — MOD.111/MOD.190
  symbols: def _employee(tenant_id); def _payroll(tenant_id, employee_id); class TestModelo111 {test_suma_retenciones_trimestrales, test_solo_nominas_del_trimestre, test_agrupa_por_empleado, test_quarter_invalido_raises, test_sin_nominas_devuelve_vacio}; class TestModelo190 {test_consolida_anualmente, test_solo_nominas_del_year, test_incluye_clave_g_profesionales, test_factura_sin_retencion_no_genera_clave_g}
  imports: app, datetime, decimal, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/hr.py, backend/app/services/reports/modelos_aeat.py
`backend/tests/test_modelos_pdf.py` (python, 154 loc) — Tests de los generadores de PDF borrador de modelos AEAT…
  symbols: def _is_pdf(b); def test_modelo_130_pdf(); def test_modelo_111_pdf_con_perceptores(); def test_modelo_111_pdf_sin_perceptores(); def test_modelo_190_pdf(); def test_modelo_347_pdf(); def test_modelo_347_pdf_sin_declarables(); def test_modelo_390_pdf(); def test_modelo_115_pdf(); def test_modelo_349_pdf(); def test_modelo_349_pdf_sin_operaciones(); def test_modelo_200_pdf() … (+1)
  imports: app
  → usa: backend/app/services/pdf_reports/__init__.py
`backend/tests/test_money_path.py` (python, 118 loc) — Camino del dinero: persistencia del consumo LLM + tope agregado por tenant…
  symbols: async def _seed_tenant(); async def test_usage_persist_and_reload_roundtrip(); async def test_usage_persist_is_idempotent(); async def _seed_token_ledger(tenant_id, cost); async def test_tenant_budget_disabled_by_default(); async def test_tenant_budget_blocks_when_over(monkeypatch); async def test_tenant_budget_allows_when_under(monkeypatch)
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/llm_usage.py, backend/app/db/models/models.py, backend/app/services/__init__.py, backend/app/services/agent_budget.py
`backend/tests/test_multitenant_isolation.py` (python, 167 loc) — HTTP-level cross-tenant isolation tests…
  symbols: class TestClientsIsolation {test_b_cannot_list_a_clients, test_b_cannot_delete_a_client}; class TestInvoicesIsolation {_create_invoice_for, test_b_does_not_see_a_invoices, test_b_cannot_get_a_invoice_by_id}; class TestAIEmployeesIsolation {test_b_does_not_see_a_employees, test_b_cannot_get_a_employee_by_id, test_b_cannot_access_a_employee_usage, test_b_cannot_instruct_a_employee}; class TestHrEmployeesIsolation {test_b_does_not_see_a_employees}; class TestTasksIsolation {test_b_does_not_see_a_tasks}
  imports: datetime, httpx, pytest
`backend/tests/test_norma43_parser.py` (python, 153 loc) — Tests del parser Norma 43 (Cuaderno 43 AEB) — fixture sintética anonimizada
  symbols: def _line(code, body); def _mov22(fecha, dh, cents, doc); def _build_file(movs, saldo_inicial_cents); def test_parse_fichero_valido(); def test_to_rows_formato_import(); def test_registro_33_totales_no_cuadran(); def test_registro_33_numero_apuntes_no_cuadra(); def test_fichero_vacio_y_sin_cabecera(); def test_codigo_desconocido(); def test_decode_latin1(); async def test_import_n43_idempotente(db)
  imports: app, pytest
  → usa: backend/app/services/banking/parsers/norma43.py
`backend/tests/test_notifications.py` (python, 149 loc) — Tests del servicio de notificaciones persistentes (UI.NOT)
  symbols: class TestNotifications {test_create_y_list, test_count_unread, test_mark_read, test_mark_read_idempotente, test_mark_all_read, test_aislamiento_entre_tenants, test_broadcast_tenant_wide_visible_a_todos, test_only_unread_filtra}
  imports: app, pytest, uuid
  → usa: backend/app/services/__init__.py
`backend/tests/test_observability.py` (python, 173 loc) — Tests para app.core.observability — Logging, métricas y trazabilidad
  symbols: class TestStructuredFormatter {test_format_basic_record, test_format_with_extra_fields, test_format_with_exception}; class TestGetLogger {test_returns_logger, test_logger_has_handler, test_logger_level_is_info, test_same_logger_returned}; class TestTraceLlmCall {test_context_manager_yields_dict, test_context_data_persists, test_accepts_all_parameters, test_handles_exception_inside}; class TestMetricFunctions {test_record_task_metric_created, test_record_task_metric_completed, test_record_llm_latency, test_set_approvals_pending, test_record_http_request, test_record_http_request_normalizes_ids, test_ws_connection_opened, test_ws_connection_closed}; class TestGetMetricsRegistry {test_returns_registry_or_none}
  imports: app, json, logging, pytest
  → usa: backend/app/core/observability.py
`backend/tests/test_onboarding_regap.py` (python, 109 loc) — Tests del wizard REGAP (PRES.REG)
  symbols: class TestRegapWizard {test_status_inicial_es_not_started, test_idempotente, test_start_clave_va_a_identifying, test_start_cert_fnmt_va_a_cert_pending, test_grant_solo_desde_identifying_o_cert_pending, test_flow_completo_clave_pin, test_verify_solo_desde_power_granted, test_reset_vuelve_a_not_started}
  imports: app, pytest
  → usa: backend/app/services/onboarding/regap.py
`backend/tests/test_onboarding_seed.py` (python, 151 loc) — Tests del seed de datos de ejemplo del onboarding (services/onboarding/seed.py)…
  symbols: async def test_seed_creates_data_and_marks_step(db, seed_tenant_and_user); async def test_seed_is_idempotent(db, seed_tenant_and_user); async def test_demo_invoices_excluded_from_fiscal_but_visible(db, seed_tenant_and_user); async def test_real_invoice_still_appears_in_fiscal(db, seed_tenant_and_user); async def test_demo_invoices_do_not_consume_real_series(db, seed_tenant_and_user); async def test_clear_removes_only_demo(db, seed_tenant_and_user)
  imports: app, datetime, sqlalchemy
  → usa: backend/app/db/models/models.py, backend/app/services/billing/numbering.py, backend/app/services/onboarding/seed.py, backend/app/services/onboarding/wizard.py, backend/app/services/reports/modelos_aeat.py
`backend/tests/test_onboarding_wizard.py` (python, 155 loc) — Tests del wizard onboarding focado (UI.ONB)
  symbols: class TestWizard {test_estado_inicial_todo_falso, test_set_step_marca_un_paso, test_completar_los_5_setea_completed_at, test_completar_4_sin_llm_no_completa, test_completed_at_no_se_resetea_al_revertir, test_skip_marca_skipped_at, test_skip_idempotente, test_set_step_invalido}
  imports: app, pytest
  → usa: backend/app/services/onboarding/wizard.py
`backend/tests/test_orchestrator_clarification.py` (python, 53 loc) — Tests de la guarda de ambigüedad del Coordinador…
  symbols: def test_ambigua_lo_de_siempre(); def test_ambigua_vacia(); def test_ambigua_lo_tipico(); def test_ambigua_lo_de_costumbre(); def test_no_ambigua_con_dominio_y_cifra(); def test_no_ambigua_con_dominio(); def test_no_ambigua_instruccion_concreta(); def test_no_ambigua_sin_frase_vaga()
  imports: app
  → usa: backend/app/agents/orchestrator/_validate_handlers.py
`backend/tests/test_orchestrator_contract.py` (python, 157 loc) — QA.CTR — tests de contrato JSON orquestador ↔ agente…
  symbols: class TestAgentResultContract {test_keys_canonicas, test_construir_y_serializar_a_json, test_error_path}; class TestOrchestratorState {test_state_tiene_campos_minimos}; class TestAgentPackageExports {test_agent_module_importable, test_agent_exporta_graph_o_workflow}; class TestJsonSerializationSafety {test_output_acepta_tipos_jsonables, test_falla_visible_si_output_no_serializa}
  imports: __future__, app, importlib, json, pytest, typing
  → usa: backend/app/agents/orchestrator/state.py
`backend/tests/test_payroll_calc.py` (python, 150 loc) — Tests del cálculo de nómina: tope de base máxima y cuota de solidaridad…
  symbols: def test_topes_por_ano(); def test_por_debajo_del_tope_no_cambia_la_cotizacion(); def test_por_encima_del_tope_cotiza_sobre_el_tope(); def test_irpf_no_se_topa(); def test_tope_depende_del_ano(); def test_exactamente_en_el_tope(); def test_base_cero_todo_cero(); def test_mei_trabajador_por_ano(); def test_ss_mei_usa_tipo_del_ano(); def test_acepta_year_none_por_defecto(); def test_solidaridad_cero_por_debajo_del_tope(); def test_solidaridad_no_existia_antes_de_2025() … (+3)
  imports: app
  → usa: backend/app/services/hr/queries.py
`backend/tests/test_payroll_edge_cases.py` (python, 184 loc) — Edge cases de nómina: jornada parcial, pagas extra, horas extra, baja IT y finiquito…
  symbols: def test_defaults_reproduce_classic_calc(); def test_jornada_parcial_prorratea_base(); def test_14_pagas_sin_prorratear_cotiza_prorrata_pero_no_la_devenga(); def test_14_pagas_prorrateadas_suman_al_devengo(); def test_horas_extra_cotizan_aparte_y_tributan(); def test_horas_extra_fuerza_mayor_tipo_reducido(); def test_it_tramos_60_pct(); def test_it_tramo_75_pct_dia_21(); def test_it_days_overlap_baja_anterior_al_periodo(); def test_it_days_overlap_sin_solape(); def test_finiquito_baja_voluntaria_sin_indemnizacion(); def test_finiquito_despido_objetivo_20_dias_por_anio() … (+2)
  imports: app, datetime, pytest
  → usa: backend/app/services/hr/finiquito.py, backend/app/services/hr/queries.py
`backend/tests/test_payroll_migration_import.py` (python, 93 loc) — Migración de nóminas históricas (import desde otro programa)…
  symbols: async def _seed(db); def _row(periodo, neto); async def _count(db, tenant_id); class TestPayrollMigration {test_importa_y_preserva_importes, test_idempotente_no_duplica, test_distinto_periodo_si_crea, test_empleado_inexistente_error, test_falta_importe_obligatorio_error}
  imports: app, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/hr.py, backend/app/db/models/models.py, backend/app/services/migration/bulk_import.py
`backend/tests/test_planner_custom_agents.py` (python, 377 loc) — Tests para el soporte de AIEmployees custom en el planner del orchestrator…
  symbols: class TestCustomEmployeesHelpers {test_load_returns_only_custom_active, test_block_text_contains_name_role_id, test_block_includes_expertise_snippet_and_use_guidance, test_block_empty_when_no_employees, test_hash_stable_and_changes_with_set}; class TestValidateNodeCustomAgent {test_custom_with_params_employee_id_passes, test_custom_with_addressed_employee_id_in_metadata_passes, test_custom_without_employee_id_anywhere_fails}; class TestDispatcherCustomPerStepEmployee {test_step_params_employee_id_wins_over_metadata}; class TestDispatcherErrorPropagation {test_timeout_error_propagates_meaningful_message, test_exception_without_message_falls_back_to_type_name}
  imports: __future__, asyncio, pytest, sqlalchemy, unittest, uuid
`backend/tests/test_planner_robustness.py` (python, 177 loc) — Tests para los dos fixes del planner robustness: 1…
  symbols: class _PlanStep; class _Plan; def _parse_via_claude_code(raw); class TestClaudeCodeStructuredOutputParser {test_clean_json, test_json_wrapped_in_markdown, test_json_with_prose_before, test_json_with_prose_after, test_two_sibling_objects_takes_first, test_brace_in_prose_then_real_json}; class TestValidateNodeHeuristicFallback {test_empty_plan_with_billing_keywords_routes_to_billing, test_empty_plan_with_payroll_keywords_routes_to_hr, test_empty_plan_with_no_keywords_falls_back_to_chat, test_non_empty_plan_passes_through, test_invalid_agent_in_plan_still_fails}
  imports: __future__, pydantic, pytest
`backend/tests/test_portal_serialization.py` (python, 53 loc) — Regresión: el portal admin "ver como empleado" salía EN BLANCO…
  symbols: def _orm(model); def test_leave_request_response_validates_from_orm_instance(); def test_attendance_response_validates_from_orm_instance()
  imports: app, datetime, uuid
  → usa: backend/app/api/v1/__init__.py, backend/app/db/models/hr.py
`backend/tests/test_preconditions.py` (python, 37 loc) — Tests para el kill-switch de precondiciones (CONT.KILL)
  symbols: class TestPreconditions {test_check_invoice_preconditions_ok, test_endpoint_get_preconditions, test_required_tables_son_las_3_esperadas}
  imports: app, httpx, pytest
  → usa: backend/app/main.py, backend/app/services/system/preconditions.py
`backend/tests/test_presentacion_asistida.py` (python, 94 loc) — Tests de presentación asistida (PRES.ASS)
  symbols: def _tenant(year, quarter); class TestBuildXml {test_modelo_131_contiene_datos_tenant, test_modelo_131_devengo_correcto, test_modelo_200_periodo_es_anual, test_modelo_200_tipo_gravamen_25, test_meta_prerelleno_presente, test_caracteres_especiales_escapados}; class TestBuildXmlDispatcher {test_modelo_131, test_modelo_200, test_modelo_invalido_lanza}; class TestSedeLinks {test_linkmaps_apunta_a_sede_oficial, test_modelo_invalido_lanza, test_links_son_estables}
  imports: app, pytest
  → usa: backend/app/services/presentacion/asistida.py
`backend/tests/test_preventive_check.py` (python, 212 loc) — Tests del asistente fiscal preventivo (F1.4)
  symbols: def _inv(tenant_id, client_id); def _line(qty, price, tax_pct); def _codes(findings); async def test_sin_facturas_sin_hallazgos(db, seed_tenant_and_user); async def test_received_sin_nif_proveedor_detectado(db, seed_tenant_and_user); async def test_factura_sin_lineas_detectada(db, seed_tenant_and_user); async def test_totales_descuadrados(db, seed_tenant_and_user); async def test_draft_emitida_en_periodo_detectada(db, seed_tenant_and_user); async def test_iva_repercutido_sin_facturas_recibidas(db, seed_tenant_and_user); async def test_severidad_ordenada_high_primero(db, seed_tenant_and_user); async def test_quarter_invalido_raises(db, seed_tenant_and_user)
  imports: app, datetime, decimal, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/aeat/preventive_check.py
`backend/tests/test_prompt_e2e.py` (python, 1130 loc) — E2E Prompt Tests — dos niveles: 1…
  symbols: def _load_prompt(name); def _has_real_llm(); class TestBillingPromptContent {setup_method, test_iva_critico_rule_exists, test_iva_example_1210_to_1000, test_few_shot_create_invoice_example, test_few_shot_no_create_on_query, test_tipo_reducido_alimentacion_example, test_send_invoice_example, test_tenant_id_placeholder}; class TestHRPromptContent {setup_method, test_salary_annual_to_monthly_rule, test_generate_all_payrolls_example, test_mes_pasado_resolved, test_nif_required_for_employee, test_list_employees_before_payroll, test_current_date_injected}; class TestClassifierPromptContent {setup_method, test_has_all_critical_domains, test_single_word_instruction, test_workflow_trigger_words}; class TestWorkflowPromptContent {setup_method, test_cron_format_documented, test_ui_nodes_required_for_create, test_event_based_and_schedule_based, test_action_config_with_domain}; class TestBankingPromptContent {setup_method, test_check_balances_tool_mentioned, test_list_transactions_tool_mentioned, test_financial_summary_tool_mentioned, test_reconcile_tool_mentioned, test_tenant_id_placeholder, test_saldo_routing_rule}; class TestCompliancePromptContent {setup_method, test_fiscal_deadlines_tool_mentioned, test_boe_news_tool_mentioned, test_fiscal_query_tool_mentioned, test_tenant_id_placeholder, test_asesor_fiscal_disclaimer, test_plazos_routing_rule}; class TestCRMPromptContent {setup_method, test_list_opportunities_tool_mentioned, test_qualify_leads_tool_mentioned, test_create_opportunity_tool_mentioned, test_update_opportunity_stage_tool_mentioned, test_agente_comercial_identity}; class TestDocumentsPromptContent {setup_method, test_classify_document_tool_mentioned, test_search_documents_semantic_tool_mentioned, test_tenant_id_placeholder, test_nif_linking_mentioned, test_document_types_mentioned}; class TestEmailPromptContent {setup_method, test_check_inbox_tool_mentioned, test_send_email_tool_mentioned, test_check_unread_tool_mentioned, test_tenant_id_injected, test_attachment_workflow_mentioned}; class TestExcelPromptContent {setup_method, test_export_erp_data_tool_mentioned, test_import_excel_tool_mentioned, test_list_available_datasets_tool_mentioned, test_tenant_id_placeholder, test_datasets_documented, test_critical_export_rule} … (+29)
  imports: os, pathlib, pytest, re
`backend/tests/test_prompt_sanitizer.py` (python, 58 loc) — Tests para app.core.prompt_sanitizer
  symbols: class TestSanitizeUserInput {test_normal_input_unchanged, test_empty_input, test_truncation, test_default_max_length, test_filters_system_tag, test_filters_inst_tag, test_filters_ignore_instructions, test_filters_you_are_now}
  imports: app
  → usa: backend/app/core/prompt_sanitizer.py
`backend/tests/test_prompt_snapshots.py` (python, 107 loc) — QA.PRM — snapshot tests de prompts…
  symbols: def _collect_prompts(); def _load_snapshot(); class TestPromptSnapshots {test_existe_baseline, test_baseline_cubre_todos_los_prompts, test_baseline_no_referencia_prompts_inexistentes, test_hashes_coinciden_con_baseline, test_descubre_prompts_de_ambos_directorios}
  imports: __future__, hashlib, json, pathlib, pytest
`backend/tests/test_rag_agent.py` (python, 69 loc) — Smoke tests for the rag agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_rag_tools_registered(); async def test_rag_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_rbac_admin_endpoints.py` (python, 73 loc) — SEC.RBAC — los endpoints de gestión (import masivo + conectar/desconectar integraciones) exigen rol admin…
  symbols: async def user_client(db); class TestRbacAdminOnly {test_user_cannot_bulk_import, test_user_cannot_disconnect_gmail, test_user_cannot_disconnect_psd2, test_user_can_read_integrations_list}; class TestRbacAdminAllowed {test_admin_can_bulk_import}
  imports: app, httpx, pytest, pytest_asyncio, uuid
  → usa: backend/app/core/security.py, backend/app/db/models/models.py, backend/app/main.py
`backend/tests/test_reconciliation_explainable.py` (python, 186 loc) — Tests del scoring explicable de conciliación + rechazo persistente (F2.6)
  symbols: def test_normalize_client_name(raw, expected); def _make_pair(); def test_explain_match_solo_importe(); def test_explain_match_importe_y_fecha_proxima(); def test_explain_match_cliente_completo_en_concepto(); def test_explain_match_cliente_por_token_largo(); def test_explain_match_normaliza_suffix_legal(); async def test_rechazo_oculta_par_de_sugerencias(db, seed_tenant_and_user); async def test_rechazo_idempotente(db, seed_tenant_and_user)
  imports: app, datetime, decimal, pytest, types
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/db/models/models.py, backend/app/services/banking/service.py
`backend/tests/test_recruitment_agent.py` (python, 77 loc) — Smoke tests for the recruitment agent: graph, tools, and node logic
  symbols: def test_graph_compiles(); def test_graph_has_expected_nodes(); def test_tools_not_empty(); def test_tools_have_docstrings(); def test_core_recruitment_tools_registered(); async def test_recruitment_agent_node_invokes_llm()
  imports: langchain_core, pytest, unittest
`backend/tests/test_recruitment_business.py` (python, 117 loc) — Tests de negocio del agente recruitment…
  symbols: async def test_create_position_rejects_empty_title(); async def test_create_position_rejects_bad_tenant_uuid(); async def test_list_positions_rejects_bad_tenant_uuid(); async def test_list_candidates_rejects_bad_position_uuid(); async def test_update_candidate_status_rejects_invalid_status(); async def test_create_candidate_rejects_empty_name(); async def test_process_cv_bad_uuid_returns_friendly_error(); async def test_process_cv_missing_file_degrades(); async def test_process_cv_empty_text_degrades(); async def test_process_cv_llm_failure_degrades()
  imports: app, pytest, unittest
  → usa: backend/app/agents/recruitment/tools.py
`backend/tests/test_rectificativa.py` (python, 122 loc) — Tests de facturas rectificativas por anulación (RD 1619/2012 Art…
  symbols: async def _seed(db); async def _original(db, tenant, client); class TestCreateRectificativa {test_importes_negados, test_tipo_vinculo_y_motivo, test_numeracion_serie_r, test_lineas_espejo_negadas, test_idempotencia_no_doble_abono, test_motivo_obligatorio, test_original_inexistente, test_no_rectificar_una_rectificativa}
  imports: app, datetime, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/db/models/billing.py, backend/app/services/billing/invoice.py
`backend/tests/test_request_context.py` (python, 134 loc) — Tests del ContextVar de request_id y su integración con observabilidad…
  symbols: def _reset(); def test_set_get_roundtrip(); def test_request_context_restores_previous(); async def test_concurrent_tasks_do_not_contaminate(); def test_structured_formatter_auto_injects_request_id(); def test_structured_formatter_explicit_extra_overrides_contextvar(); def test_structured_formatter_no_request_id_field_when_unset(); def test_trace_llm_call_uses_contextvar_as_default_trace_id(); def test_trace_llm_call_explicit_trace_id_wins_over_contextvar()
  imports: app, asyncio, json, logging, pytest
  → usa: backend/app/core/observability.py, backend/app/core/request_context.py
`backend/tests/test_rls.py` (python, 56 loc) — Tests para Row-Level Security helper (SEC.RLS)…
  symbols: class TestApplyTenantRls {test_sqlite_devuelve_none_sin_error, test_sqlite_con_tenant_sigue_devolviendo_none, test_tenant_invalido_no_lanza, test_context_var_se_lee_correctamente}; class TestRlsMigrationSafety {test_migracion_no_rompe_sqlite_setup}
  imports: app, pytest, uuid
  → usa: backend/app/core/tenant_context.py, backend/app/db/rls.py
`backend/tests/test_rls_postgres.py` (python, 255 loc) — SEC.RLS Fase C — verificación end-to-end de la RLS fail-closed contra Postgres…
  symbols: async def _admin_connect(database); def _setup_schema(sync_conn); async def _provision(); async def _teardown(); def pg_rls_db(); async def app_engine(pg_rls_db); async def _count(engine); def _pg_sqlstate(exc); async def test_tenant_scoped_select_solo_ve_su_tenant(app_engine); async def test_sin_tenant_es_fail_closed(app_engine); async def test_rls_bypass_ve_todos_los_tenants(app_engine); async def test_with_check_permite_insert_del_propio_tenant(app_engine) … (+2)
  imports: __future__, app, asyncio, os, pytest, pytest_asyncio, sqlalchemy, uuid
  → usa: backend/app/core/tenant_context.py, backend/app/db/rls.py, backend/app/db/security_bootstrap.py
`backend/tests/test_routing_seam.py` (python, 337 loc) — Tests del seam de routing — bloquean en CI la familia de bugs que vimos en la sesion del 2026-05-07…
  symbols: def _emp(name, role, domain); def test_generate_preview_nodes_uses_custom_for_billing(); def test_generate_preview_nodes_uses_builtin_name_when_no_custom(); async def test_plan_from_blueprint_propagates_employee_id(seed_tenant_and_user); def test_build_skill_dispatch_propagates_employee_id(); async def test_plan_node_single_domain_swaps_to_custom(db, seed_tenant_and_user); async def test_resolve_custom_employee_matches_by_name_with_correct_filter(db, seed_tenant_and_user); async def test_invoke_dispatcher_routes_custom_with_employee_id_intact()
  imports: __future__, pytest, sqlalchemy, types, unittest, uuid
`backend/tests/test_scanner_auth.py` (python, 138 loc) — Tests para app.middleware.scanner_auth — Tokens de escáner móvil
  symbols: class TestCreateScannerToken {test_returns_dict_with_token, test_token_is_decodable, test_custom_device_name, test_scope_matches_config, test_token_has_expiration}; class TestDecodeScannerToken {test_valid_token, test_expired_token_raises_401, test_invalid_token_raises_401, test_non_scanner_sub_raises_403}; class TestIsScannerToken {test_valid_scanner_token, test_regular_token_returns_false, test_no_auth_header_returns_false, test_invalid_token_returns_false, test_non_bearer_returns_false}
  imports: app, datetime, fastapi, jwt, pytest, time
  → usa: backend/app/core/config.py, backend/app/middleware/scanner_auth.py
`backend/tests/test_scheduler_next_due_run.py` (python, 52 loc) — _next_due_run: catch-up de ticks retrasados sin doble disparo
  symbols: def _at(h, m, s); def test_minuto_exacto_dispara(); def test_tick_retrasado_dentro_de_gracia_recupera(); def test_fuera_de_ventana_no_dispara(); def test_cron_cada_minuto_devuelve_el_ultimo_vencido(); def test_sin_cron_o_invalido(); def test_infer_domain_sin_keywords_va_al_coordinador()
  imports: app, datetime, zoneinfo
  → usa: backend/app/workers/tasks_scheduler.py
`backend/tests/test_security.py` (python, 135 loc) — Tests para app.core.security — hashing, tokens JWT
  symbols: class TestPasswordHashing {test_hash_and_verify, test_wrong_password_fails, test_different_hashes_for_same_password, test_empty_password, test_unicode_password}; class TestAccessToken {test_create_and_decode, test_custom_expiry, test_expired_token_returns_none, test_invalid_token_returns_none}; class TestRefreshToken {test_create_and_decode, test_refresh_token_differs_from_access}; class TestMaskIban {test_iban_sin_espacios, test_iban_con_espacios, test_iban_dentro_de_texto, test_iban_minusculas_normaliza_pais, test_no_es_iban_no_toca, test_string_corto_no_se_toca, test_idempotente_no_re_enmascara, test_iban_pais_diferente}
  imports: app, datetime
  → usa: backend/app/core/security.py
`backend/tests/test_security_hardening.py` (python, 112 loc) — Regresión de la tanda de seguridad (auditoría 2026-06-25): SEC1 / X1 / SEC2…
  symbols: def test_verify_webhook_secret_fail_closed_sin_secreto(monkeypatch); def test_verify_webhook_secret_ok_con_secreto(monkeypatch); def test_reset_email_produccion_sin_smtp_no_filtra_token_ni_finge(monkeypatch, caplog); def test_reset_email_dev_sin_smtp_muestra_enlace(monkeypatch, caplog); async def _start(db, tenant_id); async def test_callback_rechaza_sesion_caducada(db, seed_tenant_and_user); async def test_callback_sesion_reciente_no_caduca(db, seed_tenant_and_user)
  imports: app, base64, datetime, logging, pytest, sqlalchemy
  → usa: backend/app/db/models/signed_document.py, backend/app/services/auth/__init__.py, backend/app/services/integration/__init__.py, backend/app/services/signing/autofirma.py, backend/app/services/signing/sessions.py
`backend/tests/test_security_hardening_medium.py` (python, 90 loc) — Regresión de la tanda de seguridad MEDIUM (auditoría 2026-06-25): M1 / M2 / M3…
  symbols: async def _seed_client_with_token(db, tenant_id); async def test_portal_jwt_rechazado_si_token_revocado(db, seed_tenant_and_user); async def test_portal_jwt_ok_si_token_activo(db, seed_tenant_and_user); def test_frontend_origin_extrae_origen_del_primero(monkeypatch); def test_frontend_origin_localhost(monkeypatch); async def test_import_db_rechaza_fichero_demasiado_grande(auth_client, monkeypatch)
  imports: app, fastapi, pytest
  → usa: backend/app/core/__init__.py, backend/app/core/dependencies.py, backend/app/core/security.py, backend/app/db/models/auth.py, backend/app/db/models/crm.py
`backend/tests/test_semantic_search_disabled_fallback.py` (python, 47 loc) — Cuando la tabla document_embeddings o la extensión pgvector no están instaladas (caso del Postgres portable que distribuye la app), las tool…
  symbols: class _FakeUndefinedTable {__str__}; class TestSemanticSearchGracefulDisabled {test_disabled_message_mentions_alternative_tool, test_helper_detects_sqlstate_42P01, test_helper_detects_message_text, test_helper_detects_pgvector_missing, test_helper_passes_unrelated_errors}
  imports: __future__
`backend/tests/test_semantic_search_python_cosine.py` (python, 147 loc) — Tests para la búsqueda semántica sin pgvector — cálculo coseno en Python sobre embeddings almacenados como JSONB en document_embeddings
  symbols: class TestCosineDistance {test_identical_vectors_distance_zero, test_orthogonal_vectors_distance_one, test_opposite_vectors_distance_two, test_zero_vector_returns_max_distance, test_length_mismatch_returns_max_distance, test_similarity_clamped_to_zero}; class TestIsMissingTableOrExtension {test_sqlstate_42P01_is_missing, test_sqlstate_42704_is_missing, test_text_does_not_exist_is_missing, test_unrelated_error_is_not_missing}; class TestCosineTopkAgainstDB {test_topk_returns_closest_first, test_topk_filters_by_tenant}
  imports: __future__, app, pytest, sqlalchemy, uuid
  → usa: backend/app/agents/agent_tools/semantic_search.py
`backend/tests/test_service_activity.py` (python, 72 loc) — Tests para app.services.activity_service — feed de actividad…
  symbols: class TestActivityService {test_log_activity_creates_entry, test_log_activity_with_metadata, test_log_activity_with_task_id}
  imports: app, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/ai_employees.py
`backend/tests/test_service_ai_employee_crud.py` (python, 118 loc) — Tests para app.services.ai.employee_crud — CRUD de empleados IA (cobertura QA)…
  symbols: async def _make_employee(db, tenant_id); class TestEmployeeCrud {test_list_vacio, test_create_y_list, test_create_sin_capacidades_ok, test_update_icon, test_update_icon_no_existe_devuelve_none, test_update_appearance, test_update_status_idle_y_otro, test_update_status_no_existe}
  imports: app, pytest, uuid
  → usa: backend/app/services/ai/employee_crud.py
`backend/tests/test_service_audit.py` (python, 85 loc) — Tests para app.services.audit — logging inmutable de acciones
  symbols: class TestAuditService {test_log_action_creates_record, test_log_action_with_error, test_log_llm_call, test_log_action_with_task_id}
  imports: app, pytest, sqlalchemy
  → usa: backend/app/db/models/models.py, backend/app/services/audit.py
`backend/tests/test_service_auth.py` (python, 249 loc) — Tests para app.services.auth.service — login, refresh, reset de contraseña…
  symbols: async def _seed_user(db); class TestRegister {test_crea_tenant_y_usuario_admin, test_falla_si_email_duplicado, test_falla_si_nif_duplicado}; class TestLogin {test_devuelve_par_de_tokens, test_falla_con_password_incorrecto, test_falla_si_email_no_existe, test_falla_si_cuenta_desactivada}; class TestRefresh {test_genera_nuevos_tokens, test_falla_si_token_invalido, test_falla_si_es_access_token_en_lugar_de_refresh}; class TestResetPassword {test_forgot_no_revela_existencia_de_email, test_forgot_crea_token_si_user_existe, test_reset_actualiza_password_y_marca_token_usado, test_reset_falla_si_password_corta, test_reset_falla_si_token_invalido, test_reset_falla_si_token_ya_usado, test_reset_falla_si_token_expirado}
  imports: app, datetime, pytest, sqlalchemy, unittest, uuid
  → usa: backend/app/core/security.py, backend/app/db/models/models.py, backend/app/services/auth/__init__.py, backend/app/services/auth/_schemas.py
`backend/tests/test_service_email_marketing_campaigns.py` (python, 96 loc) — Regresión R1 (2026-06-25): la lógica de email marketing vive en services/, no en la ruta…
  symbols: async def _seed_clients(db, tenant_id); async def test_create_campaign_precarga_solo_destinatarios_consentidos(db, seed_tenant_and_user); async def test_recipient_count(db, seed_tenant_and_user); async def test_campaign_crud_via_service(db, seed_tenant_and_user); async def test_template_crud_via_service(db, seed_tenant_and_user)
  imports: app, pytest, sqlalchemy, types
  → usa: backend/app/db/models/crm.py, backend/app/db/models/email_marketing.py, backend/app/services/email_marketing/__init__.py
`backend/tests/test_service_exec_log.py` (python, 49 loc) — Tests para app.services.exec_log_store — buffer en memoria con TTL
  symbols: class TestExecLogStore {setup_method, test_push_and_get, test_get_nonexistent_task, test_clear, test_clear_nonexistent_no_error, test_multiple_tasks_isolated, test_ttl_eviction, test_push_updates_expiry}
  imports: app, time
  → usa: backend/app/services/exec_log_store.py
`backend/tests/test_service_hr_generate_document.py` (python, 52 loc) — Regresión R2 (2026-06-25): `generate_document` persiste el HRDocument con el `db` inyectado de la request, no con una `AsyncSessionLocal` ap…
  symbols: async def test_generate_document_persiste_con_db_inyectado(db, seed_tenant_and_user)
  imports: app, langchain_core, pytest, sqlalchemy, unittest, uuid
  → usa: backend/app/db/models/hr_documents.py, backend/app/services/hr/commands.py
`backend/tests/test_service_hr_payroll.py` (python, 221 loc) — Tests para app.services.hr — cálculo y persistencia de nóminas…
  symbols: async def _seed_employee(db, tenant_id); class TestCalcPayroll {test_aplica_tasas_ss_estandar, test_irpf_se_calcula_sobre_base, test_net_salary_es_base_menos_deducciones, test_irpf_cero_solo_descuenta_ss, test_base_cero_produce_todo_cero}; class TestPreviewPayroll {test_devuelve_calculo_con_irpf_del_empleado, test_falla_si_empleado_no_existe, test_falla_si_empleado_no_tiene_salario_base}; class TestCreatePayrollAuto {test_persiste_nomina_con_calculo_automatico, test_usa_base_salary_del_payload_si_se_indica, test_falla_si_base_salary_cero, test_falla_si_empleado_no_existe}
  imports: app, datetime, decimal, pytest, sqlalchemy, types, uuid
  → usa: backend/app/db/models/hr.py, backend/app/db/models/models.py, backend/app/services/hr/queries.py, backend/app/services/hr/commands.py
`backend/tests/test_service_invoice.py` (python, 325 loc) — Tests para app.services.billing.invoice — CRUD de facturas
  symbols: async def _seed_tenant_client(db); async def _create_basic_invoice(db, tenant, client, user_id); class TestValidIva {test_valid_iva_values}; class TestCreateInvoice {test_create_invoice_basic, test_invoice_amounts_calculated, test_invoice_with_discount, test_invoice_with_zero_iva, test_invoice_invalid_iva_raises, test_invoice_manual_number, test_duplicate_issued_number_raises, test_received_can_share_number_with_issued}; class TestListInvoices {test_list_empty, test_list_with_invoices, test_list_pagination, test_list_tenant_isolation}; class TestGetInvoice {test_get_existing, test_get_nonexistent}; class TestUpdateStatus {test_update_to_paid, test_update_invalid_status_raises, test_update_nonexistent_raises}; class TestDeleteInvoice {test_delete_existing, test_delete_nonexistent}
  imports: app, datetime, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/billing/invoice.py
`backend/tests/test_service_marketing_extractions.py` (python, 148 loc) — Regresión R1 (2026-06-25): extracción de marketing.py → services…
  symbols: async def _seed_account(db, tenant_id); async def _seed_post(db, tenant_id, account_id); def _fake_publisher(ok); async def test_disconnect_account_desactiva_y_llama_zernio(db, seed_tenant_and_user); async def test_disconnect_account_inexistente_devuelve_false(db, seed_tenant_and_user); async def test_disconnect_account_propaga_error_zernio_no_404(db, seed_tenant_and_user); async def test_publish_single_post_ok(db, seed_tenant_and_user); async def test_publish_single_post_inexistente(db, seed_tenant_and_user); async def test_publish_single_post_ya_publicado(db, seed_tenant_and_user); async def test_publish_posts_batch_separa_ok_y_fallidos(db, seed_tenant_and_user)
  imports: app, pytest, unittest, uuid
  → usa: backend/app/db/models/marketing.py, backend/app/services/marketing/__init__.py, backend/app/services/marketing/publisher_base.py, backend/app/services/marketing/publishing.py, backend/app/services/marketing/zernio_client.py
`backend/tests/test_service_period_close.py` (python, 123 loc) — Tests para app.services.accounting.period_close — cierre/reapertura de periodos contables y comprobación de bloqueo (cobertura QA)
  symbols: def test_period_closed_error_mensaje(); class TestClosePeriod {test_kind_invalido, test_month_index_fuera_rango, test_quarter_index_fuera_rango, test_year_index_debe_ser_cero, test_cierra_mes_nuevo, test_cierre_idempotente}; class TestReopenPeriod {test_requiere_motivo, test_periodo_no_existe, test_reabre_ok}; class TestLockAndList {test_is_date_locked_true, test_is_date_locked_false_fuera_de_rango, test_list_periods_filtra_por_year}; def _period(kind, year, idx); def test_contains_date_ramas()
  imports: app, datetime, pytest, uuid
  → usa: backend/app/services/accounting/period_close.py
`backend/tests/test_service_sales_albaran.py` (python, 221 loc) — Tests para app.services.sales.commands — flujo de stock en albaranes…
  symbols: async def _seed_client_and_product(db, tenant_id); def _line(product_id, qty, price); class TestUpdateAlbaranStatus {test_pasar_a_confirmed_descuenta_stock, test_confirmed_a_draft_revierte_stock, test_idempotencia_doble_confirmacion_no_duplica_movements, test_falla_si_estado_invalido, test_falla_si_no_existe, test_confirmacion_falla_si_stock_insuficiente, test_delete_albaran_confirmado_revierte_stock}
  imports: app, decimal, pytest, sqlalchemy, types, uuid
  → usa: backend/app/db/models/crm.py, backend/app/db/models/inventory.py, backend/app/services/sales/commands.py
`backend/tests/test_service_sales_commands.py` (python, 300 loc) — Tests para app.services.sales.commands — CRUD de clientes, productos, movimientos de stock y presupuestos (cobertura QA)…
  symbols: class TestClientCommands {test_create_client_ok_emite_evento, test_create_client_nif_duplicado_raise_value_error, test_update_client_ok, test_update_client_no_existe_raise_lookup, test_delete_client_ok, test_delete_client_no_existe_raise_lookup}; def _product_data(); class TestProductCommands {test_create_product_ok, test_update_product_ok, test_update_product_no_existe, test_delete_product_ok, test_delete_product_no_existe}; class TestStockMovementCommands {test_entrada_incrementa_stock, test_salida_decrementa_stock, test_salida_insuficiente_raise_value_error, test_ajuste_fija_stock_absoluto, test_producto_no_existe_raise_lookup, test_baja_unidades_con_motivo_persiste, test_baja_cajas_descuenta_contador_independiente, test_baja_cajas_insuficiente_raise_value_error}; class TestQuoteCommands {_make_client, test_create_quote_calcula_importes, test_update_quote_ok, test_update_quote_no_existe, test_delete_quote_ok}
  imports: app, decimal, pytest, sqlalchemy, uuid
  → usa: backend/app/db/models/inventory.py, backend/app/services/sales/commands.py
`backend/tests/test_service_workflow_approval.py` (python, 283 loc) — Tests para app.services.workflow.approval…
  symbols: async def _ctx(db); def _utcnow(); async def _make_task(db, tenant_id, status); async def _make_approval(db, tenant_id, task_id, expires_in_minutes, status, execution_id); class TestListPending {test_devuelve_solo_pending, test_ordenado_por_expires_at_asc, test_aislamiento_por_tenant}; class TestDecide {test_approved_happy_path, test_rejected_con_razon, test_rechazo_si_no_existe, test_rechazo_si_ya_cerrada, test_marca_expirada_si_pasó_expires_at, test_aislamiento_por_tenant}; class TestCleanupAll {test_borra_todas_y_devuelve_count, test_cancela_tasks_de_aprobaciones_pending, test_no_toca_tasks_terminales, test_aislamiento_por_tenant, test_devuelve_0_si_no_hay_aprobaciones}
  imports: app, datetime, pytest, unittest, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/workflow/__init__.py
`backend/tests/test_service_workflow_db_providers.py` (python, 298 loc) — Tests para app.services.workflow.db_query_providers y db_conditions…
  symbols: async def _tenant(db); def _utcnow(); class TestCollectProviderLeaves {test_none_devuelve_vacio, test_arbol_vacio_devuelve_vacio, test_hoja_provider_se_recoge, test_hoja_sin_provider_no_se_recoge, test_arbol_AND_recoge_hijos, test_arbol_OR_recoge_hijos, test_NOT_recoge_hijo_anidado, test_arbol_mixto_AND_NOT}; class TestResolveDbConditions {test_sin_hojas_provider_devuelve_contexto_intacto, test_provider_se_resuelve_y_se_inyecta_en_db_ctx, test_provider_desconocido_no_rompe, test_provider_que_lanza_excepcion_devuelve_None}; class TestBillingProviders {_make_invoices, test_pending_invoice_count, test_unpaid_total, test_overdue_count, test_aislamiento_por_tenant}; class TestHrProviders {_make_employees, _make_payrolls, test_employee_count, test_draft_payroll_count, test_payrolls_this_month}; class TestRegistryIntegrity {test_todos_los_providers_son_callables, test_no_hay_keys_duplicadas}
  imports: app, datetime, decimal, pytest, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/workflow/db_conditions.py, backend/app/services/workflow/db_query_providers.py
`backend/tests/test_service_workflow_execution.py` (python, 288 loc) — Tests para app.services.workflow._execution…
  symbols: def _mk_workflow(tenant_id); async def _tenant(db); class TestBuildAiInstruction {test_usa_instruction_si_existe, test_fallback_a_intent, test_fallback_a_description, test_fallback_a_name, test_default_final_si_todo_None, test_action_config_None_no_crashea}; class TestInferDomain {test_coordinator_si_agent_coordinator, test_orchestrator_por_defecto, test_orchestrator_si_agent_otro, test_action_config_None_no_crashea}; class TestRunDeterministicStep {test_sin_tool_marca_error, test_happy_path, test_reemplaza_prev_en_params, test_inyecta_tenant_id_si_falta, test_exception_se_captura_en_result}; class TestExecuteDeterministicSteps {test_lista_vacia_devuelve_vacio, test_steps_deterministicos_secuenciales_propagan_prev, test_step_sin_tool_pasa_a_reasoning_mockeado}; class TestCancelExecution {_make_wf_exec, test_cancela_ejecucion_running, test_rechaza_si_no_existe, test_rechaza_si_estado_terminal}; class TestRunWorkflow {_make_workflow, test_lanza_value_error_si_no_existe, test_lanza_value_error_si_desactivado, test_lanza_value_error_si_ya_en_curso, test_dispatch_reasoning_happy_path}
  imports: app, pytest, unittest, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/workflow/_execution.py
`backend/tests/test_service_workflow_fiscal_approval.py` (python, 431 loc) — Tests para app.services.workflow.fiscal_approval (SEC.APR)…
  symbols: async def _tenant_user_task(db); class TestComputePayloadHash {test_hash_deterministico, test_hash_order_independent, test_hash_cambia_si_cambia_payload, test_hash_acepta_datetimes}; class TestBuildExpectedApprovalText {test_formato_canonico, test_anyo_solo_sin_quarter}; class TestValidateApprovalText {test_match_exacto, test_match_sin_acentos, test_match_case_insensitive, test_match_con_whitespace_externo, test_no_match_si_texto_diferente, test_no_match_si_periodo_diferente}; class TestRequestFiscalApproval {test_crea_pending_approval_con_risk_level_correcto, test_sin_quarter_solo_anyo}; class TestApproveFiscal {_make_pending, test_approve_happy_path, test_approve_rechaza_texto_incorrecto, test_approve_falla_si_pending_no_existe, test_approve_falla_si_ya_cerrado}; class TestRejectFiscal {test_reject_happy_path}; class TestHasValidFiscalApproval {test_hit_si_payload_hash_coincide, test_miss_si_payload_cambia, test_miss_si_decision_rejected, test_aislamiento_por_tenant}
  imports: app, pytest, uuid
  → usa: backend/app/db/models/models.py, backend/app/db/models/tasks.py, backend/app/services/workflow/__init__.py
`backend/tests/test_service_workflow_nlp_extra.py` (python, 217 loc) — Tests adicionales para app.services.workflow._nlp…
  symbols: async def _tenant(db); async def _make_employee(db, tenant_id, status, is_builtin); async def _make_workflow(db, tenant_id); class TestLoadTenantEmployees {test_tenant_id_None_devuelve_vacio, test_tenant_id_vacio_devuelve_vacio, test_filtra_por_status_activo, test_aislamiento_por_tenant, test_db_error_devuelve_vacio_sin_crashear}; class TestFireEvent {test_sin_workflows_devuelve_vacio, test_workflow_inactivo_no_dispara, test_evento_no_coincide_skip, test_evento_any_coincide_con_cualquiera, test_condition_falsa_bloquea_dispatch, test_condition_verdadera_lanza, test_deterministic_path_se_invoca_si_modo_determinista_y_compiled_steps, test_reasoning_path_si_no_es_determinista}
  imports: app, pytest, unittest, uuid
  → usa: backend/app/db/models/ai_employees.py, backend/app/db/models/models.py, backend/app/services/workflow/_nlp.py
`backend/tests/test_service_workflow_parse_nl.py` (python, 150 loc) — Tests para app.services.workflow._nlp.parse_natural_language…
  symbols: def _make_llm_mock(json_payload, determinism); class TestParseNaturalLanguage {test_genera_schema_event_based, test_genera_schema_cron, test_acepta_respuesta_envuelta_en_markdown_json, test_falla_si_llm_devuelve_json_invalido, test_determinism_check_fallback_si_falla}
  imports: app, json, pytest, types, unittest
  → usa: backend/app/services/workflow/_nlp.py
`backend/tests/test_service_workflow_recovery.py` (python, 224 loc) — Tests para app.services.workflow.recovery…
  symbols: async def _make_workflow(db, tenant_id); async def _tenant(db); def _utcnow(); def _patch_session(monkeypatch); class TestRecoverStaleExecutions {test_zombie_task_sin_progreso_y_vieja_se_marca_failed, test_zombie_sin_progreso_5min_aunque_no_supere_30min, test_task_viva_con_progreso_pero_solo_7min_NO_se_toca, test_execution_huerfana_sin_task_se_marca_cancelled, test_execution_con_task_zombie_se_sincroniza_a_failed, test_recovery_idempotente_sin_zombies}
  imports: app, datetime, pytest, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/workflow/recovery.py
`backend/tests/test_service_workflow_scheduler.py` (python, 216 loc) — Tests para app.services.workflow.scheduler…
  symbols: def _utcnow(); async def _tenant(db); async def _make_workflow(db, tenant_id); class TestGetActiveScheduledWorkflows {test_devuelve_solo_active_schedule_based}; class TestHasActiveExecution {test_true_si_hay_running, test_true_si_hay_pending, test_false_si_solo_terminales, test_false_si_no_hay_ejecuciones}; class TestGetLastExecution {test_devuelve_la_mas_reciente, test_devuelve_None_si_no_hay}; class TestCreateExecution {test_inserta_y_flush, test_tenant_id_se_propaga_del_workflow}; class TestCreateTaskForExecution {test_crea_task_y_vincula_a_execution}; class TestGetStuckExecutions {test_filtra_solo_running_antes_de_cutoff}; class TestMarkExecutionsFailed {test_marca_failed_y_appendea_note, test_lista_vacia_no_crashea}
  imports: app, datetime, pytest, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/workflow/scheduler.py
`backend/tests/test_service_workflow_scheduler_dispatch.py` (python, 267 loc) — Cobertura del path crítico de dispatch del scheduler (cada minuto)…
  symbols: async def _seed_workflow(); async def _add_execution(wf_id, tenant_id, status); async def _executions(wf_id); async def _tasks(tenant_id); def _install_fake_guard(monkeypatch, already); async def test_due_workflow_dispatches_reasoning(monkeypatch); async def test_domain_routing_from_keywords(monkeypatch, instruction, expected); async def test_explicit_domain_overrides_inference(monkeypatch); async def test_deterministic_workflow_runs_steps_not_orchestrator(monkeypatch); async def test_failing_execution_is_isolated(monkeypatch); async def test_no_due_workflows_is_noop(monkeypatch); async def test_active_execution_skips_dispatch(monkeypatch) … (+1)
  imports: app, pytest, sqlalchemy, unittest, uuid
  → usa: backend/app/workers/tasks_scheduler.py, backend/app/db/base.py, backend/app/db/models/models.py
`backend/tests/test_service_workflow_task.py` (python, 196 loc) — Tests para app.services.workflow.task…
  symbols: async def _tenant(db); class TestCleanupTasks {test_cleanup_marca_is_deleted_y_preserva_audit, test_cleanup_cancela_activas_y_las_oculta, test_cleanup_borra_pending_approvals, test_cleanup_idempotente_si_no_hay_tareas, test_cleanup_no_toca_tasks_de_otros_tenants}; class TestListAndGet {test_list_excluye_soft_deleted, test_get_404_si_soft_deleted}
  imports: app, datetime, pytest, uuid
  → usa: backend/app/db/models/models.py, backend/app/services/workflow/__init__.py
`backend/tests/test_service_workflow_task_runner.py` (python, 186 loc) — Tests para app.services.workflow.task_runner.TaskRunner…
  symbols: async def runner(); class TestTaskRunner {test_submit_lanza_task_y_registra, test_duplicado_se_ignora, test_cancel_detiene_tarea, test_cancel_de_inexistente_devuelve_false, test_cancel_de_task_ya_terminada_devuelve_false, test_is_running_y_active_count, test_submit_delayed_respeta_retardo, test_exception_en_tarea_dispara_mark_failed}
  imports: app, asyncio, pytest, unittest
  → usa: backend/app/services/workflow/task_runner.py
`backend/tests/test_service_workflow_ui_graph.py` (python, 279 loc) — Tests para app.services.workflow._ui_graph…
  symbols: def _emp(domain, name, is_builtin); class TestPerDomainInstruction {test_single_skill_devuelve_instruccion_recortada, test_multi_con_dominio_conocido_usa_directiva, test_multi_con_dominio_desconocido_fallback_a_recorte, test_master_None_single_devuelve_string_vacio, test_master_None_multi_aplica_directiva_aunque_no_haya_contexto, test_master_vacio_multi_sin_dominio_devuelve_vacio, test_todas_las_directivas_existen}; class TestPlanToUiGraph {test_plan_vacio_devuelve_solo_trigger, test_single_step_genera_trigger_y_step_conectados, test_step_sin_deps_se_conecta_a_trigger, test_dependencias_se_traducen_en_edges, test_capas_topologicas_posicionan_y_correctamente, test_trigger_label_se_resuelve, test_agent_desconocido_usa_titlecase_de_fallback, test_description_se_recorta_a_120}; class TestPickEmployee {test_lista_vacia_devuelve_None, test_custom_gana_sobre_builtin, test_solo_builtin_se_devuelve, test_sin_match_de_dominio_devuelve_None}; class TestSkillData {test_sin_employees_usa_default_label, test_con_custom_etiqueta_domain_custom, test_con_builtin_mantiene_domain_pero_label_real, test_multi_aplica_directiva_por_dominio, test_employees_None_no_crashea}; class TestGeneratePreviewNodes {test_payload_minimo_genera_trigger_y_un_skill, test_sin_keywords_detectadas_fallback_a_skill_generico, test_multi_dominio_anyade_consolidacion, test_employees_se_inyectan_en_skill_nodes, test_trigger_type_event_based, test_description_se_concatena_a_instruction_para_detectar, test_action_config_None_no_crashea}
  imports: app, types, uuid
  → usa: backend/app/services/workflow/_ui_graph.py
`backend/tests/test_signing_autofirma.py` (python, 226 loc) — Tests de la firma electrónica AutoFirma (F3.11)
  symbols: def test_build_uri_devuelve_uri_y_hash(); def test_build_uri_rechaza_documento_vacio(); def test_build_uri_rechaza_token_corto(); def test_build_uri_rechaza_algoritmo_no_soportado(); def test_build_uri_pades_marca_visibilidad_firma(); def test_parse_response_json_valido(); def test_parse_response_json_con_error_levanta(); def test_parse_response_string_base64(); def test_parse_response_bytes_directos(); def test_parse_response_tipo_no_soportado(); def test_extract_pades_detecta_firma(); def test_extract_pades_sin_firma() … (+5)
  imports: app, base64, json, pytest
  → usa: backend/app/services/signing/autofirma.py, backend/app/services/signing/sessions.py
`backend/tests/test_simulate_303.py` (python, 84 loc) — Tests del simulador Modelo 303 (UI.SIM) — datos ejemplo, sin BD
  symbols: class TestSimulate303 {test_devuelve_estructura_canonica, test_resultado_positivo_a_ingresar, test_totales_coherentes, test_iva_devengado_agrupa_por_tipo, test_iva_deducible_no_vacio, test_explanation_tiene_3_bullets, test_rechaza_trimestre_invalido, test_acepta_q1_q2_q3_q4}
  imports: app, pytest
  → usa: backend/app/services/onboarding/simulate_303.py
`backend/tests/test_skill_catalog_valid.py` (python, 29 loc) — El catálogo de skills de UI/provisioning debe ser 100% ejecutable…
  symbols: def test_every_ui_skill_resolves_to_a_real_tool(); def test_known_skills_match_labels()
  imports: app
  → usa: backend/app/agents/tool_registry.py, backend/app/services/ai/employee_crud.py
`backend/tests/test_state_machine.py` (python, 120 loc) — Tests para app.services.state_machine
  symbols: class TestInvoiceTransitions {test_draft_to_sent, test_draft_to_pending, test_draft_to_cancelled, test_sent_to_paid, test_pending_to_paid, test_sent_to_cancelled, test_paid_to_sent_unreconcile, test_paid_to_draft_not_allowed}; class TestPayrollTransitions {test_draft_to_approved, test_approved_to_paid, test_draft_to_rejected, test_paid_is_terminal}; class TestTaskTransitions {test_pending_to_planning, test_executing_to_done, test_executing_to_failed, test_done_is_terminal}; class TestCanTransition {test_valid_returns_true, test_invalid_returns_false}; class TestAllowedNextStates {test_draft_invoice, test_terminal_returns_empty}; class TestIsTerminal {test_cancelled_is_terminal, test_paid_is_not_terminal, test_draft_is_not_terminal}; class TestInvalidTransitionError {test_error_message_contains_info}
  imports: app, pytest
  → usa: backend/app/services/state_machine.py
`backend/tests/test_stream_tokens.py` (python, 130 loc) — Tests del helper de streaming token-a-token (UI.AGT v2)
  symbols: class FakeChunk {__init__, __add__}; class FakeLLM {__init__, astream, ainvoke}; class TestStreamLLM {test_sin_task_id_se_comporta_como_ainvoke, test_con_task_id_publica_tokens_al_hub, test_acumula_mensaje_final_correctamente, test_chunks_vacios_no_emiten_eventos, test_hub_caido_no_rompe_streaming}
  imports: app, asyncio, pytest
  → usa: backend/app/services/ai/stream_tokens.py, backend/app/services/workflow/task_event_hub.py
`backend/tests/test_structured_logging.py` (python, 106 loc) — Tests para `structured_logging` y `diagnostic_bundle` (CONT.LOG)
  symbols: class TestJSONFormatter {test_emite_json_line_valida, test_scrub_aplicado_a_mensaje, test_extra_se_serializa}; class TestGetLogDir {test_devuelve_path_existente}; class TestDiagnosticBundle {test_bundle_contiene_info_basica, test_bundle_zip_valido, test_endpoint_requiere_auth, test_endpoint_devuelve_zip}
  imports: app, httpx, io, json, logging, pytest, zipfile
  → usa: backend/app/core/structured_logging.py, backend/app/main.py, backend/app/services/system/diagnostic_bundle.py
`backend/tests/test_supplier_learning.py` (python, 213 loc) — Tests del aprendizaje OCR por proveedor (F2.5)
  symbols: def test_file_sha256_estable(); def test_diff_corrections_detecta_tax_uniforme(); def test_diff_corrections_no_propone_tax_si_no_uniforme(); def test_diff_corrections_detecta_renombrados_descripcion(); def test_diff_corrections_vacio_si_no_hay_cambios(); def test_apply_template_overrides_sin_template_no_modifica(); def test_apply_template_overrides_aplica_default_tax_si_falta(); def test_apply_template_overrides_renombra_descripcion(); def test_build_few_shot_block_vacio_si_no_hay_template(); def test_build_few_shot_block_con_extraccion_previa(); async def test_cache_roundtrip(db, seed_tenant_and_user); async def test_record_extraction_crea_template_y_actualiza_contador(db, seed_tenant_and_user) … (+2)
  imports: app, pytest
  → usa: backend/app/db/models/supplier_learning.py, backend/app/services/ocr/supplier_learning.py
`backend/tests/test_task_cost.py` (python, 161 loc) — Tests del agregador de coste por task (UI.COST)
  symbols: def _trace(); def _task(tenant_id, user_id); class TestTaskCost {test_task_inexistente_devuelve_status_none, test_task_sin_trazas_devuelve_ceros, test_agrega_tokens_y_eur, test_record_task_cost_trace_alimenta_el_resumen, test_record_task_cost_trace_ignora_cero_tokens, test_aislamiento_entre_tenants}
  imports: app, decimal, pytest, uuid
  → usa: backend/app/db/models/tasks.py, backend/app/services/ai/task_cost.py, backend/app/services/observability/__init__.py, backend/app/services/observability/agent_trace.py
`backend/tests/test_task_event_hub.py` (python, 86 loc) — Tests del TaskEventHub (UI.AGT — streaming SSE de progreso de tareas)
  symbols: class TestTaskEventHub {test_subscribe_recibe_eventos, test_publish_a_task_id_distinto_no_propaga, test_dos_suscriptores_misma_task_reciben_ambos, test_unsubscribe_limpia, test_signal_end_cierra_stream, test_stream_se_limpia_al_terminar, test_publish_sin_suscriptores_no_falla}
  imports: app, asyncio, pytest
  → usa: backend/app/services/workflow/task_event_hub.py
`backend/tests/test_tasks_orchestrator.py` (python, 246 loc) — Tests for tasks_orchestrator and its helpers in _orchestrator_state.py…
  symbols: def test_is_transient_returns_true(exc); def test_is_transient_returns_false(exc); async def tenant_with_employee_and_task(db); async def test_set_agent_status_updates_employee(db, tenant_with_employee_and_task); async def test_set_agent_status_silent_for_unknown_employee(db); async def test_save_final_state_persists_status_and_results(db, tenant_with_employee_and_task); async def test_save_final_state_sets_completed_only_for_terminal_states(db, tenant_with_employee_and_task); async def test_mark_task_failed_writes_error(tenant_with_employee_and_task); async def test_log_task_completion_creates_activity(db, tenant_with_employee_and_task); async def test_log_task_completion_marks_error_with_x(db, tenant_with_employee_and_task); async def test_execute_orchestrator_writes_token_ledger_for_employee_task(tenant_with_employee_and_task); async def test_execute_orchestrator_skips_cancelled_task(db, tenant_with_employee_and_task)
  imports: __future__, app, pytest, pytest_asyncio, sqlalchemy, unittest, uuid
  → usa: backend/app/db/models/ai_employees.py, backend/app/db/models/auth.py, backend/app/db/models/models.py, backend/app/workers/__init__.py
`backend/tests/test_telemetry_endpoint.py` (python, 84 loc) — Tests para el endpoint de telemetría (AI.REV)
  symbols: class TestTelemetryEndpoint {test_get_status_default_no_opted_out, test_revoke_marca_opted_out, test_revoke_idempotente, test_status_tras_revoke_devuelve_opted_out, test_endpoint_requiere_auth}
  imports: app, httpx, pytest, sqlalchemy
  → usa: backend/app/db/models/auth.py, backend/app/main.py
`backend/tests/test_telemetry_scrubber.py` (python, 138 loc) — Tests para `telemetry_scrubber` (AI.SCR)
  symbols: class TestScrubText {test_nif_se_redacta, test_nie_se_redacta, test_cif_se_redacta, test_iban_se_redacta, test_iban_con_espacios, test_email_se_redacta, test_tarjeta_se_redacta, test_ip_se_redacta}; class TestHashTenantId {test_determinista_con_misma_sal, test_sal_diferente_produce_hash_diferente, test_longitud_16_chars}; class TestScrubEvent {test_solo_campos_whitelisted_pasan, test_error_message_truncado_y_redactado, test_stack_trace_scrubbed, test_campos_whitelist_completa, test_evento_vacio_devuelve_dict_vacio, test_no_se_filtran_campos_no_string_whitelisted}
  imports: app
  → usa: backend/app/core/telemetry_scrubber.py
`backend/tests/test_tenant_context.py` (python, 117 loc) — Tests del ContextVar central de tenant en `app.core.tenant_context`…
  symbols: def _reset_context(); def test_set_get_roundtrip(); def test_require_raises_when_unset(); def test_require_returns_when_set(); def test_tenant_context_restores_previous(); def test_tenant_context_restores_on_exception(); async def test_concurrent_tasks_do_not_contaminate(); async def test_outer_context_isolated_from_gathered_tasks(); def test_alias_in_agents_module_shares_same_contextvar()
  imports: app, asyncio, pytest
  → usa: backend/app/core/tenant_context.py
`backend/tests/test_token_ledger_isolation.py` (python, 114 loc) — Cross-tenant isolation tests for TokenLedger queries…
  symbols: async def two_tenants_with_ledger(db); async def test_spend_returns_data_for_correct_tenant(db, two_tenants_with_ledger); async def test_spend_returns_zero_when_employee_id_belongs_to_other_tenant(db, two_tenants_with_ledger); async def test_ledger_returns_only_own_tenant_entries(db, two_tenants_with_ledger); async def test_ledger_returns_empty_for_other_tenant(db, two_tenants_with_ledger); async def test_ledger_aggregates_only_correct_tenant(db, two_tenants_with_ledger)
  imports: __future__, app, decimal, pytest, pytest_asyncio, sqlalchemy, uuid
  → usa: backend/app/db/models/ai_employees.py, backend/app/db/models/auth.py, backend/app/services/ai/employee_crud.py
`backend/tests/test_tool_session.py` (python, 26 loc) — Tests del hardening de tool_session() (RLS — defensa en profundidad)…
  symbols: async def test_tool_session_rejects_none(); async def test_tool_session_yields_session_with_tenant()
  imports: app, pytest, uuid
  → usa: backend/app/agents/shared/db.py
`backend/tests/test_tool_timeout.py` (python, 94 loc) — Tests del wrapper de timeout por tool…
  symbols: class _FakeTool {__init__}; async def test_async_tool_returns_normally_when_under_timeout(); async def test_async_tool_is_cancelled_when_exceeds_timeout(); async def test_sync_only_tool_is_not_modified(); async def test_apply_default_uses_override_for_known_tool(); async def test_apply_default_uses_default_for_unknown_tool()
  imports: app, asyncio
  → usa: backend/app/agents/tool_timeout.py
`backend/tests/test_treasury.py` (python, 202 loc) — Tests del motor de tesorería (F2.7): cashflow proyectado + SEPA pain.001
  symbols: async def test_projection_sin_movimientos_da_serie_plana(db, seed_tenant_and_user); async def test_projection_cuenta_cobros_emitidos(db, seed_tenant_and_user); async def test_projection_detecta_tension_liquidez(db, seed_tenant_and_user); async def test_projection_rechaza_horizonte_invalido(db, seed_tenant_and_user); def _basic_debtor(); def _basic_orders(n); def test_pain001_xml_estructura_basica(); def test_pain001_dos_transferencias_suma_control_sum(); def test_pain001_rechaza_iban_invalido(); def test_pain001_rechaza_importe_no_positivo(); def test_pain001_rechaza_fecha_pasada(); def test_pain001_rechaza_remesa_vacia() … (+2)
  imports: app, datetime, decimal, pytest, xml
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/treasury/projection.py, backend/app/services/treasury/sepa.py
`backend/tests/test_treasury_remittances.py` (python, 202 loc) — Tests de remesas SEPA persistidas: pain.008 + ciclo de estados
  symbols: def _creditor(); def _dd_order(seq, amount); def test_pain008_xml_estructura_basica(); def test_pain008_agrupa_pmtinf_por_secuencia(); def test_pain008_rechaza_secuencia_invalida(); def test_pain008_rechaza_sin_mandato(); def test_pain008_rechaza_fecha_pasada(); def test_pain008_rechaza_remesa_vacia(); def _transfer_orders(); async def test_remesa_pain001_se_persiste(db, seed_tenant_and_user); async def test_remesa_pain008_se_persiste_con_mandato(db, seed_tenant_and_user); async def test_ciclo_estados_remesa(db, seed_tenant_and_user) … (+2)
  imports: app, datetime, decimal, pytest, xml
  → usa: backend/app/services/treasury/remittances.py, backend/app/services/treasury/sepa.py
`backend/tests/test_verifactu_chain.py` (python, 302 loc) — Tests para la cadena hash Verifactu (FAC.HASH) — RD 1007/2023 Art…
  symbols: def _make_invoice(tenant_id, client_id); def _payload_alta(); class TestVectorOficialAEAT {test_cadena_canonica_coincide_con_el_ejemplo, test_huella_coincide_con_el_vector_oficial}; class TestBuildPayloadAlta {test_formato_determinista, test_orden_oficial_de_campos, test_huella_anterior_vacia_si_none, test_huella_anterior_encadenada, test_importe_2_decimales_insensible_a_ceros}; class TestBuildPayloadAnulacion {test_subconjunto_de_campos_anulacion}; class TestComputeHuella {test_es_sha256_hex_mayusculas, test_determinista, test_cambio_detectable}; class TestAppendVerifactuRecord {_setup_tenant_and_client, test_primer_registro_huella_anterior_es_none, test_segundo_registro_encadena_al_primero, test_idempotencia_no_duplica_para_misma_factura, test_cadenas_independientes_por_tenant, test_verify_chain_integrity_ok, test_verify_chain_integrity_detecta_manipulacion}; class TestMaybeAppendVerifactuRecord {test_modo_no_remission_no_crea_registro, test_modo_voluntary_si_crea_registro}
  imports: app, datetime, decimal, pytest, sqlalchemy
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/services/billing/verifactu_chain.py
`backend/tests/test_verifactu_chain_order.py` (python, 110 loc) — Tests del ordenamiento por enlace de la cadena Verifactu (FAC.HASH)…
  symbols: class _Rec {__init__}; def _chain(n); def test_ordena_por_enlace_no_por_orden_de_entrada(); def test_cadena_vacia_es_valida(); def test_un_solo_registro(); def test_genesis_con_string_vacio_equivale_a_none(); def test_eslabon_perdido_no_bien_formada(); def test_bifurcacion_no_bien_formada(); def test_multiple_genesis_no_bien_formada(); def test_ciclo_no_bien_formada(); def test_tail_de_cadena_lineal(); def test_tail_un_registro() … (+2)
  imports: app, random
  → usa: backend/app/services/billing/verifactu_chain.py
`backend/tests/test_verifactu_mode.py` (python, 92 loc) — Tests del modo de remisión Verifactu (FAC.MODE)
  symbols: class TestVerifactuMode {test_default_es_no_remission, test_get_config_idempotente, test_set_mode_voluntary, test_set_mode_alterna, test_set_mode_rechaza_invalido, test_should_remit_segun_modo, test_aislamiento_entre_tenants, test_to_dict_marca_is_default}
  imports: app, pytest, uuid
  → usa: backend/app/services/billing/verifactu_mode.py
`backend/tests/test_verifactu_registro_xml.py` (python, 170 loc) — VeriFactu — el XML RegistroAlta/Anulación valida contra el XSD oficial AEAT…
  symbols: def _make_record(num); def _invoice(); def _lines(); def test_alta_primer_registro_valida_xsd(); def test_alta_encadenado_valida_xsd(); def test_anulacion_valida_xsd(); def test_multiples_tipos_iva_generan_varios_detalles(); def test_huella_xml_coincide_con_payload(); def test_registro_anterior_sin_prev_record_falla(); def test_parse_payload_roundtrip(); def test_id_sistema_informatico_max_2_chars()
  imports: __future__, app, datetime, decimal, pathlib, pytest, types
  → usa: backend/app/services/billing/__init__.py, backend/app/services/billing/verifactu_chain.py
`backend/tests/test_verifactu_submit.py` (python, 244 loc) — Tests de la costura de envío VeriFactu (services/billing/verifactu_submit)…
  symbols: class TestParseAcuse {test_correcto, test_incorrecto, test_parcialmente_correcto_y_duplicado, test_soap_envuelto_y_prefijos, test_respuesta_irreconocible_lanza, test_xml_invalido_lanza}; class _FakeTransport {__init__, send}; def _patch(monkeypatch); class TestSubmitters {test_no_remission_es_noop, test_dry_run_no_carga_cert_ni_envia, test_confirmed_firma_y_envia, test_confirmed_sin_certificado_aborta, test_confirmed_firma_stub_no_envia, test_xml_invalido_aborta}; class TestFactory {test_no_remission_devuelve_noop, test_voluntary_devuelve_preproduccion}
  imports: app, pytest, types, uuid
  → usa: backend/app/services/aeat/certificate_storage.py, backend/app/services/aeat/xades_signer.py, backend/app/services/billing/__init__.py
`backend/tests/test_verify_endpoint.py` (python, 123 loc) — Tests para el endpoint público de verificación Verifactu (FAC.QR)
  symbols: def _make_invoice(tenant_id, client_id); async def _create_record(db, seed_tenant_and_user); class TestVerifyEndpoint {test_huella_invalida_devuelve_400, test_huella_inexistente_devuelve_404, test_huella_valida_devuelve_datos, test_endpoint_no_requiere_auth, test_huella_uppercase_se_normaliza}; class TestPdfQrBlock {test_pdf_con_verifactu_contiene_huella, test_pdf_sin_verifactu_funciona}
  imports: app, datetime, decimal, httpx, pytest
  → usa: backend/app/db/models/billing.py, backend/app/db/models/crm.py, backend/app/main.py, backend/app/services/billing/verifactu_chain.py
`backend/tests/test_workflow_conditions.py` (python, 130 loc) — Tests for workflow condition evaluator
  symbols: class TestLeafOperators {test_eq_true, test_eq_false, test_ne, test_gt, test_gt_false, test_gte_equal, test_lt, test_lte}; class TestCompoundOperators {test_and_all_true, test_and_one_false, test_or_one_true, test_or_all_false, test_not, test_nested}; class TestEdgeCases {test_none_condition_always_true, test_empty_condition_always_true, test_missing_field_eq_false, test_dot_notation, test_temporal_context_weekday}
  imports: app
  → usa: backend/app/services/workflow/conditions.py
`backend/tests/test_workflow_failure_alerts.py` (python, 94 loc) — Alertado de fallos de automatizaciones desatendidas (#5)…
  symbols: async def _seed_failed_execution(trigger_payload); async def _notifications(tenant_id); async def _is_notified(ex_id); async def test_scheduled_failure_notifies_gestor(); async def test_manual_failure_not_notified(); async def test_sweep_is_idempotent()
  imports: app, sqlalchemy, uuid
  → usa: backend/app/db/base.py, backend/app/db/models/models.py, backend/app/db/models/notifications.py, backend/app/workers/tasks_scheduler.py
`backend/tests/test_workflow_marketplace.py` (python, 177 loc) — Tests del marketplace de workflows (F3.10)
  symbols: async def test_seed_official_idempotente(db, seed_tenant_and_user); async def test_list_templates_devuelve_oficiales(db, seed_tenant_and_user); async def test_list_templates_filtra_por_categoria(db, seed_tenant_and_user); async def test_get_template_devuelve_none_si_no_existe(db, seed_tenant_and_user); async def test_install_template_crea_workflow_inactivo(db, seed_tenant_and_user); async def test_install_template_sufija_si_nombre_existe(db, seed_tenant_and_user); async def test_install_template_incrementa_downloads(db, seed_tenant_and_user); async def test_install_template_no_existente_da_value_error(db, seed_tenant_and_user); def _make_wf(tenant_id, name); def test_export_workflow_to_yaml_parseable(); async def test_roundtrip_export_import(db, seed_tenant_and_user); async def test_import_rechaza_yaml_invalido(db, seed_tenant_and_user) … (+2)
  imports: app, pytest, uuid, yaml
  → usa: backend/app/db/models/workflows.py, backend/app/services/workflow_marketplace/__init__.py
`backend/tests/test_zernio_client.py` (python, 101 loc) — Tests del cliente REST de Zernio (httpx MockTransport, sin red real)…
  symbols: def _client(handler); def test_create_post_publish_now_envia_contrato_correcto(); def test_list_accounts_desempaqueta_data(); def test_connect_url_devuelve_authurl(); def test_error_429_es_transient(); def test_error_400_no_es_transient(); def test_disconnect_account_hace_delete(); def test_api_key_obligatoria()
  imports: app, asyncio, httpx, json, pytest
  → usa: backend/app/services/marketing/zernio_client.py
`backend/tests/test_zernio_publisher.py` (python, 69 loc) — Tests de `ZernioPublisher._do_publish` (sin BD: cuenta y cliente inyectados)…
  symbols: def _client(handler); def _post(); def test_publish_ok_marca_published(); def test_publish_sin_cuenta_falla_no_transient(); def test_publish_429_es_transient(); def test_publish_400_no_transient()
  imports: app, asyncio, httpx, types
  → usa: backend/app/db/models/marketing.py, backend/app/services/marketing/zernio_client.py, backend/app/services/marketing/zernio_publisher.py
`backend/tests/test_zernio_state.py` (python, 24 loc) — Test del state cifrado URL-safe del flujo de conexión vía Zernio…
  symbols: def test_state_roundtrip_y_url_safe(); def test_state_manipulado_falla()
  imports: app, pytest, uuid
  → usa: backend/app/api/v1/routes/marketing.py

## dependencies/  (1 archivos)
`dependencies/embedded_binaries.json` (json, 34 loc)
  symbols: key: $schema; key: _doc; key: binaries

## desktop/  (39 archivos)
`desktop/.claude/settings.local.json` (json, 15 loc)
  symbols: key: permissions
`desktop/afterPack.js` (js, 3 loc) — electron-builder gestiona el ícono nativamente via build.win.icon
`desktop/docs/a11y_audit.md` (markdown, 143 loc) — Auditoría de accesibilidad — U.6 / QA.AXE
  symbols: # Auditoría de accesibilidad — U.6 / QA.AXE; ## §1 Marco normativo aplicable; ## §2 Gate automatizado (axe-core); ### §2.1 Suite local; ### §2.2 CI; ### §2.3 Componentes cubiertos a 2026-05-14; ## §3 Auditoría manual con NVDA — procedimiento para fundador; ### §3.1 Instalación (10 min); ### §3.2 Checklist por flujo (2h sesión); ### §3.3 Registro de la auditoría; ## §4 Reglas de regresión; ## §5 Excepciones documentadas
`desktop/docs/aeat_modelos_alcance.md` (markdown, 63 loc) — Modelos AEAT — alcance MVP y roadmap (AEAT.4)
  symbols: # Modelos AEAT — alcance MVP y roadmap (AEAT.4); ## §1 Modelos generados y presentables en MVP v1; ## §2 Modelos en roadmap (v1.1, Q4-2026); ## §3 Modelos NO cubiertos por AutomatizaCore; ## §4 Limitaciones declaradas al cliente; ## §5 Recomendación para casos complejos
`desktop/docs/ai_act_eula_clause.md` (markdown, 84 loc) — Cláusula AI Act para EULA — AI.EULA
  symbols: # Cláusula AI Act para EULA — AI.EULA; ## Cláusula X — Sistema de Inteligencia Artificial; ### X.1 Naturaleza del sistema; ### X.2 Distribución de responsabilidades; ### X.3 Sistemas de alto riesgo y excepciones; ### X.4 Limitación de responsabilidad; ### X.5 Datos personales (RGPD); ### X.6 Modificación de la cláusula; ## Notas internas (no parte del EULA del cliente)
`desktop/docs/ai_act_governance.md` (markdown, 106 loc) — Gobernanza de prompts y datos — AI.GOV
  symbols: # Gobernanza de prompts y datos — AI.GOV; ## §1 Prompts versionados en repositorio; ### Ubicación canónica; ### Trazabilidad por ejecución; ### Política de cambio de prompt; ## §2 Datos de entrenamiento; ### Datos few-shot enviados al LLM; ### Memoria conversacional; ## §3 Supervisión humana (Art. 14); ## §4 Registro de incidentes AI Act; ## §5 Tabla resumen de cumplimiento; ## §6 Revisión periódica
`desktop/docs/ai_act_info_trabajadores.md` (markdown, 88 loc) — Información a representantes de trabajadores — AI.WRK
  symbols: # Información a representantes de trabajadores — AI.WRK; ## Plantilla de comunicación a trabajadores (versión 1.0); ### Notificación sobre el uso de un sistema de Inteligencia Artificial en el entorno laboral; ## Notas para el equipo de AutomatizaCore
`desktop/docs/ai_act_scoping.md` (markdown, 153 loc) — AI Act Scoping Memo — AutomatizaCore MVP
  symbols: # AI Act Scoping Memo — AutomatizaCore MVP; ## §1 Resumen ejecutivo; ## §2 Clasificación por agente; ### Agentes high-risk Anexo III (4) "Empleo, gestión de trabajadores"; ### Agentes limited risk (transparencia Art. 50); ### Agentes minimal risk; ## §3 Análisis especial — `crm.qualify_leads`; ### Evidencia; ### Clasificación AI Act; ### Acción; ## §4 Columnas DB AI Act-related; ## §5 Obligaciones Art. 26 (deployer) que asume el cliente
`desktop/docs/analisis-proyecto-mercado.md` (markdown, 596 loc) — AutomatizaCore — Analisis Exhaustivo del Proyecto y Proyeccion de Mercado
  symbols: # AutomatizaCore — Analisis Exhaustivo del Proyecto y Proyeccion de Mercado; ## 1. RESUMEN EJECUTIVO; ## 2. ANALISIS TECNICO DEL PRODUCTO; ### 2.1 Arquitectura de Agentes (3 Capas) — El Diferenciador Central; ### 2.2 Sistema de Workflows Hibridos (Automatizaciones); ### 2.3 Empleados IA con Skills — La Capa de Personalizacion; ### 2.4 Budget Guard — Control de Costes; ### 2.5 Sandbox; ### 2.6 Modulos ERP Completos (30+ paginas); ### 2.7 Integraciones; ### 2.8 Multi-Proveedor LLM; ## 3. ANALISIS COMPETITIVO
`desktop/docs/auto_update_guide.md` (markdown, 212 loc) — Auto-update con electron-updater (DIS.UPD)
  symbols: # Auto-update con electron-updater (DIS.UPD); ## §1 Lifecycle; ## §2 Canales; ### Cómo publicar en cada canal; ## §3 Delta updates; ## §4 Publish (estado 2026-06-12); ## §5 Code signing (cross-ref DIS.SIG); ### Cómo firmar cuando haya certificado; # .pfx en base64 o ruta al fichero; ## §6 IPC bridge expuesto al renderer; ## §7 Componentes UI; ## §8 Tests
`desktop/docs/autonomy_gate_guide.md` (markdown, 137 loc) — Autonomy gate — guía de integración (AI.AGT wiring)
  symbols: # Autonomy gate — guía de integración (AI.AGT wiring); ## El gate en una frase; ## Dominios que deben gatearse; ## Patrón canónico (Python); ## Tres respuestas estándar; ## Errores comunes; ### 1. Llamar al gate **después** de la acción; ### 2. Ignorar la decisión MANUAL; ### 3. Persistir aprobación sin `task_id`; ### 4. No gatear tools "obviamente seguras"; ## Decisión MANUAL: ¿qué muestra el usuario?; ## Logs y observabilidad
`desktop/docs/ci_quality_gates.md` (markdown, 115 loc) — Gates de calidad en CI (QA.CI)
  symbols: # Gates de calidad en CI (QA.CI); ## §1 Pinning de versión Python; ## §2 Mypy estricto en agents/ y services/; ## §3 Coverage backend ≥ 70%; ## §4 Coverage frontend ≥ 20% (target 40%); ## §5 Job a11y bloqueante; ## §6 Excepciones documentadas; ## §7 Cómo desactivar localmente un gate (uso excepcional); ## §8 Métricas de la ejecución; ## §9 Próximos gates a añadir (post-MVP)
`desktop/docs/db_hooks_guide.md` (markdown, 121 loc) — Hooks de BD — drift detection + pre-commit (ALB.2 / ALB.6)
  symbols: # Hooks de BD — drift detection + pre-commit (ALB.2 / ALB.6); ## ALB.2 · Drift detection BD vs modelos; ### Cuándo usar; ### Cómo correrlo; # o contra una BD remota:; # En CI, con código de salida:; ### Salida; ### Limitaciones conscientes; ## ALB.6 · Pre-commit hook: migración obligatoria si tocas modelos; ### Qué hace; ### Instalación local; # ALB.6 — migration check
`desktop/docs/dependency_security.md` (markdown, 81 loc) — Seguridad de dependencias — DIS.DEP
  symbols: # Seguridad de dependencias — DIS.DEP; ## §1 Escaneo automático — Dependabot; ## §2 SCA en CI — OSV-Scanner; ## §3 Política de versiones; ### Pinning; ### Excepciones; ## §4 SBOM por release; ## §5 Verificación de binarios embebidos; ## §6 Periodicidad de revisión
`desktop/docs/desktop_service_guide.md` (markdown, 153 loc) — Backend como servicio + tray persistente (DIS.SVC)
  symbols: # Backend como servicio + tray persistente (DIS.SVC); ## §1 Decisión de diseño: Electron host, no SCM; ## §2 Lifecycle; ## §3 Supervisor de backend; ### Backoff defaults; ### Stop limpio vs crash; ### Integración con install-update; ## §4 Tray contextual; ## §5 Diagnóstico; ## §6 Tests; ## §7 macOS / Linux
`desktop/docs/empty_states_guide.md` (markdown, 81 loc) — Catálogo de empty states productivos — UI.EMP
  symbols: # Catálogo de empty states productivos — UI.EMP; ## Componentes disponibles; ## Reglas de copy; ## Catálogo por dominio; ## Ejemplo de uso (ui/EmptyState); ## Migración de las páginas existentes; ## Próximas iteraciones
`desktop/docs/incident_response_fiscal.md` (markdown, 105 loc) — Runbook incidente fiscal del cliente — OPS.RUN
  symbols: # Runbook incidente fiscal del cliente — OPS.RUN; ## §1 Personas designadas; ## §2 Plazos clave; ## §3 Recopilación de evidencia técnica; ## §4 Análisis de responsabilidad; ### Escenario A — Bug del software (responsabilidad del proveedor); ### Escenario B — Datos del cliente incorrectos (responsabilidad del cliente); ### Escenario C — Aprobación humana omitida o saltada (responsabilidad compartida); ### Escenario D — Cambio normativo posterior (responsabilidad mitigada); ## §5 Comunicación al cliente; ### Plantilla de acuse inicial (24h); ### Plantilla de análisis completado (10 días)
`desktop/docs/monitoring_aeat.md` (markdown, 62 loc) — Monitorización portal AEAT — CONT.MON
  symbols: # Monitorización portal AEAT — CONT.MON; ## §1 Fuentes oficiales (suscripción obligatoria); ### Portal AEAT — Novedades técnicas; ### BOE — Sumario diario; ### Documentación Verifactu — versión vigente; ## §2 Procedimiento de respuesta; ## §3 Buffer técnico en sprint; ## §4 Calendario interno; ## §5 Runbook expreso si AEAT publica un breaking change crítico durante un sprint comprometido
`desktop/docs/multitenancy/tenant_scoped_tables.md` (markdown, 328 loc) — Auditoría Multi-Tenancy — Fase 1
  symbols: # Auditoría Multi-Tenancy — Fase 1; ## 0. Verificación posterior (2026-05-02 — fuente de verdad); ### 0.1 Hallazgo confirmado tras auditoría detallada; ### 0.2 Lecciones; ## 1. Resumen ejecutivo; ## 2. Tablas tenant-scoped (26 modelos); ## 3. Tablas globales; ### 3.1 Sistema de tenants (3 modelos); ### 3.2 Auth compartido (1 modelo); ### 3.3 Catálogo / configuración global (1 modelo); ### 3.4 Sospechosas (deberían tener tenant_id); ## 4. Queries potencialmente vulnerables
`desktop/docs/oauth_proxy.md` (markdown, 138 loc) — Proxy OAuth en el servidor (Render) — contrato
  symbols: # Proxy OAuth en el servidor (Render) — contrato; ## Activación; ## Endpoints que debe exponer Render; ### `POST /oauth/exchange`; ### `POST /oauth/fb-longtoken`; ### `GET /oauth/cb` — rebote HTTPS → callback local; ## Flujo completo de conexión (redes sociales); ## Alta en el panel de cada red (checklist); ### Facebook / Instagram (developers.facebook.com); ### X (Twitter) y LinkedIn; ## Seguridad del proxy; ## Google (Gmail + Drive) — NO usa proxy, usa PKCE
`desktop/docs/observability/langfuse.md` (markdown, 84 loc) — Activar Langfuse (trazabilidad LLM)
  symbols: # Activar Langfuse (trazabilidad LLM); ## Setup (~5 min); ### 1. Cuenta gratis en Langfuse Cloud; ### 2. Instalar el paquete en el venv; # o, con poetry:; ### 3. Añadir las keys al `.env` del backend; # Opcional, default es cloud.langfuse.com:; ### 4. Reiniciar backend; ## Cómo se integra (sin tocar agentes); ## Verificar que funciona; ## Desactivar; ## Coste
`desktop/docs/sbom_guide.md` (markdown, 120 loc) — SBOM CycloneDX — guía operacional (DIS.SBOM)
  symbols: # SBOM CycloneDX — guía operacional (DIS.SBOM); ## §1 Generar el SBOM; ## §2 Manifest de binarios embebidos; ### Verificación pre-release; ## §3 Integración con releases GitHub; ## §4 Consumo externo; ## §5 Actualización del manifest embebido; ## §6 Política de divulgación; ## §7 Tests
`desktop/docs/sla_tiers.md` (markdown, 77 loc) — SLA por tier — OPS.SLA
  symbols: # SLA por tier — OPS.SLA; ## §1 Tiers; ### Solo — 39€/mes; ### Pro — 65€/mes; ### Gestoría — 159€/mes; ## §2 Definición de "horas hábiles"; ## §3 Definición de "incidencia"; ## §4 Procedimiento de escalado; ## §5 Compensaciones por incumplimiento; ## §6 Integración Crisp chat (referencia)
`desktop/docs/telemetry-data-policy.md` (markdown, 109 loc) — Política de datos de telemetría — AutomatizaCore
  symbols: # Política de datos de telemetría — AutomatizaCore; ## §1 Promesa al usuario; ## §2 Whitelist de campos enviados; ## §3 Retención (AI.RET); ## §4 Revocación (AI.REV); ## §5 Salt por incidente; ## §6 Base jurídica; ## §7 Punto de contacto
`desktop/docs/ui_polish_guide.md` (markdown, 157 loc) — UI polish guide — patrones canónicos (UI.POL)
  symbols: # UI polish guide — patrones canónicos (UI.POL); ## §1 Encabezado de página; ## §2 Botones y CTAs; ## §3 Espaciado y layout; ## §4 Empty states; ## §5 Loading states; ## §6 Modales / dialogs; ## §7 Iconografía; ## §8 Colores semánticos; ## §9 Tablas; ## §10 Antipatrones a evitar; ## §11 Aplicación incremental
`desktop/jre-manager.js` (js, 172 loc) — Gestor de Java JRE portable — descarga auto en primera ejecución…
  symbols: function logDebug; function isJREInstalled; function getJavaPath; function downloadJRE; function downloadFile
  imports: child_process, fs, http, https, os, path
`desktop/launch.js` (js, 29 loc) — Launcher que limpia ELECTRON_RUN_AS_NODE antes de arrancar Electron…
  imports: child_process, electron, path
`desktop/lib/update-channel.js` (js, 75 loc) — DIS.UPD — gestor del canal de actualización (stable | beta)…
  symbols: function normalize; function createUpdateChannelManager; function getChannel; function setChannel; function apply
`desktop/main.js` (js, 449 loc) — true = backend en 0.0.0.0 (LAN); false = solo 127.0.0.1
  symbols: function secureStoreFilePath; function isSecureStoreAvailable; function _loadElectronStore; function _ensureUpdateChannelMgr; function setupAutoUpdater; function createSplash; function splashStatus; function createMainWindow; function startup
  imports: electron, electron-updater, fs, path
  → usa: desktop/service-manager.js, desktop/python-manager.js, desktop/network-utils.js, desktop/tray-manager.js, desktop/lib/update-channel.js
`desktop/network-utils.js` (js, 38 loc) — Devuelve la primera IPv4 no-interna (IP de LAN)
  symbols: function getLanIP; function getAccessURLs
  imports: os
`desktop/package-lock.json` (json, 3957 loc) — package 'automatizacore-desktop', 0 deps
  symbols: key: name; key: version; key: lockfileVersion; key: requires; key: packages
`desktop/package.json` (json, 103 loc) — package 'automatizacore-desktop', 6 deps; scripts: start, generate-icon, predist, dist, sync, sync:rebuild
  symbols: key: name; key: version; key: description; key: author; key: license; key: main; key: scripts; key: dependencies; key: devDependencies; key: build
`desktop/postgres-manager.js` (js, 363 loc) — Verifica si PostgreSQL portable ya está descargado
  symbols: function logDebug; function isPostgresInstalled; function downloadPostgres; function initDatabase; function startPostgres; function stopPostgres; function isPostgresRunning; function waitForPostgres; function createDatabase; function getDatabaseURL; function getAdminDatabaseURL; function downloadFile
  imports: child_process, fs, http, https, net, os, path
`desktop/preload.js` (js, 33 loc)
  imports: electron
`desktop/python-manager.js` (js, 501 loc) — Verifica si Python embebido está instalado
  symbols: function logPython; function isPythonInstalled; function areDepsInstalled; function downloadPython; function installDeps; function startBackend; function requestGracefulShutdown; function stopBackend; function runMigrations; function downloadFile
  imports: child_process, crypto, electron, fs, http, https, os, path
  → usa: desktop/postgres-manager.js
`desktop/sanitize-env.js` (js, 85 loc) — sanitize-env.js — genera `.env.dist` saneado para empaquetar (predist)…
  symbols: function isDenied; function main
  imports: fs, path
`desktop/service-manager.js` (js, 657 loc) — Gestor de servicios nativos — reemplaza docker-manager.js…
  symbols: function logBoot; function loadDotEnv; function envVar; function killOrphanProcesses; function getOrCreateSecrets; function getBackendEnv; function runSpawn; function startFrontend; function stopFrontend; function waitForHTTP; function startAll; function stopAll
  imports: child_process, crypto, electron, fs, http, os, path
  → usa: desktop/postgres-manager.js, desktop/python-manager.js, desktop/jre-manager.js, desktop/network-utils.js
`desktop/sync.js` (js, 176 loc) — sync.js — Sincroniza backend/frontend del proyecto al app instalada…
  symbols: function log; function warn; function error; function fileHash; function shouldIgnore; function syncDir; function main
  imports: child_process, crypto, fs, os, path
`desktop/tray-manager.js` (js, 114 loc) — Crea el icono en la bandeja del sistema con menú contextual…
  symbols: function createTray; function updateTooltip; function destroyTray
  imports: electron, path

## docs/  (7 archivos)
`docs/architecture/information-flow.md` (markdown, 373 loc) — Flujo de información en AutomatizaCore
  symbols: # Flujo de información en AutomatizaCore; ## 1. Resumen ejecutivo; ## 2. Diagrama de flujo (Mermaid); ## 3. Dimensiones del flujo de información; ### 3.1 Acoplamiento a nivel de datos (Foreign Keys cross-dominio); ### 3.2 Eventos de dominio y triggers (event bus); ### 3.3 Llamadas cross-módulo entre servicios; ### 3.4 Flujo de datos en runtime de la capa de agentes; ### 3.5 Pipeline de información documental (RAG / embeddings); ### 3.6 Propagación de contexto de tenant y aislamiento; ### 3.7 Distribución de información backend → frontend; ### 3.8 Distribución de trabajo por automatizaciones/workflows
`docs/guia-piloto.md` (markdown, 48 loc) — AutomatizaCore — Guía rápida de instalación (piloto)
  symbols: # AutomatizaCore — Guía rápida de instalación (piloto); ## 1. Instalar; ## 2. Crear tu cuenta; ## 3. Configurar lo esencial (Primeros pasos); ## 4. (Opcional) Integraciones; ## 5. Probar (5 minutos); ## Bueno saber
`docs/marketing-zernio-setup.md` (markdown, 86 loc) — Conecta tus redes sociales (Zernio)
  symbols: # Conecta tus redes sociales (Zernio); ## Resumen (≈5 minutos); ## Paso 1 · Crea tu cuenta de Zernio (gratis); ## Paso 2 · Consigue tu API key; ## Paso 3 · Añádela en AutomatizaCore; ## Paso 4 · Conecta tus redes; ## Truco · Conecta más de 2 redes gratis; ## Paso 5 · Publica; ## Problemas frecuentes; ## Seguridad
`docs/oauth-social-setup.md` (markdown, 124 loc) — Configuración OAuth — Redes Sociales
  symbols: # Configuración OAuth — Redes Sociales; ## Variables de entorno necesarias (`.env` del backend); # URL de callback — debe coincidir exactamente con lo registrado en cada plataforma; # Proxy OAuth/imágenes (opcional). Si se define, registra {OAUTH_PROXY_URL}/oauth/cb; # como redirect en lugar del callback local.; # Instagram / Facebook (una sola app Meta cubre ambas); # LinkedIn; # Twitter / X; ## 1. Meta (Instagram + Facebook); ## 2. LinkedIn; ## 3. Twitter / X; ## Flujo técnico
`docs/parametros-fiscales-actualizacion.md` (markdown, 60 loc) — Parámetros fiscales y su actualización cuando la AEAT cambia
  symbols: # Parámetros fiscales y su actualización cuando la AEAT cambia; ## 1. Lo que YA se actualiza solo; ## 2. Parámetros versionados por año (revisar cada enero / cuando el BOE cambie); ## 3. Por qué NO scrapeamos los tipos automáticamente; ## 4. Checklist de revisión anual (enero)
`docs/remote-access-cloudflare.md` (markdown, 134 loc) — Acceso remoto vía Cloudflare Tunnel — Fase 1
  symbols: # Acceso remoto vía Cloudflare Tunnel — Fase 1; ## Topología; ## Lo que YA está preparado en el código (Fase 1); ## Requisitos previos; ## Paso a paso (túnel con nombre); ## Cloudflare Access — el front-door de seguridad (OBLIGATORIO); ## Validación end-to-end (hazla TÚ antes de dar la URL al cliente); ## Pendiente antes de dar de alta a los ~10 empleados (Fase 1.5); ## Fase 2 (solo si llega un 2º cliente)
`docs/rollout-autonomy-gate.md` (markdown, 98 loc) — Rollout del autonomy gate a las acciones consecuentes
  symbols: # Rollout del autonomy gate a las acciones consecuentes; ## Patrón de referencia (ya aplicado: agente de stock); ## Pendiente de aplicar (mismo patrón); ### 1. email.send_email (dominio `email`) — PRIORIDAD ALTA; ### 2. documents.import_invoice_document (dominio `documents`) — PRIORIDAD ALTA; ### 3. hr.generate_all_payrolls (dominio `hr`) — MEDIA; ### 4. excel.import_excel / modify_excel — MEDIA; ### 5. billing.send_invoice_by_email / update_invoice_status(anular) — MEDIA; ## Checklist por acción

## frontend/  (608 archivos)
`frontend/components.json` (json, 20 loc)
  symbols: key: $schema; key: style; key: rsc; key: tsx; key: tailwind; key: aliases
`frontend/e2e/README.md` (markdown, 69 loc) — E2E Tests — Playwright (QA.E2E)
  symbols: # E2E Tests — Playwright (QA.E2E); ## Estructura; ## Cómo correrlo; ### Primera vez (descargar Chromium ~170MB); ### Ejecutar tests; ### Pre-requisitos para `happy-path.spec.ts` (cuando se active); ## CI; ## Próximos pasos (TODO)
`frontend/e2e/happy-path.spec.ts` (ts, 35 loc) — Happy path E2E (QA.E2E): signup → factura → Verifactu QR → simulación 303…
  imports: @playwright/test
`frontend/e2e/smoke.spec.ts` (ts, 36 loc) — Smoke tests E2E — sin dependencia de backend…
  imports: @playwright/test
`frontend/middleware.ts` (ts, 34 loc) — Middleware de autenticación: protege todas las rutas del dashboard…
  symbols: export function middleware; export const config
  imports: next
`frontend/next-env.d.ts` (ts, 7 loc) — / <reference types="next" />
`frontend/next.config.js` (js, 28 loc) — @type {import('next').NextConfig}
  imports: next-intl
`frontend/package-lock.json` (json, 12804 loc) — package 'automatizacion-frontend', 0 deps
  symbols: key: name; key: version; key: lockfileVersion; key: requires; key: packages
`frontend/package.json` (json, 81 loc) — package 'automatizacion-frontend', 55 deps; scripts: dev, build, start, lint, test, test:ci, test:ui, test:a11y
  symbols: key: name; key: version; key: private; key: author; key: license; key: scripts; key: dependencies; key: devDependencies; key: overrides
`frontend/playwright.config.ts` (ts, 48 loc) — Playwright E2E config (QA.E2E)…
  imports: @playwright/test
`frontend/postcss.config.js` (js, 9 loc)
`frontend/src/__probe.ts` (ts, 11 loc)
  imports: @/lib
  → usa: frontend/src/lib/api/analytics.ts, frontend/src/lib/api.ts
`frontend/src/__tests__/update-channel.test.ts` (ts, 136 loc) — Tests del gestor de canal de actualización (DIS.UPD)…
  symbols: function makeStore; function makeAutoUpdater
  imports: vitest
  → usa: desktop/lib/update-channel.js
`frontend/src/app/(auth)/__tests__/login.test.tsx` (tsx, 124 loc)
  imports: @/test-utils, vitest
  → usa: frontend/src/test-utils/render.tsx, frontend/src/app/(auth)/login/page.tsx
`frontend/src/app/(auth)/aceptar-invitacion/[token]/page.tsx` (tsx, 215 loc)
  symbols: export function AceptarInvitacionPage; function handleSubmit; function Field
  imports: @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/client.ts
`frontend/src/app/(auth)/error.tsx` (tsx, 45 loc)
  symbols: export function AuthError
  imports: @/lib, next, next-intl, react
  → usa: frontend/src/lib/error-reporter.ts
`frontend/src/app/(auth)/forgot-password/page.tsx` (tsx, 105 loc)
  symbols: export function ForgotPasswordPage; function handleSubmit
  imports: @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(auth)/login/page.tsx` (tsx, 251 loc)
  symbols: export function LoginPage; function NeuralBackground; function handleSubmit
  imports: @/components, @/lib, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/client.ts, frontend/src/components/ui/logo-svg.tsx
`frontend/src/app/(auth)/registro/page.tsx` (tsx, 249 loc)
  symbols: export function RegistroPage; function NeuralBackground; function handleChange; function handleSubmit
  imports: @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(auth)/reset-password/page.tsx` (tsx, 138 loc)
  symbols: export function ResetPasswordPage; function ResetPasswordForm; function handleSubmit
  imports: @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/_components/AiActivitySection.tsx` (tsx, 52 loc)
  symbols: export function AiActivitySection
  imports: @/lib, lucide-react, next, next-intl
  → usa: frontend/src/app/(dashboard)/_components/DashboardBadges.tsx, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/_components/AiChatBar.tsx` (tsx, 163 loc)
  symbols: export function AiChatBar; function send
  imports: @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/_components/TaskProgressPipeline.tsx
`frontend/src/app/(dashboard)/_components/AiInsightsSection.tsx` (tsx, 67 loc)
  symbols: export function AiInsightsSection
  imports: lucide-react, next, next-intl
`frontend/src/app/(dashboard)/_components/ApprovalsSection.tsx` (tsx, 53 loc)
  symbols: export function ApprovalsSection
  imports: @/lib, lucide-react, next, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/_components/CashflowChart.tsx` (tsx, 48 loc)
  symbols: export function CashflowChart
  imports: lucide-react, next-intl, recharts
`frontend/src/app/(dashboard)/_components/DashboardBadges.tsx` (tsx, 48 loc)
  symbols: export function StatusBadge; export function InvBadge
  imports: next-intl
`frontend/src/app/(dashboard)/_components/IntegrationsWidget.tsx` (tsx, 141 loc)
  symbols: export function IntegrationsWidget
  imports: @/lib, lucide-react, next, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/_hooks/useDashboard.ts
`frontend/src/app/(dashboard)/_components/KpiSection.tsx` (tsx, 68 loc)
  symbols: export function KpiSection
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/_components/LiveTeamSection.tsx` (tsx, 288 loc)
  symbols: export function LiveTeamSection; function EmployeeNode
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/app/(dashboard)/_hooks/useLiveTeam.ts, frontend/src/lib/api/ai_employees.ts
`frontend/src/app/(dashboard)/_components/MorningBrief.tsx` (tsx, 273 loc)
  symbols: export function MorningBrief; function accentClasses; function computeBrief; function formatMinutes
  imports: @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/_components/RecentInvoicesSection.tsx` (tsx, 70 loc)
  symbols: export function RecentInvoicesSection
  imports: @/lib, lucide-react, next, next-intl
  → usa: frontend/src/app/(dashboard)/_components/DashboardBadges.tsx, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/_components/RrhhWidget.tsx` (tsx, 122 loc)
  symbols: export function RrhhWidget
  imports: @/components, @/lib, lucide-react, next, next-intl
  → usa: frontend/src/components/ui/card.tsx, frontend/src/components/ui/badge.tsx, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/_components/TaskProgressPipeline.tsx` (tsx, 184 loc)
  symbols: export function TaskProgressPipeline
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/hooks/useNotificationSocket.ts
`frontend/src/app/(dashboard)/_components/TimeSavedCard.tsx` (tsx, 112 loc) — Widget "Tiempo ahorrado por la IA" del centro de mando…
  symbols: export function TimeSavedCard; function formatTime
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/metrics.ts, frontend/src/lib/api/errors.ts
`frontend/src/app/(dashboard)/_components/UsageWidget.tsx` (tsx, 112 loc) — Widget de consumo de IA del mes en curso…
  symbols: export function UsageWidget
  imports: @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api/llm_usage.ts, frontend/src/lib/api/errors.ts
`frontend/src/app/(dashboard)/_hooks/useDashboard.ts` (ts, 132 loc)
  symbols: export function useDashboard; function decodeJwtName
  imports: @/lib, @/stores, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/client.ts, frontend/src/stores/notifications.ts
`frontend/src/app/(dashboard)/_hooks/useLiveTeam.ts` (ts, 142 loc) — Domains con actividad reciente — para iluminar avatares aunque el backend no haya emitido agent_status_changed (ocurre con prompts sin addre…
  symbols: export function useLiveTeam
  imports: @/lib, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/ai_employees.ts, frontend/src/lib/hooks/useNotificationSocket.ts
`frontend/src/app/(dashboard)/actividades/page.tsx` (tsx, 6 loc)
  symbols: export function ActividadesRedirect
  imports: next
`frontend/src/app/(dashboard)/albaranes/_components/AlbaranModal.tsx` (tsx, 107 loc)
  symbols: export function AlbaranModal
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/albaranes/_hooks/useAlbaranes.ts
`frontend/src/app/(dashboard)/albaranes/_hooks/useAlbaranes.ts` (ts, 122 loc)
  symbols: export const emptyLine; export const STATUS_COLORS; export const fmt; export function useAlbaranes
  imports: @/lib, @/stores, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/client.ts, frontend/src/lib/api/albaranes.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/albaranes/page.tsx` (tsx, 147 loc)
  symbols: export function AlbaranesPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/albaranes/_hooks/useAlbaranes.ts, frontend/src/app/(dashboard)/albaranes/_components/AlbaranModal.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/alertas/page.tsx` (tsx, 176 loc)
  symbols: export function AlertasPage
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/shared/KpiCard.tsx, frontend/src/stores/toast.ts, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/analitica/_components/AgingTable.tsx` (tsx, 69 loc)
  symbols: export function AgingTable
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/analitica/_components/utils.ts
`frontend/src/app/(dashboard)/analitica/_components/CustomTooltip.tsx` (tsx, 26 loc)
  symbols: export const CustomTooltip
  → usa: frontend/src/app/(dashboard)/analitica/_components/utils.ts
`frontend/src/app/(dashboard)/analitica/_components/FinanzasSection.tsx` (tsx, 128 loc)
  symbols: export function FinanzasSection
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/analitica/_components/KpiCard.tsx, frontend/src/app/(dashboard)/analitica/_components/SectionHeader.tsx, frontend/src/app/(dashboard)/analitica/_components/AgingTable.tsx, frontend/src/app/(dashboard)/analitica/_components/utils.ts
`frontend/src/app/(dashboard)/analitica/_components/IaSection.tsx` (tsx, 162 loc)
  symbols: export function IaSection
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/analitica/_components/KpiCard.tsx, frontend/src/app/(dashboard)/analitica/_components/SectionHeader.tsx, frontend/src/app/(dashboard)/analitica/_components/utils.ts
`frontend/src/app/(dashboard)/analitica/_components/KpiCard.tsx` (tsx, 41 loc)
  symbols: export function KpiCard
  imports: lucide-react
`frontend/src/app/(dashboard)/analitica/_components/ResumenSection.tsx` (tsx, 246 loc)
  symbols: export function ResumenSection
  imports: @/lib, lucide-react, next-intl, recharts
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/analitica/_components/KpiCard.tsx, frontend/src/app/(dashboard)/analitica/_components/SectionHeader.tsx, frontend/src/app/(dashboard)/analitica/_components/CustomTooltip.tsx, frontend/src/app/(dashboard)/analitica/_components/utils.ts
`frontend/src/app/(dashboard)/analitica/_components/RrhhSection.tsx` (tsx, 161 loc)
  symbols: export function RrhhSection
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/analitica/_components/KpiCard.tsx, frontend/src/app/(dashboard)/analitica/_components/SectionHeader.tsx, frontend/src/app/(dashboard)/analitica/_components/utils.ts
`frontend/src/app/(dashboard)/analitica/_components/SectionHeader.tsx` (tsx, 18 loc)
  symbols: export function SectionHeader
  imports: lucide-react
`frontend/src/app/(dashboard)/analitica/_components/VentasSection.tsx` (tsx, 235 loc)
  symbols: export function VentasSection
  imports: @/lib, lucide-react, next-intl, recharts
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/analitica/_components/KpiCard.tsx, frontend/src/app/(dashboard)/analitica/_components/SectionHeader.tsx, frontend/src/app/(dashboard)/analitica/_components/CustomTooltip.tsx, frontend/src/app/(dashboard)/analitica/_components/utils.ts
`frontend/src/app/(dashboard)/analitica/_components/utils.ts` (ts, 10 loc)
  symbols: export function fmt; export function fmtInt; export const COLORS_PIE
`frontend/src/app/(dashboard)/analitica/_hooks/useAnalitica.ts` (ts, 138 loc)
  symbols: export function useAnalitica
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/analitica/page.tsx` (tsx, 175 loc)
  symbols: export function AnaliticaPage; function monthOptions
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/analitica/_hooks/useAnalitica.ts, frontend/src/app/(dashboard)/analitica/_components/ResumenSection.tsx, frontend/src/app/(dashboard)/analitica/_components/VentasSection.tsx, frontend/src/app/(dashboard)/analitica/_components/FinanzasSection.tsx, frontend/src/app/(dashboard)/analitica/_components/RrhhSection.tsx, frontend/src/app/(dashboard)/analitica/_components/IaSection.tsx
`frontend/src/app/(dashboard)/aprobaciones/page.tsx` (tsx, 6 loc)
  symbols: export function AprobacionesRedirect
  imports: next
`frontend/src/app/(dashboard)/auditoria/_hooks/useAuditoria.ts` (ts, 34 loc)
  symbols: export function useAuditoria
  imports: @/lib, next, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/auditoria/page.tsx` (tsx, 154 loc)
  symbols: export function AuditoriaPage; function EntryRow; function AuditoriaContent; function AuditoriaFallback
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/auditoria/_hooks/useAuditoria.ts
`frontend/src/app/(dashboard)/automatizaciones/_components/ScheduleBuilder.tsx` (tsx, 172 loc)
  symbols: export function ScheduleBuilder
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/automatizaciones/_components/constants.ts
`frontend/src/app/(dashboard)/automatizaciones/_components/WorkflowCard.tsx` (tsx, 454 loc)
  symbols: export function WorkflowCard; function runningMinutesSince
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/automatizaciones/_components/constants.ts, frontend/src/app/(dashboard)/automatizaciones/_hooks/useWorkflowExecution.ts
`frontend/src/app/(dashboard)/automatizaciones/_components/WorkflowFormModal.tsx` (tsx, 276 loc)
  symbols: export function WorkflowFormModal
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/components/Workflows/WorkflowGraph.tsx, frontend/src/app/(dashboard)/automatizaciones/_components/ScheduleBuilder.tsx, frontend/src/app/(dashboard)/automatizaciones/_components/constants.ts
`frontend/src/app/(dashboard)/automatizaciones/_components/constants.ts` (ts, 144 loc)
  symbols: export function buildTriggerConfig; export function buildExecStatus; export function buildTemplates; export function buildDays; export const MONTHS_DAYS; export const HOURS; export const MINUTES_OPTIONS; export function parseCron; export function buildCron; export function cronToHuman; export function hasFanOut
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizaciones.ts` (ts, 116 loc)
  symbols: export function useAutomatizaciones
  → usa: frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizacionesCRUD.ts, frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizacionesExecution.ts
`frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizacionesCRUD.ts` (ts, 378 loc)
  symbols: export function useAutomatizacionesCRUD; function detectDomainFromIntent; function pickEmployeeForDomain
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/ai_employees.ts, frontend/src/lib/logger.ts, frontend/src/app/(dashboard)/automatizaciones/_components/constants.ts, frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizaciones.ts
`frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizacionesExecution.ts` (ts, 140 loc)
  symbols: export function useAutomatizacionesExecution
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts, frontend/src/lib/hooks/usePolling.ts
`frontend/src/app/(dashboard)/automatizaciones/_hooks/useWorkflowExecution.ts` (ts, 130 loc) — Suscripción a eventos WS de ejecución de workflow: - workflow_node_started → marca node como running con startedAt…
  symbols: export function useWorkflowExecution; export function formatElapsed; function enrichWithElapsed
  imports: @/lib, react
  → usa: frontend/src/lib/hooks/useNotificationSocket.ts
`frontend/src/app/(dashboard)/automatizaciones/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/automatizaciones/page.tsx` (tsx, 238 loc)
  symbols: export function WorkflowsPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/components/InfoBanner.tsx, frontend/src/components/ui/ErrorBoundary.tsx, frontend/src/app/(dashboard)/automatizaciones/_components/constants.ts, frontend/src/app/(dashboard)/automatizaciones/_components/WorkflowCard.tsx, frontend/src/app/(dashboard)/automatizaciones/_components/WorkflowFormModal.tsx, frontend/src/app/(dashboard)/automatizaciones/_hooks/useAutomatizaciones.ts
`frontend/src/app/(dashboard)/banca/_components/BancaCharts.tsx` (tsx, 57 loc)
  symbols: export function DonutChart; export function BarSparkline; export function AgentLoader
`frontend/src/app/(dashboard)/banca/_components/ConciliacionTab.tsx` (tsx, 363 loc)
  symbols: export function ConciliacionTab
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/ui/button.tsx, frontend/src/components/shared/KpiCard.tsx, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/banca/_components/ResumenTab.tsx` (tsx, 182 loc)
  symbols: export function ResumenTab
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/KpiCard.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/card.tsx, frontend/src/stores/toast.ts, frontend/src/app/(dashboard)/banca/_hooks/useAgentPolling.ts, frontend/src/app/(dashboard)/banca/_components/BancaCharts.tsx
`frontend/src/app/(dashboard)/banca/_components/SaldosTab.tsx` (tsx, 96 loc)
  symbols: export function SaldosTab
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/components/ui/button.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/EmptyState.tsx, frontend/src/app/(dashboard)/banca/_hooks/useAgentPolling.ts, frontend/src/app/(dashboard)/banca/_components/BancaCharts.tsx
`frontend/src/app/(dashboard)/banca/_components/TransaccionesTab.tsx` (tsx, 298 loc)
  symbols: export function TransaccionesTab; function getTransactionColumns
  imports: @/components, @/lib, @/stores, @tanstack/react-table, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/data-table/index.ts, frontend/src/components/shared/KpiCard.tsx, frontend/src/components/shared/StatusBadge.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/card.tsx, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/banca/_hooks/useAgentPolling.ts` (ts, 53 loc)
  symbols: export function useAgentPolling; export function extractOutput
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/banca/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/banca/page.tsx` (tsx, 64 loc)
  symbols: export function BancaPage
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/banca/_components/SaldosTab.tsx, frontend/src/app/(dashboard)/banca/_components/TransaccionesTab.tsx, frontend/src/app/(dashboard)/banca/_components/ResumenTab.tsx, frontend/src/app/(dashboard)/banca/_components/ConciliacionTab.tsx, frontend/src/components/shared/PageContainer.tsx, frontend/src/components/ui/tabs.tsx
`frontend/src/app/(dashboard)/bandeja/_components/ActivityTab.tsx` (tsx, 131 loc)
  symbols: export function ActivityTab
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/ai_employees.ts, frontend/src/app/(dashboard)/bandeja/_components/InboxMessage.tsx, frontend/src/lib/hooks/useNotificationSocket.ts, frontend/src/lib/hooks/usePolling.ts
`frontend/src/app/(dashboard)/bandeja/_components/ApprovalCard.tsx` (tsx, 91 loc)
  symbols: export function ApprovalCard
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/bandeja/_components/approval-constants.ts
`frontend/src/app/(dashboard)/bandeja/_components/ApprovalsTab.tsx` (tsx, 203 loc)
  symbols: export function ApprovalsTab; function handleApprove; function handleConfirmReject; function handleCleanup
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/hooks/useNotificationSocket.ts, frontend/src/lib/hooks/usePolling.ts, frontend/src/app/(dashboard)/bandeja/_components/ApprovalCard.tsx
`frontend/src/app/(dashboard)/bandeja/_components/InboxMessage.tsx` (tsx, 76 loc)
  symbols: export const buildCategoryConfig; export function timeAgo; export function InboxMessage
  imports: @/lib, next-intl
  → usa: frontend/src/lib/api/ai_employees.ts
`frontend/src/app/(dashboard)/bandeja/_components/approval-constants.ts` (ts, 19 loc)
  symbols: export const RISK_STYLE; export const buildRiskLabels; export const minutesUntil
`frontend/src/app/(dashboard)/bandeja/page.tsx` (tsx, 78 loc)
  symbols: export function BandejaPage
  imports: @/components, lucide-react, next, next-intl, react
  → usa: frontend/src/app/(dashboard)/bandeja/_components/ApprovalsTab.tsx, frontend/src/app/(dashboard)/bandeja/_components/ActivityTab.tsx, frontend/src/components/shared/PageContainer.tsx, frontend/src/components/ui/tabs.tsx
`frontend/src/app/(dashboard)/bienvenida/page.tsx` (tsx, 8 loc)
  symbols: export function BienvenidaRedirect
  imports: next
`frontend/src/app/(dashboard)/bienvenida/simulacion-303/page.tsx` (tsx, 200 loc) — UI.SIM — simulación Modelo 303 con datos ejemplo…
  symbols: export function Simulacion303Page; function Box; function Table
  imports: @/lib, @/stores, lucide-react, next, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/onboarding.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/calendario/page.tsx` (tsx, 497 loc)
  symbols: export function CalendarioPage; function padDate; function daysInMonth; function firstWeekday; function toDateKey; function openNewEvent; function handleCreate
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx, frontend/src/components/ui/select.tsx, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/catalogo/_components/ProductModal.tsx` (tsx, 204 loc)
  symbols: export function ProductModal
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/catalogo/_hooks/useCatalogPage.ts` (ts, 126 loc)
  symbols: export function useCatalogPage
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/catalogo/page.tsx` (tsx, 176 loc)
  symbols: export function CatalogPage
  imports: @/components, @/lib, @tanstack/react-table, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/data-table/index.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/StatusBadge.tsx, frontend/src/components/ui/EmptyState.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/catalogo/_hooks/useCatalogPage.ts, frontend/src/app/(dashboard)/catalogo/_components/ProductModal.tsx, frontend/src/components/shared/ImportCsvModal.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/clientes/[id]/_hooks/useClienteDetalle.ts` (ts, 81 loc)
  symbols: export function useClienteDetalle
  imports: @/lib, next, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/clientes/[id]/page.tsx` (tsx, 180 loc)
  symbols: export function ClientDetailPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/app/(dashboard)/clientes/[id]/_hooks/useClienteDetalle.ts, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/clientes/_components/ClienteDrawer.tsx` (tsx, 266 loc)
  symbols: export function ClienteDrawer; function downloadInvoicePdf; function getInitials
  imports: @/components, @/lib, @/stores, lucide-react, next, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/components/shared/index.ts, frontend/src/components/ui/EmptyState.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/avatar.tsx
`frontend/src/app/(dashboard)/clientes/_components/ClienteFormModal.tsx` (tsx, 139 loc)
  symbols: export function ClienteFormModal
  imports: @/components, @/lib, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/index.ts, frontend/src/components/ui/input.tsx, frontend/src/components/ui/select.tsx, frontend/src/app/(dashboard)/clientes/_components/clientHealth.ts
`frontend/src/app/(dashboard)/clientes/_components/ClientesCardGrid.tsx` (tsx, 159 loc)
  symbols: export function ClientesCardGrid
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/index.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/app/(dashboard)/clientes/_components/clientHealth.ts
`frontend/src/app/(dashboard)/clientes/_components/ClientesEmptyState.tsx` (tsx, 44 loc)
  symbols: export function ClientesEmptyState
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/components/ui/EmptyState.tsx, frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/clientes/_components/ClientesImportModal.tsx` (tsx, 37 loc)
  symbols: export function ClientesImportModal
  imports: @/components, @/lib, next-intl
  → usa: frontend/src/components/shared/ImportCsvModal.tsx, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/clientes/_components/ClientesTable.tsx` (tsx, 168 loc)
  symbols: export function ClientesTable
  imports: @/components, @/lib, @tanstack/react-table, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/index.ts, frontend/src/components/data-table/index.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/avatar.tsx, frontend/src/app/(dashboard)/clientes/_components/clientHealth.ts
`frontend/src/app/(dashboard)/clientes/_components/clientHealth.ts` (ts, 30 loc)
  symbols: export function getInitials; export function clientHealth; export const HEALTH_CONFIG
  imports: @/lib
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/clientes/_hooks/useClientes.ts` (ts, 161 loc)
  symbols: export function useClientes
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/notifications.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/clientes/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/clientes/page.tsx` (tsx, 155 loc)
  symbols: export function ClientesPage
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/components/shared/index.ts, frontend/src/components/ui/EmptyState.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/clientes/_hooks/useClientes.ts, frontend/src/app/(dashboard)/clientes/_components/ClienteDrawer.tsx, frontend/src/app/(dashboard)/clientes/_components/ClientesTable.tsx, frontend/src/app/(dashboard)/clientes/_components/ClientesCardGrid.tsx, frontend/src/app/(dashboard)/clientes/_components/ClientesEmptyState.tsx, frontend/src/app/(dashboard)/clientes/_components/ClienteFormModal.tsx, frontend/src/app/(dashboard)/clientes/_components/ClientesImportModal.tsx (+2)
`frontend/src/app/(dashboard)/clientes/portal/page.tsx` (tsx, 296 loc)
  symbols: export function PortalClientesPage; function PortalStatusBadge
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/erp.ts, frontend/src/lib/api/client_portal.ts, frontend/src/components/shared/index.ts, frontend/src/stores/confirm.ts, frontend/src/stores/toast.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/dialog.tsx
`frontend/src/app/(dashboard)/compliance/_components/BOETab.tsx` (tsx, 181 loc)
  symbols: export function BOETab
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/errors.ts
`frontend/src/app/(dashboard)/compliance/_components/CalendarioTab.tsx` (tsx, 147 loc)
  symbols: export function CalendarioTab; function VencimientoCard
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/errors.ts, frontend/src/app/(dashboard)/compliance/_hooks/useCompliance.ts
`frontend/src/app/(dashboard)/compliance/_components/ConsultaTab.tsx` (tsx, 109 loc)
  symbols: export function ConsultaTab; function submit
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/app/(dashboard)/compliance/_hooks/useCompliance.ts, frontend/src/lib/api/errors.ts
`frontend/src/app/(dashboard)/compliance/_hooks/useCompliance.ts` (ts, 64 loc)
  symbols: export async function executeTaskAndWait; export function useCompliance
  imports: @/lib, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/compliance/page.tsx` (tsx, 49 loc)
  symbols: export function CompliancePage
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/compliance/_hooks/useCompliance.ts, frontend/src/app/(dashboard)/compliance/_components/CalendarioTab.tsx, frontend/src/app/(dashboard)/compliance/_components/BOETab.tsx, frontend/src/app/(dashboard)/compliance/_components/ConsultaTab.tsx
`frontend/src/app/(dashboard)/compras/facturas/_components/RegistrarFacturaModal.tsx` (tsx, 130 loc)
  symbols: export function RegistrarFacturaModal
  imports: @/components, @/lib, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/index.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/select.tsx
`frontend/src/app/(dashboard)/compras/facturas/_hooks/useFacturasRecibidas.ts` (ts, 204 loc)
  symbols: export function useFacturasRecibidas
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/compras/facturas/page.tsx` (tsx, 236 loc)
  symbols: export function FacturasRecibidasPage
  imports: @/components, @/lib, @tanstack/react-table, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/StatusBadge.tsx, frontend/src/components/data-table/index.ts, frontend/src/components/ui/EmptyState.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/compras/facturas/_hooks/useFacturasRecibidas.ts, frontend/src/app/(dashboard)/compras/facturas/_components/RegistrarFacturaModal.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/compras/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/compras/page.tsx` (tsx, 73 loc)
  symbols: export async function ComprasPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/compras/pedidos/_components/NuevoPedidoModal.tsx` (tsx, 135 loc)
  symbols: export function NuevoPedidoModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/compras/pedidos/_hooks/usePedidosCompra.ts
`frontend/src/app/(dashboard)/compras/pedidos/_components/RecibirModal.tsx` (tsx, 139 loc)
  symbols: export function RecibirModal
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/warehouses.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx, frontend/src/components/ui/dialog.tsx
`frontend/src/app/(dashboard)/compras/pedidos/_hooks/usePedidosCompra.ts` (ts, 143 loc)
  symbols: export function usePedidosCompra
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/compras/pedidos/page.tsx` (tsx, 182 loc)
  symbols: export function PedidosCompraPage
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/app/(dashboard)/compras/pedidos/_hooks/usePedidosCompra.ts, frontend/src/app/(dashboard)/compras/pedidos/_components/NuevoPedidoModal.tsx, frontend/src/app/(dashboard)/compras/pedidos/_components/RecibirModal.tsx, frontend/src/lib/api.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/compras/proveedores/_components/ProveedorModal.tsx` (tsx, 99 loc)
  symbols: export function ProveedorModal
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/compras/proveedores/_hooks/useProveedores.ts` (ts, 90 loc)
  symbols: export function useProveedores
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/compras/proveedores/page.tsx` (tsx, 138 loc)
  symbols: export function ProveedoresPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/compras/proveedores/_hooks/useProveedores.ts, frontend/src/app/(dashboard)/compras/proveedores/_components/ProveedorModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/actualizaciones/_hooks/useActualizaciones.ts` (ts, 94 loc)
  symbols: export function useActualizaciones; function checkForUpdates; function installUpdate
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/configuracion/actualizaciones/page.tsx` (tsx, 240 loc)
  symbols: export function ActualizacionesPage; function StatusRow
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/configuracion/actualizaciones/_hooks/useActualizaciones.ts, frontend/src/components/settings/UpdateChannelSelector.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/api-keys/_components/ClaudeCodeCard.tsx` (tsx, 191 loc)
  symbols: export function ClaudeCodeCard
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/configuracion/api-keys/_hooks/useApiKeys.tsx
`frontend/src/app/(dashboard)/configuracion/api-keys/_components/EmbeddingsCard.tsx` (tsx, 46 loc)
  symbols: export function EmbeddingsCard
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/configuracion/api-keys/_hooks/useApiKeys.tsx
`frontend/src/app/(dashboard)/configuracion/api-keys/_components/LlmProvidersCard.tsx` (tsx, 143 loc)
  symbols: export function LlmProvidersCard
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/configuracion/api-keys/_hooks/useApiKeys.tsx
`frontend/src/app/(dashboard)/configuracion/api-keys/_components/UsageStatsCard.tsx` (tsx, 141 loc)
  symbols: export function UsageStatsCard; function fmt; function monthLabel
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/llm_usage.ts
`frontend/src/app/(dashboard)/configuracion/api-keys/_hooks/useApiKeys.tsx` (tsx, 150 loc)
  symbols: export const LLM_PROVIDERS; export const EMBEDDINGS_OPTIONS; export function useApiKeys; function updateProvider; function save
  imports: @/lib, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/configuracion/api-keys/page.tsx` (tsx, 89 loc)
  symbols: export function ApiKeysPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/InfoBanner.tsx, frontend/src/app/(dashboard)/configuracion/api-keys/_hooks/useApiKeys.tsx, frontend/src/app/(dashboard)/configuracion/api-keys/_components/LlmProvidersCard.tsx, frontend/src/app/(dashboard)/configuracion/api-keys/_components/EmbeddingsCard.tsx, frontend/src/app/(dashboard)/configuracion/api-keys/_components/ClaudeCodeCard.tsx, frontend/src/app/(dashboard)/configuracion/api-keys/_components/UsageStatsCard.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/autonomia/page.tsx` (tsx, 191 loc) — SEC.AUT — Settings de autonomía por dominio…
  symbols: export function AutonomyPage; function changeMode; function resetDomain
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/autonomy.ts, frontend/src/stores/toast.ts, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/backups/page.tsx` (tsx, 284 loc)
  symbols: export function BackupsPage; function formatAge; function formatDate
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/stores/toast.ts, frontend/src/lib/api/system.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/table.tsx, frontend/src/components/ui/skeleton.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/empresa/_components/LogoSection.tsx` (tsx, 209 loc)
  symbols: export function LogoSection
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/tenant.ts, frontend/src/components/ui/button.tsx, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/configuracion/empresa/_hooks/useConfiguracionEmpresa.ts` (ts, 79 loc)
  symbols: export function useConfiguracionEmpresa; function handleSave
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/configuracion/empresa/page.tsx` (tsx, 149 loc)
  symbols: export function EmpresaConfigPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/configuracion/empresa/_components/LogoSection.tsx, frontend/src/app/(dashboard)/configuracion/empresa/_hooks/useConfiguracionEmpresa.ts, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/firma-digital/page.tsx` (tsx, 7 loc)
  symbols: export function FirmaDigitalRedirect
  imports: next
`frontend/src/app/(dashboard)/configuracion/idioma/page.tsx` (tsx, 106 loc) — I18N.SEL — Settings selector de idioma…
  symbols: export function IdiomaPage; function choose
  imports: @/components, @/hooks, @/stores, lucide-react, next, next-intl, react
  → usa: frontend/src/stores/toast.ts, frontend/src/hooks/useLocale.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/integraciones/_hooks/useConfiguracionIntegraciones.ts` (ts, 82 loc)
  symbols: export function useConfiguracionIntegraciones
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/messaging.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/configuracion/integraciones/page.tsx` (tsx, 119 loc)
  symbols: export function IntegracionesPage
  imports: next-intl
  → usa: frontend/src/app/(dashboard)/configuracion/integraciones/_hooks/useConfiguracionIntegraciones.ts
`frontend/src/app/(dashboard)/configuracion/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/configuracion/mantenimiento/page.tsx` (tsx, 168 loc) — Mantenimiento — herramientas de admin para operaciones puntuales: - CONT.LOG: descargar bundle de diagnóstico ZIP (logs scrubbed + info) - M…
  symbols: export function MantenimientoPage; function downloadBundle; function runBackfill
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/system.ts, frontend/src/stores/toast.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/page.tsx` (tsx, 111 loc)
  symbols: export async function ConfiguracionPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/perfil/page.tsx` (tsx, 93 loc)
  symbols: export function PerfilPage; function save
  imports: @/components, @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/preferencias/page.tsx` (tsx, 100 loc) — UI.DEN — Settings de preferencias de UI (densidad)
  symbols: export function PreferenciasPage
  imports: @/components, @/hooks, lucide-react, next-intl
  → usa: frontend/src/hooks/useDensity.ts, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/configuracion/regap/page.tsx` (tsx, 7 loc)
  symbols: export function RegapRedirect
  imports: next
`frontend/src/app/(dashboard)/configuracion/usuarios/_components/Modal.tsx` (tsx, 80 loc)
  symbols: export function Modal; export function ModalActions; export function Field
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/configuracion/usuarios/_components/NewInvitationModal.tsx` (tsx, 82 loc)
  symbols: export function NewInvitationModal; function handleSubmit
  imports: next-intl, react
  → usa: frontend/src/app/(dashboard)/configuracion/usuarios/roles.ts, frontend/src/app/(dashboard)/configuracion/usuarios/_components/Modal.tsx
`frontend/src/app/(dashboard)/configuracion/usuarios/_components/NewUserModal.tsx` (tsx, 104 loc)
  symbols: export function NewUserModal; function handleSubmit
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/configuracion/usuarios/roles.ts, frontend/src/app/(dashboard)/configuracion/usuarios/_components/Modal.tsx
`frontend/src/app/(dashboard)/configuracion/usuarios/_components/PendingInvitationsTable.tsx` (tsx, 64 loc)
  symbols: export function PendingInvitationsTable
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/configuracion/usuarios/roles.ts
`frontend/src/app/(dashboard)/configuracion/usuarios/_components/PortalAccessCard.tsx` (tsx, 111 loc) — Tarjeta que muestra la URL para que los empleados accedan a su portal desde el móvil dentro de la red de la oficina (misma Wi-Fi)…
  symbols: export function PortalAccessCard; function CopyRow; function copy
  imports: lucide-react, next-intl, react
  → usa: frontend/src/app/(dashboard)/configuracion/usuarios/_hooks/useLanAccess.ts
`frontend/src/app/(dashboard)/configuracion/usuarios/_components/ShareInvitationModal.tsx` (tsx, 87 loc)
  symbols: export function ShareInvitationModal; function buildShareUrl; function copy
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/configuracion/usuarios/_components/Modal.tsx
`frontend/src/app/(dashboard)/configuracion/usuarios/_components/UsersTable.tsx` (tsx, 121 loc)
  symbols: export function UsersTable
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/configuracion/usuarios/roles.ts
`frontend/src/app/(dashboard)/configuracion/usuarios/_hooks/useLanAccess.ts` (ts, 58 loc) — Acceso desde la red local (oficina) para que los empleados entren al portal desde su móvil…
  symbols: export function useLanAccess; function getElectronAPI
  imports: react
`frontend/src/app/(dashboard)/configuracion/usuarios/_hooks/useUsuarios.ts` (ts, 113 loc)
  symbols: export function useUsuarios
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/configuracion/usuarios/page.tsx` (tsx, 183 loc)
  symbols: export function UsuariosConfigPage; function handleCreate; function handleInvite; function handleToggleActive; function handleChangeRole; function handleDelete; function handleRevoke
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/confirm.ts, frontend/src/app/(dashboard)/configuracion/usuarios/_hooks/useUsuarios.ts, frontend/src/app/(dashboard)/configuracion/usuarios/_hooks/useLanAccess.ts, frontend/src/app/(dashboard)/configuracion/usuarios/_components/PortalAccessCard.tsx, frontend/src/app/(dashboard)/configuracion/usuarios/_components/PendingInvitationsTable.tsx, frontend/src/app/(dashboard)/configuracion/usuarios/_components/UsersTable.tsx, frontend/src/app/(dashboard)/configuracion/usuarios/_components/NewUserModal.tsx, frontend/src/app/(dashboard)/configuracion/usuarios/_components/NewInvitationModal.tsx, frontend/src/app/(dashboard)/configuracion/usuarios/_components/ShareInvitationModal.tsx (+1)
`frontend/src/app/(dashboard)/configuracion/usuarios/roles.ts` (ts, 14 loc)
  symbols: export const USER_ROLES; export const INVITE_ROLES; export function roleLabels
`frontend/src/app/(dashboard)/configuracion/verifactu/ApoderamientoPanel.tsx` (tsx, 493 loc) — PRES.REG — wizard onboarding REGAP (apoderamiento AEAT)…
  symbols: export function ApoderamientoPanel; function handleStartBranch; function handleGrant; function handleVerify; function handleReset; function PhaseStepper; function BranchCard; function Instructions
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/regap.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/configuracion/verifactu/FirmaDigitalPanel.tsx` (tsx, 212 loc)
  symbols: export function FirmaDigitalPanel; function isExpired; function isExpiringSoon
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/configuracion/verifactu/ModoVerifactuPanel.tsx` (tsx, 202 loc) — FAC.MODE — Settings del modo de remisión Verifactu…
  symbols: export function ModoVerifactuPanel; function setMode; function ModeCard
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/verifactuConfig.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/configuracion/verifactu/page.tsx` (tsx, 62 loc)
  symbols: export function ConfiguracionFiscalPage
  imports: @/components, lucide-react, next, next-intl, react
  → usa: frontend/src/app/(dashboard)/configuracion/verifactu/ModoVerifactuPanel.tsx, frontend/src/app/(dashboard)/configuracion/verifactu/ApoderamientoPanel.tsx, frontend/src/app/(dashboard)/configuracion/verifactu/FirmaDigitalPanel.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/contabilidad/activos/_components/AssetModal.tsx` (tsx, 140 loc)
  symbols: export function AssetModal
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/contabilidad/activos/_hooks/useActivos.ts
`frontend/src/app/(dashboard)/contabilidad/activos/_hooks/useActivos.ts` (ts, 126 loc)
  symbols: export const emptyForm; export function calcDepreciation; export function useActivos
  imports: @/lib, @/stores, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/contabilidad/activos/page.tsx` (tsx, 163 loc)
  symbols: export function ActivosFijosPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/contabilidad/activos/_hooks/useActivos.ts, frontend/src/app/(dashboard)/contabilidad/activos/_components/AssetModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/contabilidad/asesorias/_components/AdvisoryChatPanel.tsx` (tsx, 77 loc)
  symbols: export function AdvisoryChatPanel
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/contabilidad/asesorias/_components/CalendarSection.tsx` (tsx, 68 loc)
  symbols: export function CalendarSection
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts
`frontend/src/app/(dashboard)/contabilidad/asesorias/_components/GuidesSection.tsx` (tsx, 96 loc)
  symbols: export function GuidesSection
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/contabilidad/asesorias/_components/NewsFeed.tsx` (tsx, 85 loc)
  symbols: export function NewsFeed
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/contabilidad/asesorias/_hooks/useAsesorias.ts` (ts, 106 loc)
  symbols: export function useAsesorias; function fetchAdvisory; function handleChat
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/contabilidad/asesorias/page.tsx` (tsx, 100 loc)
  symbols: export function AsesoriasPage
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/contabilidad/asesorias/_hooks/useAsesorias.ts, frontend/src/app/(dashboard)/contabilidad/asesorias/_components/AdvisoryChatPanel.tsx, frontend/src/app/(dashboard)/contabilidad/asesorias/_components/CalendarSection.tsx, frontend/src/app/(dashboard)/contabilidad/asesorias/_components/GuidesSection.tsx, frontend/src/app/(dashboard)/contabilidad/asesorias/_components/NewsFeed.tsx
`frontend/src/app/(dashboard)/contabilidad/balance-de-situacion/_hooks/useBalanceSituacion.ts` (ts, 110 loc)
  symbols: export function useBalanceSituacion; function classify; function groupBySub
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/contabilidad/balance-de-situacion/page.tsx` (tsx, 186 loc)
  symbols: export function BalanceSituacionPage; function SectionBlock
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/utils.ts, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/contabilidad/balance-de-situacion/_hooks/useBalanceSituacion.ts
`frontend/src/app/(dashboard)/contabilidad/cuadro-de-cuentas/_hooks/useCuadroCuentas.ts` (ts, 91 loc)
  symbols: export function useCuadroCuentas
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/contabilidad/cuadro-de-cuentas/page.tsx` (tsx, 124 loc)
  symbols: export function CuadroCuentasPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/contabilidad/cuadro-de-cuentas/_hooks/useCuadroCuentas.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx
`frontend/src/app/(dashboard)/contabilidad/libro-diario/_components/AsientoModal.tsx` (tsx, 124 loc)
  symbols: export function AsientoModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/lib/api.ts, frontend/src/app/(dashboard)/contabilidad/libro-diario/_hooks/useLibroDiario.ts
`frontend/src/app/(dashboard)/contabilidad/libro-diario/_components/CierreLibrosCard.tsx` (tsx, 288 loc)
  symbols: export function CierreLibrosCard; function quarterRange; function currentQuarter
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/accounting.ts, frontend/src/components/ui/button.tsx, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/contabilidad/libro-diario/_hooks/useLibroDiario.ts` (ts, 124 loc)
  symbols: export function useLibroDiario
  imports: @/lib, @/stores, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/contabilidad/libro-diario/page.tsx` (tsx, 128 loc)
  symbols: export function LibroDiarioPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/contabilidad/libro-diario/_hooks/useLibroDiario.ts, frontend/src/app/(dashboard)/contabilidad/libro-diario/_components/AsientoModal.tsx, frontend/src/app/(dashboard)/contabilidad/libro-diario/_components/CierreLibrosCard.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/contabilidad/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/contabilidad/page.tsx` (tsx, 105 loc)
  symbols: export async function ContabilidadPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/contabilidad/perdidas-y-ganancias/_hooks/usePyG.ts` (ts, 101 loc)
  symbols: export function usePyG
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/contabilidad/perdidas-y-ganancias/page.tsx` (tsx, 131 loc)
  symbols: export function PyGPage
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/contabilidad/perdidas-y-ganancias/_hooks/usePyG.ts
`frontend/src/app/(dashboard)/correos/_components/ComposeTab.tsx` (tsx, 152 loc)
  symbols: export function ComposeTab
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/messaging.ts, frontend/src/lib/api/documents.ts, frontend/src/app/(dashboard)/correos/format.ts
`frontend/src/app/(dashboard)/correos/_components/DrivePickerModal.tsx` (tsx, 101 loc)
  symbols: export function DrivePickerModal
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/messaging.ts, frontend/src/app/(dashboard)/correos/format.ts
`frontend/src/app/(dashboard)/correos/_components/InboxTab.tsx` (tsx, 149 loc)
  symbols: export function InboxTab
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/messaging.ts, frontend/src/app/(dashboard)/correos/format.ts, frontend/src/app/(dashboard)/correos/_components/MessageDetailModal.tsx
`frontend/src/app/(dashboard)/correos/_components/InstructTab.tsx` (tsx, 40 loc)
  symbols: export function InstructTab
  imports: lucide-react, next-intl, react
`frontend/src/app/(dashboard)/correos/_components/MessageDetailModal.tsx` (tsx, 91 loc)
  symbols: export function MessageDetailModal
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/components/GenerativeUI.tsx, frontend/src/lib/api/messaging.ts, frontend/src/app/(dashboard)/correos/format.ts
`frontend/src/app/(dashboard)/correos/_hooks/useCorreos.ts` (ts, 249 loc)
  symbols: export function useCorreos; function classifyInbox; function handleDraftReply; function loadInbox; function openMessage; function handleSend; function handleAttach; function removeAttachment; function openDrivePicker; function loadDrive; function attachFromDrive; function handleInstruct
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/messaging.ts, frontend/src/lib/api/documents.ts, frontend/src/app/(dashboard)/correos/constants.ts
`frontend/src/app/(dashboard)/correos/constants.ts` (ts, 9 loc)
  symbols: export const TABS
  imports: lucide-react
`frontend/src/app/(dashboard)/correos/format.ts` (ts, 18 loc)
  symbols: export function formatBytes; export function formatDate
`frontend/src/app/(dashboard)/correos/page.tsx` (tsx, 148 loc)
  symbols: export function CorreosPage
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/correos/constants.ts, frontend/src/app/(dashboard)/correos/_hooks/useCorreos.ts, frontend/src/app/(dashboard)/correos/_components/InboxTab.tsx, frontend/src/app/(dashboard)/correos/_components/ComposeTab.tsx, frontend/src/app/(dashboard)/correos/_components/InstructTab.tsx, frontend/src/app/(dashboard)/correos/_components/DrivePickerModal.tsx
`frontend/src/app/(dashboard)/crm/actividades/_components/CreateActivityModal.tsx` (tsx, 110 loc)
  symbols: export function CreateActivityModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/crm/actividades/_hooks/useActividades.tsx` (tsx, 104 loc)
  symbols: export function useActividades
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/crm/actividades/page.tsx` (tsx, 160 loc)
  symbols: export function ActivitiesPage
  imports: @/components, date-fns, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/crm/actividades/_hooks/useActividades.tsx, frontend/src/app/(dashboard)/crm/actividades/_components/CreateActivityModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/select.tsx
`frontend/src/app/(dashboard)/crm/calendario/_components/CreateEventModal.tsx` (tsx, 95 loc)
  symbols: export function CreateEventModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/crm/calendario/_components/EventDetailModal.tsx` (tsx, 57 loc)
  symbols: export function EventDetailModal
  imports: @/lib, date-fns, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/crm/calendario/_hooks/useCalendario.ts` (ts, 90 loc)
  symbols: export function useCalendario
  imports: @/lib, @/stores, date-fns, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/crm/calendario/page.tsx` (tsx, 115 loc)
  symbols: export function CalendarPage
  imports: @/components, date-fns, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/crm/calendario/_hooks/useCalendario.ts, frontend/src/app/(dashboard)/crm/calendario/_components/CreateEventModal.tsx, frontend/src/app/(dashboard)/crm/calendario/_components/EventDetailModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/crm/embudo-de-ventas/_components/CreateOpportunityModal.tsx` (tsx, 95 loc)
  symbols: export function CreateOpportunityModal
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx
`frontend/src/app/(dashboard)/crm/embudo-de-ventas/_hooks/useEmbudoDeVentas.ts` (ts, 106 loc)
  symbols: export function useEmbudoDeVentas
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/crm/embudo-de-ventas/page.tsx` (tsx, 149 loc)
  symbols: export function CRMPipelinePage
  imports: @/components, date-fns, lucide-react, next-intl
  → usa: frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/badge.tsx, frontend/src/components/ui/input.tsx, frontend/src/app/(dashboard)/crm/embudo-de-ventas/_hooks/useEmbudoDeVentas.ts, frontend/src/app/(dashboard)/crm/embudo-de-ventas/_components/CreateOpportunityModal.tsx
`frontend/src/app/(dashboard)/crm/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/crm/page.tsx` (tsx, 90 loc)
  symbols: export async function CRMPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/crm/reservas/_components/CreateReservationModal.tsx` (tsx, 71 loc)
  symbols: export function CreateReservationModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/crm/reservas/_hooks/useReservas.tsx` (tsx, 87 loc)
  symbols: export function useReservas
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/crm/reservas/page.tsx` (tsx, 131 loc)
  symbols: export function ReservationsPage
  imports: @/components, date-fns, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/crm/reservas/_hooks/useReservas.tsx, frontend/src/app/(dashboard)/crm/reservas/_components/CreateReservationModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx
`frontend/src/app/(dashboard)/crm/reuniones/_components/CreateMeetingModal.tsx` (tsx, 84 loc)
  symbols: export function CreateMeetingModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/crm/reuniones/_hooks/useReuniones.ts` (ts, 77 loc)
  symbols: export function useReuniones
  imports: @/lib, @/stores, date-fns, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/crm/reuniones/page.tsx` (tsx, 141 loc)
  symbols: export function MeetingsPage
  imports: @/components, @/lib, date-fns, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/crm/reuniones/_hooks/useReuniones.ts, frontend/src/app/(dashboard)/crm/reuniones/_components/CreateMeetingModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx
`frontend/src/app/(dashboard)/documentos/_hooks/useDocumentos.ts` (ts, 66 loc)
  symbols: export function useDocumentos; function handleExportDocs; function handleBackup
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/documentos/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/documentos/page.tsx` (tsx, 169 loc)
  symbols: export function DocumentosPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/documentos/RestoreModal.tsx, frontend/src/components/documentos/DocRow.tsx, frontend/src/components/documentos/DocCard.tsx, frontend/src/components/documentos/RagChatBox.tsx, frontend/src/components/documentos/DocSemanticSearch.tsx, frontend/src/components/documentos/ContractWizard.tsx, frontend/src/app/(dashboard)/documentos/_hooks/useDocumentos.ts
`frontend/src/app/(dashboard)/email-marketing/_components/CampaignsTab.tsx` (tsx, 244 loc)
  symbols: export function TabCampaigns
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/components/GenerativeUI.tsx, frontend/src/lib/api/email_marketing.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts, frontend/src/app/(dashboard)/email-marketing/_components/constants.ts
`frontend/src/app/(dashboard)/email-marketing/_components/StatsTab.tsx` (tsx, 83 loc)
  symbols: export function TabStats
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/email_marketing.ts, frontend/src/app/(dashboard)/email-marketing/_components/constants.ts
`frontend/src/app/(dashboard)/email-marketing/_components/TemplatesTab.tsx` (tsx, 176 loc)
  symbols: export function TabTemplates
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/components/GenerativeUI.tsx, frontend/src/lib/api/email_marketing.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts, frontend/src/app/(dashboard)/email-marketing/_components/constants.ts
`frontend/src/app/(dashboard)/email-marketing/_components/constants.ts` (ts, 6 loc)
  symbols: export const errMsg; export const fmt
`frontend/src/app/(dashboard)/email-marketing/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/email-marketing/page.tsx` (tsx, 61 loc)
  symbols: export function EmailMarketingPage
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/app/(dashboard)/email-marketing/_components/CampaignsTab.tsx, frontend/src/app/(dashboard)/email-marketing/_components/TemplatesTab.tsx, frontend/src/app/(dashboard)/email-marketing/_components/StatsTab.tsx, frontend/src/components/shared/PageContainer.tsx, frontend/src/components/ui/tabs.tsx
`frontend/src/app/(dashboard)/error.tsx` (tsx, 41 loc)
  symbols: export function DashboardError
  imports: @/lib, lucide-react, react
  → usa: frontend/src/lib/logger.ts, frontend/src/lib/error-reporter.ts
`frontend/src/app/(dashboard)/escaner/_components/DropZone.tsx` (tsx, 50 loc)
  symbols: export function DropZone
  imports: lucide-react, next-intl, react
`frontend/src/app/(dashboard)/escaner/_components/ErpImportReview.tsx` (tsx, 152 loc) — Revisión + confirmación de una importación Excel/CSV → entidades del ERP…
  symbols: export function ErpImportReview; function handleImport
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/documents.ts
`frontend/src/app/(dashboard)/escaner/_components/ExcelImportPanel.tsx` (tsx, 189 loc)
  symbols: export function ExcelImportPanel; function loadDocuments; function processFiles; function handleUpload; function handleDelete
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/documents.ts, frontend/src/app/(dashboard)/escaner/_components/ErpImportReview.tsx, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/escaner/_components/FacturasImportPanel.tsx` (tsx, 227 loc) — Escáner de facturas de COMPRA → integra en el ERP…
  symbols: export function FacturasImportPanel; function processFiles; function handleFiles; function patch; function patchEmisor; function remove; function handleImport; function Field
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/erp.ts
`frontend/src/app/(dashboard)/escaner/_components/LanToggle.tsx` (tsx, 54 loc)
  symbols: export function LanToggle
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/escaner/_hooks/useEscaner.tsx
`frontend/src/app/(dashboard)/escaner/_components/ScanResults.tsx` (tsx, 126 loc)
  symbols: export function ScanResults
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/escaner/_hooks/useEscaner.tsx
`frontend/src/app/(dashboard)/escaner/_components/SelectedFilesList.tsx` (tsx, 59 loc)
  symbols: export function SelectedFilesList
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/escaner/_hooks/useEscaner.tsx
`frontend/src/app/(dashboard)/escaner/_hooks/useEscaner.tsx` (tsx, 128 loc)
  symbols: export function formatSize; export function getElectronAPI; export function useEscaner; function handleLanToggle; function handleScan
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/hooks/usePolling.ts
`frontend/src/app/(dashboard)/escaner/page.tsx` (tsx, 149 loc)
  symbols: export function EscanerPage; function route
  imports: @/components, lucide-react, next, next-intl, react
  → usa: frontend/src/app/(dashboard)/escaner/_hooks/useEscaner.tsx, frontend/src/app/(dashboard)/escaner/_components/LanToggle.tsx, frontend/src/app/(dashboard)/escaner/_components/DropZone.tsx, frontend/src/app/(dashboard)/escaner/_components/SelectedFilesList.tsx, frontend/src/app/(dashboard)/escaner/_components/ScanResults.tsx, frontend/src/app/(dashboard)/escaner/_components/ExcelImportPanel.tsx, frontend/src/app/(dashboard)/escaner/_components/FacturasImportPanel.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/excel/page.tsx` (tsx, 8 loc)
  symbols: export function ExcelRedirect
  imports: next
`frontend/src/app/(dashboard)/impuestos/AsistidaPanel.tsx` (tsx, 189 loc) — PRES.ASS — UI presentación asistida para Modelos 131 y 200…
  symbols: export function AsistidaPanel; function downloadAndOpen
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/presentacion.ts, frontend/src/stores/toast.ts, frontend/src/components/shared/PageHeader.tsx
`frontend/src/app/(dashboard)/impuestos/ModelosPanel.tsx` (tsx, 531 loc) — MOD.130/347/390/111/190 — preview visual de liquidaciones AEAT…
  symbols: export function ModelosPanel; function fmtEUR; function fmtPct; function downloadPdf; function generate; function TenantHeader; function Stat; function Modelo130View; function Modelo111View; function Modelo190View; function Modelo347View; function Modelo390View … (+1)
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/impuestos/ResumenPanel.tsx` (tsx, 204 loc)
  symbols: export function ResumenPanel; function currentQuarterYear
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/KpiCard.tsx, frontend/src/components/ui/EmptyState.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/tabs.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/impuestos/_hooks/useImpuestos.ts, frontend/src/app/(dashboard)/impuestos/_components/EventCard.tsx, frontend/src/app/(dashboard)/impuestos/_components/ConsultaRapida.tsx, frontend/src/app/(dashboard)/impuestos/_components/LibroRegistroExport.tsx (+3)
`frontend/src/app/(dashboard)/impuestos/_components/CertificateUploadModal.tsx` (tsx, 147 loc)
  symbols: export function CertificateUploadModal
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/impuestos/_components/ConsultaRapida.tsx` (tsx, 128 loc)
  symbols: export function ConsultaRapida; function submit
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/ui/card.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx
`frontend/src/app/(dashboard)/impuestos/_components/EventCard.tsx` (tsx, 83 loc)
  symbols: export function EventCard; function ModeloBadge; function UrgencyBar
  imports: @/components, next-intl
  → usa: frontend/src/components/ui/card.tsx, frontend/src/app/(dashboard)/impuestos/_hooks/useImpuestos.ts
`frontend/src/app/(dashboard)/impuestos/_components/Expediente303Drawer.tsx` (tsx, 258 loc)
  symbols: export function Expediente303Drawer
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/reports.ts, frontend/src/stores/toast.ts, frontend/src/app/(dashboard)/impuestos/_components/PresentacionElectronicaPanel.tsx
`frontend/src/app/(dashboard)/impuestos/_components/LibroRegistroExport.tsx` (tsx, 84 loc)
  symbols: export function LibroRegistroExport
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/components/ui/card.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx
`frontend/src/app/(dashboard)/impuestos/_components/PresentacionElectronicaPanel.tsx` (tsx, 204 loc)
  symbols: export function PresentacionElectronicaPanel
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/aeat.ts, frontend/src/stores/toast.ts, frontend/src/app/(dashboard)/impuestos/_components/CertificateUploadModal.tsx
`frontend/src/app/(dashboard)/impuestos/_components/PresentacionesPanel.tsx` (tsx, 318 loc)
  symbols: export function PresentacionesPanel; function currentDefaults
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/aeat.ts, frontend/src/stores/toast.ts, frontend/src/app/(dashboard)/impuestos/_components/CertificateUploadModal.tsx
`frontend/src/app/(dashboard)/impuestos/_components/PreventiveCheckCard.tsx` (tsx, 145 loc)
  symbols: export function PreventiveCheckCard; function FindingRow
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/modelosAeat.ts
`frontend/src/app/(dashboard)/impuestos/_hooks/useImpuestos.ts` (ts, 35 loc)
  symbols: export function useImpuestos
  imports: @/lib, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/impuestos/asistida/page.tsx` (tsx, 7 loc)
  symbols: export function AsistidaRedirect
  imports: next
`frontend/src/app/(dashboard)/impuestos/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/impuestos/modelos/page.tsx` (tsx, 7 loc)
  symbols: export function ModelosRedirect
  imports: next
`frontend/src/app/(dashboard)/impuestos/page.tsx` (tsx, 55 loc)
  symbols: export function ImpuestosPage
  imports: @/components, lucide-react, next, next-intl, react
  → usa: frontend/src/app/(dashboard)/impuestos/ResumenPanel.tsx, frontend/src/app/(dashboard)/impuestos/ModelosPanel.tsx, frontend/src/app/(dashboard)/impuestos/AsistidaPanel.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/informes/_components/FiscalTab.tsx` (tsx, 208 loc)
  symbols: export function FiscalTab
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/informes/_components/InformesHelpers.tsx, frontend/src/app/(dashboard)/informes/_hooks/useInformes.ts
`frontend/src/app/(dashboard)/informes/_components/GestionTab.tsx` (tsx, 144 loc)
  symbols: export function GestionTab
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/informes/_components/InformesHelpers.tsx, frontend/src/app/(dashboard)/informes/_hooks/useInformes.ts
`frontend/src/app/(dashboard)/informes/_components/InformesHelpers.tsx` (tsx, 80 loc)
  symbols: export function KpiCard; export function Section; export function Row; export function TabBtn
  imports: react
`frontend/src/app/(dashboard)/informes/_hooks/useInformes.ts` (ts, 218 loc)
  symbols: export function fmt; export function fmtMonth; export function prevMonth; export function nextMonth; export function currentMonthStr; export function currentQuarterStr; export function fmtQuarter; export function prevQuarter; export function nextQuarter; export function useInformes; function loadSnapshot; function loadReports … (+5)
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/informes/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/informes/page.tsx` (tsx, 98 loc)
  symbols: export function InformesPage
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/informes/_hooks/useInformes.ts, frontend/src/app/(dashboard)/informes/_components/InformesHelpers.tsx, frontend/src/app/(dashboard)/informes/_components/GestionTab.tsx, frontend/src/app/(dashboard)/informes/_components/FiscalTab.tsx
`frontend/src/app/(dashboard)/integraciones/_hooks/useIntegraciones.ts` (ts, 167 loc)
  symbols: export function useIntegraciones; function connectPsd2; function disconnectPsd2; function connectOAuth; function disconnectIntegration; function connectEmail; function disconnectEmail
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/integrations.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/integraciones/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/integraciones/page.tsx` (tsx, 386 loc)
  symbols: export function IntegracionesPage; function StatusBadge; function IntegrationCard; function EmailSmtpForm; function handleProviderChange; function submit
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/components/InfoBanner.tsx, frontend/src/app/(dashboard)/integraciones/_hooks/useIntegraciones.ts
`frontend/src/app/(dashboard)/inventario/_components/ValuationWidget.tsx` (tsx, 130 loc)
  symbols: export function ValuationWidget
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/KpiCard.tsx
`frontend/src/app/(dashboard)/inventario/almacenes/page.tsx` (tsx, 154 loc)
  symbols: export function WarehousesPage
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/warehouses.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx
`frontend/src/app/(dashboard)/inventario/analitica/page.tsx` (tsx, 212 loc)
  symbols: export function InventarioAnaliticaPage
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/inventory_analytics.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/KpiCard.tsx
`frontend/src/app/(dashboard)/inventario/etiquetas/page.tsx` (tsx, 132 loc)
  symbols: export function EtiquetasPage
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/labels.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx
`frontend/src/app/(dashboard)/inventario/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/inventario/page.tsx` (tsx, 66 loc)
  symbols: export async function InventarioPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/app/(dashboard)/inventario/_components/ValuationWidget.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/inventario/reposicion/page.tsx` (tsx, 133 loc)
  symbols: export function ReposicionPage
  imports: @/components, @/lib, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api/reorder.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/inventario/scanner/_hooks/useWarehouseScanner.ts` (ts, 57 loc)
  symbols: export function useWarehouseScanner
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/inventario/scanner/page.tsx` (tsx, 150 loc)
  symbols: export function WarehouseScannerPage
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/inventario/scanner/_hooks/useWarehouseScanner.ts
`frontend/src/app/(dashboard)/inventario/stock/__tests__/MovementModal.test.tsx` (tsx, 112 loc)
  symbols: function Harness
  imports: @/lib, @/test-utils, react, vitest
  → usa: frontend/src/test-utils/render.tsx, frontend/src/app/(dashboard)/inventario/stock/_components/MovementModal.tsx, frontend/src/app/(dashboard)/inventario/stock/_hooks/useStock.ts, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/inventario/stock/_components/ExpiringLotsPanel.tsx` (tsx, 101 loc)
  symbols: export function ExpiringLotsPanel
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/inventory_lots.ts
`frontend/src/app/(dashboard)/inventario/stock/_components/LotsPanel.tsx` (tsx, 236 loc) — Días hasta caducar (negativo si ya caducó), o null si el lote no tiene caducidad
  symbols: export function LotsPanel; function daysLeft; function ExpiryBadge
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/inventory_lots.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx
`frontend/src/app/(dashboard)/inventario/stock/_components/MovementModal.tsx` (tsx, 152 loc)
  symbols: export function MovementModal
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/inventario/stock/_hooks/useStock.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx, frontend/src/components/ui/dialog.tsx
`frontend/src/app/(dashboard)/inventario/stock/_components/ProductModal.tsx` (tsx, 211 loc)
  symbols: export function ProductModal
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/erp.ts, frontend/src/app/(dashboard)/inventario/stock/_hooks/useStock.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx, frontend/src/components/ui/dialog.tsx
`frontend/src/app/(dashboard)/inventario/stock/_components/StockHelpers.tsx` (tsx, 70 loc)
  symbols: export const MOVEMENT_ICONS; export const MOVEMENT_COLORS; export function StockStatus; export function MovementsPanel
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/StatusBadge.tsx, frontend/src/components/ui/card.tsx
`frontend/src/app/(dashboard)/inventario/stock/_components/WarehouseStockPanel.tsx` (tsx, 147 loc) — Se llama tras una transferencia, por si el padre quiere refrescar
  symbols: export function WarehouseStockPanel
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/warehouses.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx
`frontend/src/app/(dashboard)/inventario/stock/_hooks/useStock.ts` (ts, 246 loc)
  symbols: export function useStock
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/inventario/stock/page.tsx` (tsx, 395 loc)
  symbols: export function StockPage
  imports: @/components, @/lib, @tanstack/react-table, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/data-table/index.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/KpiCard.tsx, frontend/src/components/ui/EmptyState.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/dropdown-menu.tsx, frontend/src/app/(dashboard)/inventario/stock/_hooks/useStock.ts, frontend/src/app/(dashboard)/inventario/stock/_components/StockHelpers.tsx (+5)
`frontend/src/app/(dashboard)/layout.tsx` (tsx, 171 loc)
  symbols: export function DashboardLayout; function decodeJwtName
  imports: @/components, @/hooks, @/lib, @/stores, next, next-intl, react
  → usa: frontend/src/components/layout/Sidebar.tsx, frontend/src/components/layout/Header.tsx, frontend/src/components/ui/ErrorBoundary.tsx, frontend/src/components/ConfirmDialog.tsx, frontend/src/components/ui/ToastContainer.tsx, frontend/src/stores/toast.ts, frontend/src/stores/notifications.ts, frontend/src/lib/api.ts, frontend/src/lib/api/client.ts, frontend/src/lib/secureStore.ts (+3)
`frontend/src/app/(dashboard)/loading.tsx` (tsx, 14 loc)
  symbols: export function DashboardLoading
`frontend/src/app/(dashboard)/marketing/_components/EditPostModal.tsx` (tsx, 167 loc)
  symbols: export function EditPostModal; function toLocalInput
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/marketing.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/marketing/_components/PostsCalendar.tsx` (tsx, 159 loc) — Vista de calendario mensual de publicaciones programadas/publicadas
  symbols: export function PostsCalendar; function postDate
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/marketing.ts, frontend/src/app/(dashboard)/marketing/_components/constants.ts
`frontend/src/app/(dashboard)/marketing/_components/TabAnalitica.tsx` (tsx, 146 loc)
  symbols: export function TabAnalitica
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/marketing.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/marketing/_components/TabCrear.tsx` (tsx, 209 loc)
  symbols: export function TabCrear
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/marketing.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts, frontend/src/app/(dashboard)/marketing/_components/constants.ts
`frontend/src/app/(dashboard)/marketing/_components/TabCuentas.tsx` (tsx, 330 loc)
  symbols: export function TabCuentas; function openExternal
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/marketing.ts, frontend/src/components/ui/social-icons.tsx, frontend/src/app/(dashboard)/marketing/_components/constants.ts
`frontend/src/app/(dashboard)/marketing/_components/TabPlanIA.tsx` (tsx, 260 loc)
  symbols: export function TabPlanIA
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/marketing.ts, frontend/src/components/ui/social-icons.tsx, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts, frontend/src/app/(dashboard)/marketing/_components/constants.ts
`frontend/src/app/(dashboard)/marketing/_components/TabProgramados.tsx` (tsx, 199 loc)
  symbols: export function TabProgramados
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/marketing.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts, frontend/src/app/(dashboard)/marketing/_components/constants.ts, frontend/src/app/(dashboard)/marketing/_components/PostsCalendar.tsx, frontend/src/app/(dashboard)/marketing/_components/EditPostModal.tsx
`frontend/src/app/(dashboard)/marketing/_components/constants.ts` (ts, 84 loc) — ── Plataformas ────────────────────────────────────────────────────────────────
  symbols: export const PLATFORMS; export const HIDDEN_PLATFORM_IDS; export const CONNECTABLE_PLATFORMS
`frontend/src/app/(dashboard)/marketing/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/marketing/page.tsx` (tsx, 69 loc)
  symbols: export function MarketingPage
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/app/(dashboard)/marketing/_components/TabCuentas.tsx, frontend/src/app/(dashboard)/marketing/_components/TabCrear.tsx, frontend/src/app/(dashboard)/marketing/_components/TabProgramados.tsx, frontend/src/app/(dashboard)/marketing/_components/TabPlanIA.tsx, frontend/src/app/(dashboard)/marketing/_components/TabAnalitica.tsx, frontend/src/components/shared/PageContainer.tsx, frontend/src/components/ui/tabs.tsx
`frontend/src/app/(dashboard)/mi-equipo/_components/ChatBubble.tsx` (tsx, 17 loc)
  symbols: export function ChatBubble
  imports: lucide-react
`frontend/src/app/(dashboard)/mi-equipo/_components/ChatSection.tsx` (tsx, 112 loc) — UI.AGT — resumen del último evento de progreso recibido por SSE
  symbols: export function ChatSection
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/components/ai/AIDisclosureBanner.tsx
`frontend/src/app/(dashboard)/mi-equipo/_components/CoordinatorBar.tsx` (tsx, 59 loc)
  symbols: export function CoordinatorBar
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/errors.ts
`frontend/src/app/(dashboard)/mi-equipo/_components/EmployeeCard.tsx` (tsx, 142 loc)
  symbols: export const statusConfig; export const DOMAIN_ICON; export function EmployeeCard; function BudgetBar
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/ai_employees.ts, frontend/src/app/(dashboard)/mi-equipo/_components/IconPicker.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/UsageModal.tsx
`frontend/src/app/(dashboard)/mi-equipo/_components/EmployeeGrid.tsx` (tsx, 124 loc)
  symbols: export function EmployeeGrid
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/ai_employees.ts, frontend/src/app/(dashboard)/mi-equipo/_components/EmployeeCard.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/InstructModal.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/NewEmployeeModal.tsx, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/mi-equipo/_components/IconPicker.tsx` (tsx, 97 loc) — @deprecated use AppearancePicker
  symbols: export const ICON_POOL; export const COLOR_OPTIONS; export function getAvatarClasses; export function AppearancePicker; export function IconPicker; function handler
  imports: next-intl, react
`frontend/src/app/(dashboard)/mi-equipo/_components/InstructModal.tsx` (tsx, 59 loc)
  symbols: export function InstructModal
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/ai_employees.ts, frontend/src/lib/api.ts, frontend/src/lib/api/errors.ts
`frontend/src/app/(dashboard)/mi-equipo/_components/NewEmployeeModal.tsx` (tsx, 89 loc)
  symbols: export function NewEmployeeModal
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/errors.ts
`frontend/src/app/(dashboard)/mi-equipo/_components/NewTaskModal.tsx` (tsx, 139 loc)
  symbols: export function NewTaskModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api/ai_employees.ts, frontend/src/app/(dashboard)/mi-equipo/_components/task-constants.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/EmployeeCard.tsx
`frontend/src/app/(dashboard)/mi-equipo/_components/TaskPanel.tsx` (tsx, 160 loc)
  symbols: export function TaskPanel
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/components/InfoBanner.tsx, frontend/src/components/ui/ErrorBoundary.tsx, frontend/src/components/ai/CostModal.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/TaskRow.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/ChatSection.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/NewTaskModal.tsx, frontend/src/app/(dashboard)/mi-equipo/_hooks/useTaskPanel.ts
`frontend/src/app/(dashboard)/mi-equipo/_components/TaskRow.tsx` (tsx, 232 loc)
  symbols: export function TaskRow; function handleReply
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/mi-equipo/_components/task-constants.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/ChatBubble.tsx
`frontend/src/app/(dashboard)/mi-equipo/_components/UsageModal.tsx` (tsx, 120 loc)
  symbols: export function UsageModal; function fmtTokens; function fmtDate
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/ai_employees.ts
`frontend/src/app/(dashboard)/mi-equipo/_components/task-constants.tsx` (tsx, 78 loc)
  symbols: export const STATUS_COLOR; export const getStatusLabel; export const STATUS_ICON; export const getChatOption; export const getCoordinatorOption; export const getDomainOptions; export const getAllDomainOptions; export function getChatResponse
  imports: @/lib, lucide-react, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/mi-equipo/_hooks/useMiEquipo.ts` (ts, 166 loc)
  symbols: export function useMiEquipo
  imports: @/lib, @/stores, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/errors.ts, frontend/src/lib/api/ai_employees.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/hooks/useNotificationSocket.ts, frontend/src/lib/hooks/usePolling.ts
`frontend/src/app/(dashboard)/mi-equipo/_hooks/useTaskPanel.ts` (ts, 201 loc)
  symbols: export function useTaskPanel; function handleChat; function stopChat; function createTask; function replyToTask; function cancelTask; function cleanupTasks
  imports: @/hooks, @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/errors.ts, frontend/src/lib/api/ai_employees.ts, frontend/src/stores/notifications.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/hooks/useAgentStream.ts, frontend/src/lib/hooks/usePolling.ts
`frontend/src/app/(dashboard)/mi-equipo/page.tsx` (tsx, 158 loc)
  symbols: export function TareasPage
  imports: @/components, @/stores, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/mi-equipo/_components/EmployeeCard.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/InstructModal.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/NewEmployeeModal.tsx, frontend/src/app/(dashboard)/mi-equipo/_components/TaskPanel.tsx, frontend/src/app/(dashboard)/mi-equipo/_hooks/useMiEquipo.ts, frontend/src/stores/toast.ts, frontend/src/components/shared/LlmNotConfiguredBanner.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/page.tsx` (tsx, 96 loc)
  symbols: export function DashboardPage; function getGreeting
  imports: @/components, @/hooks, next, next-intl, react
  → usa: frontend/src/hooks/useUserRole.ts, frontend/src/components/ui/ErrorBoundary.tsx, frontend/src/app/(dashboard)/_hooks/useDashboard.ts, frontend/src/app/(dashboard)/_components/AiChatBar.tsx, frontend/src/app/(dashboard)/_components/IntegrationsWidget.tsx, frontend/src/app/(dashboard)/_components/KpiSection.tsx, frontend/src/app/(dashboard)/_components/AiInsightsSection.tsx, frontend/src/app/(dashboard)/_components/CashflowChart.tsx, frontend/src/app/(dashboard)/_components/RecentInvoicesSection.tsx, frontend/src/app/(dashboard)/_components/AiActivitySection.tsx (+8)
`frontend/src/app/(dashboard)/plantillas/_components/ContratosTab.tsx` (tsx, 352 loc)
  symbols: export function ContratosTab
  imports: @/components, @/lib, @/stores, lucide-react, next, next-intl, react
  → usa: frontend/src/components/GenerativeUI.tsx, frontend/src/lib/api/documents.ts, frontend/src/lib/api/erp.ts, frontend/src/lib/api/hr.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/utils.ts, frontend/src/app/(dashboard)/plantillas/_components/templateOptions.ts
`frontend/src/app/(dashboard)/plantillas/_components/templateOptions.ts` (ts, 84 loc)
  symbols: export const buildContractVariables; export const buildTemplateTypes; export const buildLayoutPresets; export const buildAccentColors; export const buildFonts; export const buildHeaderStyles; export const buildTableStyles; export const buildLogoPositions; export const EMPTY_FORM
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api/templates.ts
`frontend/src/app/(dashboard)/plantillas/_hooks/usePlantillas.ts` (ts, 159 loc)
  symbols: export function usePlantillas
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api/templates.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/app/(dashboard)/plantillas/_components/templateOptions.ts
`frontend/src/app/(dashboard)/plantillas/page.tsx` (tsx, 291 loc)
  symbols: export function PlantillasPage
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/app/(dashboard)/plantillas/_components/ContratosTab.tsx, frontend/src/app/(dashboard)/plantillas/_components/templateOptions.ts, frontend/src/app/(dashboard)/plantillas/_hooks/usePlantillas.ts, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/portal/_components/ExpenseModal.tsx` (tsx, 96 loc)
  symbols: export function ExpenseModal
  imports: @/components, next-intl, react
  → usa: frontend/src/components/ui/button.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/select.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx, frontend/src/app/(dashboard)/portal/_components/constants.ts, frontend/src/app/(dashboard)/portal/_hooks/usePortal.ts
`frontend/src/app/(dashboard)/portal/_components/FichaTab.tsx` (tsx, 118 loc)
  symbols: export function FichaTab
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/portal/_components/constants.ts
`frontend/src/app/(dashboard)/portal/_components/GastosTab.tsx` (tsx, 103 loc)
  symbols: export function GastosTab
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/portal/_components/constants.ts
`frontend/src/app/(dashboard)/portal/_components/LeaveRequestModal.tsx` (tsx, 71 loc)
  symbols: export function LeaveRequestModal
  imports: @/components, next-intl, react
  → usa: frontend/src/components/ui/button.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/select.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx, frontend/src/app/(dashboard)/portal/_components/constants.ts, frontend/src/app/(dashboard)/portal/_hooks/usePortal.ts
`frontend/src/app/(dashboard)/portal/_components/NominasTab.tsx` (tsx, 61 loc)
  symbols: export function NominasTab
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/portal/_components/constants.ts
`frontend/src/app/(dashboard)/portal/_components/PortalHeader.tsx` (tsx, 119 loc)
  symbols: export function PortalHeader
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/portal/_components/constants.ts
`frontend/src/app/(dashboard)/portal/_components/VacacionesTab.tsx` (tsx, 77 loc)
  symbols: export function VacacionesTab
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/portal/_components/constants.ts
`frontend/src/app/(dashboard)/portal/_components/constants.ts` (ts, 33 loc)
  symbols: export const STATUS_BADGE; export const LEAVE_TYPE_VALUES; export const EXPENSE_CATEGORY_VALUES; export const EXPENSE_STATUS_STYLE; export const DAY_KEYS; export function fmt; export function currency; export function formatClockTime
`frontend/src/app/(dashboard)/portal/_hooks/usePortal.ts` (ts, 185 loc)
  symbols: export function usePortal
  imports: @/hooks, @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/hooks/useUserRole.ts, frontend/src/app/(dashboard)/portal/_components/constants.ts
`frontend/src/app/(dashboard)/portal/page.tsx` (tsx, 155 loc)
  symbols: export function PortalPage
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api/client.ts, frontend/src/app/(dashboard)/portal/_hooks/usePortal.ts, frontend/src/app/(dashboard)/portal/_components/PortalHeader.tsx, frontend/src/app/(dashboard)/portal/_components/FichaTab.tsx, frontend/src/app/(dashboard)/portal/_components/NominasTab.tsx, frontend/src/app/(dashboard)/portal/_components/VacacionesTab.tsx, frontend/src/app/(dashboard)/portal/_components/GastosTab.tsx, frontend/src/app/(dashboard)/portal/_components/LeaveRequestModal.tsx, frontend/src/app/(dashboard)/portal/_components/ExpenseModal.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/primeros-pasos/_components/DemoDataCard.tsx` (tsx, 118 loc) — Tarjeta "Datos de ejemplo" del onboarding: siembra/borra una pyme demo (clientes/productos/facturas) para que el producto se vea vivo en el…
  symbols: export function DemoDataCard
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api/onboarding.ts
`frontend/src/app/(dashboard)/primeros-pasos/_hooks/usePrimerosPassos.ts` (ts, 240 loc)
  symbols: export const buildSteps; export const COLOR_MAP; export const buildIaExamples; export function usePrimerosPassos
  imports: @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/primeros-pasos/page.tsx` (tsx, 275 loc)
  symbols: export function PrimerosPassPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/app/(dashboard)/primeros-pasos/_hooks/usePrimerosPassos.ts, frontend/src/app/(dashboard)/primeros-pasos/_components/DemoDataCard.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/proyectos/_components/NewProjectModal.tsx` (tsx, 91 loc)
  symbols: export function NewProjectModal
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/proyectos/_hooks/useProjectsPage.ts` (ts, 107 loc)
  symbols: export function useProjectsPage
  imports: @/lib, date-fns, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/proyectos/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/proyectos/mis-tareas/_components/NewTaskModal.tsx` (tsx, 60 loc)
  symbols: export function NewTaskModal
  imports: @/lib, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/proyectos/mis-tareas/_hooks/useMisTareas.ts` (ts, 98 loc)
  symbols: export const STAGES; export function useMisTareas
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/proyectos/mis-tareas/page.tsx` (tsx, 126 loc)
  symbols: export function ProjectTasksPage
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/app/(dashboard)/proyectos/mis-tareas/_hooks/useMisTareas.ts, frontend/src/app/(dashboard)/proyectos/mis-tareas/_components/NewTaskModal.tsx
`frontend/src/app/(dashboard)/proyectos/page.tsx` (tsx, 138 loc)
  symbols: export function ProjectsPage
  imports: @/components, date-fns, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/proyectos/_hooks/useProjectsPage.ts, frontend/src/app/(dashboard)/proyectos/_components/NewProjectModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/proyectos/proyectos/_components/CreateProjectModal.tsx` (tsx, 49 loc)
  symbols: export function CreateProjectModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/proyectos/proyectos/_components/EditProjectModal.tsx` (tsx, 58 loc)
  symbols: export function EditProjectModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/proyectos/proyectos/_hooks/useProyectosListado.ts` (ts, 112 loc)
  symbols: export const getStatusConfig; export const statusConfig; export function useProyectosListado
  imports: @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/proyectos/proyectos/page.tsx` (tsx, 128 loc)
  symbols: export function ProyectosListado
  imports: @/components, @/lib, lucide-react, next, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/app/(dashboard)/proyectos/proyectos/_hooks/useProyectosListado.ts, frontend/src/app/(dashboard)/proyectos/proyectos/_components/CreateProjectModal.tsx, frontend/src/app/(dashboard)/proyectos/proyectos/_components/EditProjectModal.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/proyectos/tareas/_components/CreateTaskModal.tsx` (tsx, 67 loc)
  symbols: export function CreateTaskModal
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/proyectos/tareas/_components/EditTaskModal.tsx` (tsx, 67 loc)
  symbols: export function EditTaskModal
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/proyectos/tareas/_components/KanbanColumn.tsx` (tsx, 128 loc)
  symbols: export function KanbanColumn
  imports: @/lib, date-fns, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/proyectos/tareas/_hooks/useTasksKanban.ts
`frontend/src/app/(dashboard)/proyectos/tareas/_hooks/useTasksKanban.ts` (ts, 164 loc)
  symbols: export function useTasksKanban
  imports: @/lib, @/stores, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/proyectos/tareas/page.tsx` (tsx, 101 loc)
  symbols: export function TasksKanbanPage; function TasksKanbanContent
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/app/(dashboard)/proyectos/tareas/_hooks/useTasksKanban.ts, frontend/src/app/(dashboard)/proyectos/tareas/_components/KanbanColumn.tsx, frontend/src/app/(dashboard)/proyectos/tareas/_components/CreateTaskModal.tsx, frontend/src/app/(dashboard)/proyectos/tareas/_components/EditTaskModal.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/rrhh/analisis-cv/page.tsx` (tsx, 8 loc)
  symbols: export function AnalisisCvRedirect
  imports: next
`frontend/src/app/(dashboard)/rrhh/documentos/_components/DocumentCard.tsx` (tsx, 157 loc)
  symbols: export function DocumentCard; function StatusBadge
  imports: @/components, @/hooks, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/components/GenerativeUI.tsx, frontend/src/hooks/useFormat.ts, frontend/src/lib/api/hr_documents.ts, frontend/src/lib/api/signing.ts, frontend/src/stores/toast.ts, frontend/src/app/(dashboard)/rrhh/documentos/_hooks/useHRDocumentos.ts
`frontend/src/app/(dashboard)/rrhh/documentos/_hooks/useHRDocumentos.ts` (ts, 115 loc)
  symbols: export function parseNLIntent; export const DOC_TYPES; export const DOC_TEMPLATE_KEYS; export function useHRDocumentos
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api/hr_documents.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/rrhh/documentos/page.tsx` (tsx, 110 loc)
  symbols: export function HRDocumentosPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/rrhh/documentos/_hooks/useHRDocumentos.ts, frontend/src/app/(dashboard)/rrhh/documentos/_components/DocumentCard.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/select.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/rrhh/empleados/_components/EmpleadoFormModal.tsx` (tsx, 231 loc)
  symbols: export function EmpleadoFormModal
  imports: @/components, next-intl
  → usa: frontend/src/components/shared/index.ts, frontend/src/components/ui/input.tsx, frontend/src/components/ui/select.tsx, frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleadosTypes.ts
`frontend/src/app/(dashboard)/rrhh/empleados/_components/EmployeeDocsModal.tsx` (tsx, 133 loc)
  symbols: export function EmployeeDocsModal; function formatSize; function fileIcon
  imports: @/hooks, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/lib/api.ts, frontend/src/lib/api/hr.ts
`frontend/src/app/(dashboard)/rrhh/empleados/_components/PayrollDrawer.tsx` (tsx, 115 loc)
  symbols: export function PayrollDrawer
  imports: @/hooks, @/lib, date-fns, lucide-react, next, next-intl
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleados.tsx` (tsx, 57 loc) — Composer: combines CRUD + upload concerns…
  symbols: export function useEmpleados
  imports: @/lib, @tanstack/react-table
  → usa: frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleadosCRUD.tsx, frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleadosUpload.ts, frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleadosTypes.ts, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleadosCRUD.tsx` (tsx, 294 loc)
  symbols: export function useEmpleadosCRUD; function EmployeeStatusBadge
  imports: @/components, @/hooks, @/lib, @/stores, @tanstack/react-table, lucide-react, next-intl, react
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/lib/api.ts, frontend/src/stores/notifications.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts, frontend/src/components/data-table/index.ts, frontend/src/components/ui/badge.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleadosTypes.ts
`frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleadosTypes.ts` (ts, 44 loc) — Shared types and constants for empleados hooks
  symbols: export const EMPTY_FORM; export const STATUS_OPTIONS; export const LEAVE_TYPE_OPTIONS
`frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleadosUpload.ts` (ts, 11 loc) — Manages which employee's document modal is open
  symbols: export function useEmpleadosUpload
  imports: @/lib, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/rrhh/empleados/page.tsx` (tsx, 146 loc)
  symbols: export function EmployeesPage
  imports: @/components, @/hooks, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/app/(dashboard)/rrhh/empleados/_hooks/useEmpleados.tsx, frontend/src/app/(dashboard)/rrhh/empleados/_components/EmployeeDocsModal.tsx, frontend/src/app/(dashboard)/rrhh/empleados/_components/EmpleadoFormModal.tsx, frontend/src/app/(dashboard)/rrhh/empleados/_components/PayrollDrawer.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/KpiCard.tsx, frontend/src/components/ui/EmptyState.tsx, frontend/src/components/data-table/index.ts, frontend/src/components/ui/button.tsx (+4)
`frontend/src/app/(dashboard)/rrhh/fichajes/FichajesPanel.tsx` (tsx, 204 loc)
  symbols: export function FichajesPanel; function ElapsedCell
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/select.tsx, frontend/src/components/ui/input.tsx, frontend/src/app/(dashboard)/rrhh/fichajes/_hooks/useFichajes.ts
`frontend/src/app/(dashboard)/rrhh/fichajes/_hooks/useFichajes.ts` (ts, 119 loc)
  symbols: export function useElapsedTime; export function useFichajes
  imports: @/hooks, @/lib, @/stores, next-intl, react
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts, frontend/src/lib/hooks/usePolling.ts
`frontend/src/app/(dashboard)/rrhh/fichajes/page.tsx` (tsx, 7 loc)
  symbols: export function FichajesRedirect
  imports: next
`frontend/src/app/(dashboard)/rrhh/gastos/page.tsx` (tsx, 469 loc)
  symbols: export function GastosPage
  imports: @/components, @/hooks, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/components/ui/button.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/KpiCard.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/select.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx (+1)
`frontend/src/app/(dashboard)/rrhh/horarios/HorariosPanel.tsx` (tsx, 361 loc)
  symbols: export function HorariosPanel; function handleAISuggest; function handleExport; function handleSendEmail
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/card.tsx, frontend/src/components/ui/badge.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/stores/toast.ts, frontend/src/lib/api.ts, frontend/src/app/(dashboard)/rrhh/horarios/_hooks/useHorarios.ts
`frontend/src/app/(dashboard)/rrhh/horarios/_hooks/useHorarios.ts` (ts, 171 loc)
  symbols: export const DAYS; export function calcWeeklyHours; export function useHorarios; export function buildScheduleHTML; function parseMinutes; function buildGrid
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/rrhh/horarios/page.tsx` (tsx, 7 loc)
  symbols: export function HorariosRedirect
  imports: next
`frontend/src/app/(dashboard)/rrhh/jornada/page.tsx` (tsx, 56 loc)
  symbols: export function JornadaPage
  imports: @/components, lucide-react, next, next-intl, react
  → usa: frontend/src/app/(dashboard)/rrhh/horarios/HorariosPanel.tsx, frontend/src/app/(dashboard)/rrhh/fichajes/FichajesPanel.tsx, frontend/src/app/(dashboard)/rrhh/vacaciones/VacacionesPanel.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/rrhh/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/rrhh/nominas/_components/AutoPayrollModal.tsx` (tsx, 130 loc)
  symbols: export function AutoPayrollModal
  imports: @/hooks, @/lib, date-fns, lucide-react, next-intl
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/rrhh/nominas/_components/PayrollFilters.tsx` (tsx, 49 loc)
  symbols: export function PayrollFilters
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/rrhh/nominas/_components/PayrollStatusBadge.tsx` (tsx, 13 loc)
  symbols: export function PayrollStatusBadge
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/rrhh/nominas/_components/PayrollTable.tsx` (tsx, 105 loc)
  symbols: export function PayrollTable; function devengoExtras
  imports: @/hooks, @/lib, lucide-react, next-intl
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/lib/api.ts, frontend/src/app/(dashboard)/rrhh/nominas/_components/PayrollStatusBadge.tsx
`frontend/src/app/(dashboard)/rrhh/nominas/_hooks/usePayrolls.ts` (ts, 199 loc)
  symbols: export function usePayrolls
  imports: @/hooks, @/lib, @/stores, date-fns, next-intl, react
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/lib/api.ts, frontend/src/lib/logger.ts, frontend/src/stores/notifications.ts
`frontend/src/app/(dashboard)/rrhh/nominas/page.tsx` (tsx, 124 loc)
  symbols: export function PayrollsPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/components/shared/KpiCard.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/rrhh/nominas/_hooks/usePayrolls.ts, frontend/src/app/(dashboard)/rrhh/nominas/_components/AutoPayrollModal.tsx, frontend/src/app/(dashboard)/rrhh/nominas/_components/PayrollFilters.tsx, frontend/src/app/(dashboard)/rrhh/nominas/_components/PayrollTable.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/rrhh/page.tsx` (tsx, 135 loc)
  symbols: export async function RRHHPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/rrhh/reclutamiento/_components/CandidateList.tsx` (tsx, 225 loc)
  symbols: export function CandidateList; function CandidateCard
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api/recruitment.ts
`frontend/src/app/(dashboard)/rrhh/reclutamiento/_components/CreatePositionModal.tsx` (tsx, 80 loc)
  symbols: export function CreatePositionModal
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/rrhh/reclutamiento/_components/CvAnalysisTab.tsx` (tsx, 175 loc)
  symbols: export function CvAnalysisTab
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/recruitment.ts, frontend/src/stores/toast.ts, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/rrhh/reclutamiento/_hooks/useAnalisisCV.ts
`frontend/src/app/(dashboard)/rrhh/reclutamiento/_components/PositionList.tsx` (tsx, 59 loc)
  symbols: export function PositionList
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api/recruitment.ts
`frontend/src/app/(dashboard)/rrhh/reclutamiento/_hooks/useAnalisisCV.ts` (ts, 71 loc)
  symbols: export function useAnalisisCV
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api/client.ts
`frontend/src/app/(dashboard)/rrhh/reclutamiento/_hooks/useRecruitment.ts` (ts, 84 loc)
  symbols: export function useRecruitment
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/recruitment.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/rrhh/reclutamiento/page.tsx` (tsx, 114 loc)
  symbols: export function RecruitmentPage
  imports: @/components, lucide-react, next, next-intl, react
  → usa: frontend/src/app/(dashboard)/rrhh/reclutamiento/_hooks/useRecruitment.ts, frontend/src/app/(dashboard)/rrhh/reclutamiento/_components/PositionList.tsx, frontend/src/app/(dashboard)/rrhh/reclutamiento/_components/CandidateList.tsx, frontend/src/app/(dashboard)/rrhh/reclutamiento/_components/CreatePositionModal.tsx, frontend/src/app/(dashboard)/rrhh/reclutamiento/_components/CvAnalysisTab.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/rrhh/vacaciones/VacacionesPanel.tsx` (tsx, 275 loc)
  symbols: export function VacacionesPanel; function daysBetween
  imports: @/components, @/hooks, lucide-react, next-intl
  → usa: frontend/src/hooks/useFormat.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/select.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/label.tsx, frontend/src/app/(dashboard)/rrhh/vacaciones/_hooks/useVacaciones.ts
`frontend/src/app/(dashboard)/rrhh/vacaciones/_hooks/useVacaciones.ts` (ts, 150 loc)
  symbols: export const LEAVE_TYPE_LABEL_KEYS; export const STATUS_LABEL_KEYS; export function useVacaciones
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/rrhh/vacaciones/page.tsx` (tsx, 7 loc)
  symbols: export function VacacionesRedirect
  imports: next
`frontend/src/app/(dashboard)/tareas/page.tsx` (tsx, 6 loc)
  symbols: export function TareasRedirect
  imports: next
`frontend/src/app/(dashboard)/tesoreria/cashflow/_hooks/useCashflow.ts` (ts, 83 loc)
  symbols: export function useCashflow
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/tesoreria/cashflow/page.tsx` (tsx, 115 loc)
  symbols: export function CashflowPage
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/app/(dashboard)/tesoreria/cashflow/_hooks/useCashflow.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/tesoreria/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/tesoreria/page.tsx` (tsx, 74 loc)
  symbols: export async function TesoreriaPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_components/DueBadge.tsx` (tsx, 36 loc)
  symbols: export function DueBadge
  imports: date-fns, lucide-react, next-intl
`frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_components/InvoiceTable.tsx` (tsx, 75 loc)
  symbols: export function InvoiceTable
  imports: @/lib, date-fns, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_components/DueBadge.tsx
`frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_components/KpiCards.tsx` (tsx, 107 loc)
  symbols: export function KpiCards
  imports: @/lib, date-fns, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_components/TransactionsTable.tsx` (tsx, 75 loc)
  symbols: export function TransactionsTable
  imports: @/lib, date-fns, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/lib/utils.ts
`frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_hooks/usePagosYCobros.tsx` (tsx, 90 loc)
  symbols: export function usePagosYCobros
  imports: @/lib, @/stores, date-fns, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/page.tsx` (tsx, 80 loc)
  symbols: export function PagosYCobrosPage
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_hooks/usePagosYCobros.tsx, frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_components/KpiCards.tsx, frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_components/InvoiceTable.tsx, frontend/src/app/(dashboard)/tesoreria/pagos-y-cobros/_components/TransactionsTable.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/tesoreria/remesas/_components/RemesaHistorial.tsx` (tsx, 117 loc)
  symbols: export function RemesaHistorial
  imports: @/components, @/lib, lucide-react, next-intl, react
  → usa: frontend/src/lib/utils.ts, frontend/src/components/ui/button.tsx, frontend/src/lib/api/treasury.ts
`frontend/src/app/(dashboard)/tesoreria/remesas/_components/RemesaItemList.tsx` (tsx, 86 loc)
  symbols: export function RemesaItemList
  imports: @/lib, date-fns, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/app/(dashboard)/tesoreria/remesas/_hooks/useRemesas.tsx
`frontend/src/app/(dashboard)/tesoreria/remesas/_components/RemesaModal.tsx` (tsx, 83 loc)
  symbols: export function RemesaModal
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/tesoreria/remesas/_components/RemesaSummary.tsx` (tsx, 45 loc)
  symbols: export function RemesaSummary
  imports: @/lib, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/app/(dashboard)/tesoreria/remesas/_hooks/useRemesas.tsx
`frontend/src/app/(dashboard)/tesoreria/remesas/_hooks/useRemesas.tsx` (tsx, 168 loc)
  symbols: export const TYPE_CONFIG; export function useRemesas; function useAgentTask
  imports: @/lib, date-fns, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/tesoreria/remesas/page.tsx` (tsx, 106 loc)
  symbols: export function RemesasPage
  imports: @/components, @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/utils.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/tesoreria/remesas/_hooks/useRemesas.tsx, frontend/src/app/(dashboard)/tesoreria/remesas/_components/RemesaItemList.tsx, frontend/src/app/(dashboard)/tesoreria/remesas/_components/RemesaSummary.tsx, frontend/src/app/(dashboard)/tesoreria/remesas/_components/RemesaModal.tsx, frontend/src/app/(dashboard)/tesoreria/remesas/_components/RemesaHistorial.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/tpv/_components/BarcodeScanner.tsx` (tsx, 157 loc)
  symbols: export function BarcodeScanner
  imports: @/components, lucide-react, next-intl, react
  → usa: frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/tpv/_components/PaymentModal.tsx` (tsx, 64 loc)
  symbols: export function PaymentModal
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/tpv/_hooks/usePos.ts` (ts, 207 loc)
  symbols: export function usePos
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/tpv/page.tsx` (tsx, 263 loc)
  symbols: export function TpvPage
  imports: @/components, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/app/(dashboard)/tpv/_hooks/usePos.ts, frontend/src/app/(dashboard)/tpv/_components/BarcodeScanner.tsx, frontend/src/app/(dashboard)/tpv/_components/PaymentModal.tsx, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/ventas/facturacion-electronica/page.tsx` (tsx, 187 loc)
  symbols: export function FacturacionElectronicaPage
  imports: @/components, @/lib, @/stores, lucide-react, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/shared/KpiCard.tsx, frontend/src/stores/toast.ts, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/ventas/facturas/[id]/_hooks/useFacturaDetalle.ts` (ts, 109 loc)
  symbols: export function useFacturaDetalle
  imports: @/lib, @/stores, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/app/(dashboard)/ventas/facturas/[id]/page.tsx` (tsx, 210 loc)
  symbols: export function FacturaDetallePage
  imports: @/components, lucide-react, next
  → usa: frontend/src/app/(dashboard)/ventas/facturas/[id]/_hooks/useFacturaDetalle.ts, frontend/src/components/ui/button.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/ventas/facturas/_hooks/useFacturas.tsx` (tsx, 207 loc)
  symbols: export function useFacturas
  imports: @/components, @/lib, @/stores, @tanstack/react-table, lucide-react, next, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/notifications.ts, frontend/src/stores/confirm.ts, frontend/src/components/data-table/index.ts, frontend/src/components/shared/StatusBadge.tsx, frontend/src/components/ui/button.tsx
`frontend/src/app/(dashboard)/ventas/facturas/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/ventas/facturas/nueva/_components/InvoiceHeader.tsx` (tsx, 98 loc)
  symbols: export function InvoiceHeader
  imports: @/lib, next-intl
  → usa: frontend/src/lib/api.ts
`frontend/src/app/(dashboard)/ventas/facturas/nueva/_components/InvoiceLinesTable.tsx` (tsx, 106 loc)
  symbols: export function InvoiceLinesTable
  imports: @/lib, lucide-react, next-intl
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/ventas/facturas/nueva/_hooks/useNuevaFactura.tsx
`frontend/src/app/(dashboard)/ventas/facturas/nueva/_components/InvoiceTotals.tsx` (tsx, 49 loc)
  symbols: export function InvoiceTotals
  imports: lucide-react, next, next-intl
`frontend/src/app/(dashboard)/ventas/facturas/nueva/_hooks/useNuevaFactura.tsx` (tsx, 128 loc)
  symbols: export function emptyLine; export function calcLine; export function useNuevaFactura
  imports: @/lib, @/stores, next, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts
`frontend/src/app/(dashboard)/ventas/facturas/nueva/page.tsx` (tsx, 60 loc)
  symbols: export function NuevaFacturaPage; function NuevaFacturaContent
  imports: @/components, lucide-react, next, next-intl, react
  → usa: frontend/src/app/(dashboard)/ventas/facturas/nueva/_hooks/useNuevaFactura.tsx, frontend/src/app/(dashboard)/ventas/facturas/nueva/_components/InvoiceHeader.tsx, frontend/src/app/(dashboard)/ventas/facturas/nueva/_components/InvoiceLinesTable.tsx, frontend/src/app/(dashboard)/ventas/facturas/nueva/_components/InvoiceTotals.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/ventas/facturas/page.tsx` (tsx, 90 loc)
  symbols: export function FacturasPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/ui/input.tsx, frontend/src/components/data-table/index.ts, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/shared/KpiCard.tsx, frontend/src/components/ui/EmptyState.tsx, frontend/src/components/ui/button.tsx, frontend/src/app/(dashboard)/ventas/facturas/_hooks/useFacturas.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/ventas/loading.tsx` (tsx, 8 loc)
  symbols: export function Loading
`frontend/src/app/(dashboard)/ventas/page.tsx` (tsx, 90 loc)
  symbols: export async function VentasPage
  imports: @/components, lucide-react, next, next-intl
  → usa: frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/ventas/pedidos/_components/OrderCard.tsx` (tsx, 95 loc)
  symbols: export function OrderCard
  imports: @/lib, lucide-react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/ventas/pedidos/_hooks/usePedidos.tsx
`frontend/src/app/(dashboard)/ventas/pedidos/_components/OrderModal.tsx` (tsx, 164 loc)
  symbols: export function OrderModal
  imports: @/lib, lucide-react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/ventas/pedidos/_hooks/usePedidos.tsx
`frontend/src/app/(dashboard)/ventas/pedidos/_hooks/usePedidos.tsx` (tsx, 173 loc)
  symbols: export const fmt; export const STATUS_MAP; export const STATUS_FLOW; export function usePedidos
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/ventas/pedidos/page.tsx` (tsx, 106 loc)
  symbols: export function PedidosPage
  imports: @/components, lucide-react
  → usa: frontend/src/app/(dashboard)/ventas/pedidos/_hooks/usePedidos.tsx, frontend/src/app/(dashboard)/ventas/pedidos/_components/OrderCard.tsx, frontend/src/app/(dashboard)/ventas/pedidos/_components/OrderModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/ventas/presupuestos/_components/QuoteModal.tsx` (tsx, 148 loc)
  symbols: export function QuoteModal
  imports: @/lib, lucide-react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/ventas/presupuestos/_hooks/usePresupuestos.tsx
`frontend/src/app/(dashboard)/ventas/presupuestos/_components/QuoteToast.tsx` (tsx, 25 loc)
  symbols: export function QuoteToast
  imports: lucide-react, next-intl
`frontend/src/app/(dashboard)/ventas/presupuestos/_components/QuotesTable.tsx` (tsx, 134 loc)
  symbols: export function QuotesTable; function StatusBadge
  imports: @/lib, date-fns, lucide-react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/ventas/presupuestos/_hooks/usePresupuestos.tsx
`frontend/src/app/(dashboard)/ventas/presupuestos/_hooks/usePresupuestos.tsx` (tsx, 156 loc)
  symbols: export const formatCurrency; export function usePresupuestos
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/ventas/presupuestos/page.tsx` (tsx, 88 loc)
  symbols: export function QuotesPage
  imports: @/components, lucide-react
  → usa: frontend/src/app/(dashboard)/ventas/presupuestos/_hooks/usePresupuestos.tsx, frontend/src/app/(dashboard)/ventas/presupuestos/_components/QuotesTable.tsx, frontend/src/app/(dashboard)/ventas/presupuestos/_components/QuoteModal.tsx, frontend/src/app/(dashboard)/ventas/presupuestos/_components/QuoteToast.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/ventas/recurrentes/_components/RecurringList.tsx` (tsx, 99 loc)
  symbols: export function RecurringList
  imports: @/lib, lucide-react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/ventas/recurrentes/_hooks/useRecurrentes.tsx
`frontend/src/app/(dashboard)/ventas/recurrentes/_components/RecurringModal.tsx` (tsx, 131 loc)
  symbols: export function RecurringModal
  imports: @/lib, lucide-react
  → usa: frontend/src/lib/api.ts, frontend/src/app/(dashboard)/ventas/recurrentes/_hooks/useRecurrentes.tsx
`frontend/src/app/(dashboard)/ventas/recurrentes/_hooks/useRecurrentes.tsx` (tsx, 181 loc)
  symbols: export const fmt; export const INTERVAL_MAP; export const INTERVAL_COLORS; export function useRecurrentes
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/ventas/recurrentes/page.tsx` (tsx, 110 loc)
  symbols: export function RecurrentesPage
  imports: @/components, lucide-react
  → usa: frontend/src/app/(dashboard)/ventas/recurrentes/_hooks/useRecurrentes.tsx, frontend/src/app/(dashboard)/ventas/recurrentes/_components/RecurringList.tsx, frontend/src/app/(dashboard)/ventas/recurrentes/_components/RecurringModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/(dashboard)/ventas/servicios/_components/ServiceModal.tsx` (tsx, 112 loc)
  symbols: export function ServiceModal
  imports: lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/ventas/servicios/_hooks/useServicios.ts
`frontend/src/app/(dashboard)/ventas/servicios/_hooks/useServicios.ts` (ts, 108 loc)
  symbols: export const emptyForm; export const fmt; export function useServicios
  imports: @/lib, @/stores, next-intl, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/lib/logger.ts
`frontend/src/app/(dashboard)/ventas/servicios/page.tsx` (tsx, 138 loc)
  symbols: export function ServicesPage
  imports: @/components, lucide-react, next-intl
  → usa: frontend/src/app/(dashboard)/ventas/servicios/_hooks/useServicios.ts, frontend/src/app/(dashboard)/ventas/servicios/_components/ServiceModal.tsx, frontend/src/components/shared/PageHeader.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/shared/PageContainer.tsx
`frontend/src/app/error.tsx` (tsx, 51 loc)
  symbols: export function RootError
  imports: @/lib, next-intl, react
  → usa: frontend/src/lib/error-reporter.ts
`frontend/src/app/global-error.tsx` (tsx, 40 loc) — Global error boundary — catches errors in root layout…
  symbols: export function GlobalError
  imports: @/lib, react
  → usa: frontend/src/lib/error-reporter.ts
`frontend/src/app/layout.tsx` (tsx, 56 loc)
  symbols: export const metadata; export async function RootLayout
  imports: @/components, next, next-intl, next-themes
  → usa: frontend/src/components/GlobalErrorListener.tsx, frontend/src/components/LicenseListener.tsx
`frontend/src/app/mobile-scanner/page.tsx` (tsx, 282 loc)
  symbols: export function MobileScannerPage; function MobileScannerInner
  imports: @/lib, lucide-react, next, react
  → usa: frontend/src/lib/api/scanner.ts
`frontend/src/app/not-found.tsx` (tsx, 24 loc)
  symbols: export function NotFound
  imports: next, next-intl
`frontend/src/app/portal-cliente/layout.tsx` (tsx, 21 loc) — Layout del portal de cliente: vive fuera del dashboard, así que monta su propio ToastContainer (auditoría UIX #4 — sin alert() nativos)
  symbols: export function PortalClienteLayout
  imports: @/components
  → usa: frontend/src/components/ui/ToastContainer.tsx
`frontend/src/app/portal-cliente/page.tsx` (tsx, 263 loc)
  symbols: export function PortalClientePage
  imports: @/lib, @/stores, lucide-react, react
  → usa: frontend/src/lib/api/client_portal.ts, frontend/src/stores/toast.ts
`frontend/src/components/ConfirmDialog.tsx` (tsx, 77 loc)
  symbols: export function ConfirmDialog
  imports: @/stores, lucide-react
  → usa: frontend/src/stores/confirm.ts
`frontend/src/components/ContractTemplateEditor.tsx` (tsx, 199 loc) — Editor TipTap embebido para plantillas .docx (V2 del plan)…
  symbols: export function ContractTemplateEditor; function ToolbarBtn
  imports: @/lib, @/stores, @tiptap/react, @tiptap/starter-kit, lucide-react, react
  → usa: frontend/src/lib/api/documents.ts, frontend/src/stores/toast.ts, frontend/src/lib/utils.ts
`frontend/src/components/GenerativeUI.tsx` (tsx, 6 loc)
  → usa: frontend/src/components/_hooks/useGenerativeUI.ts
`frontend/src/components/GlobalErrorListener.tsx` (tsx, 72 loc) — Captura errores que se escapan a los error boundaries de Next: - `window.onerror` → excepciones síncronas no manejadas - `window.onunhandled…
  symbols: export function GlobalErrorListener
  imports: @/lib, @/stores, react
  → usa: frontend/src/lib/error-reporter.ts, frontend/src/lib/api/errors.ts, frontend/src/stores/toast.ts
`frontend/src/components/InfoBanner.tsx` (tsx, 50 loc)
  symbols: export function InfoBanner
  imports: lucide-react, react
`frontend/src/components/LicenseListener.tsx` (tsx, 48 loc)
  symbols: export function LicenseListener
  imports: @/lib, @/stores, react
  → usa: frontend/src/stores/license.ts, frontend/src/lib/api/license.ts, frontend/src/components/LicenseModal.tsx
`frontend/src/components/LicenseModal.tsx` (tsx, 122 loc)
  symbols: export function LicenseModal; function handleActivate
  imports: @/lib, @/stores, lucide-react, react
  → usa: frontend/src/lib/api/license.ts, frontend/src/stores/license.ts
`frontend/src/components/NotificationBell.tsx` (tsx, 128 loc)
  symbols: export function NotificationBell; function timeAgo; function handleClick; function handleOpen
  imports: @/stores, lucide-react, react
  → usa: frontend/src/stores/notifications.ts
`frontend/src/components/ProfileMenu.tsx` (tsx, 167 loc)
  symbols: export function ProfileMenu; function readJwt; function handleClick; function logout
  imports: @/lib, lucide-react, next, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/client.ts
`frontend/src/components/Workflows/CustomNodes.tsx` (tsx, 253 loc)
  symbols: export const TriggerNode; export const SkillNode; export const ConditionalNode; export const DelayNode; export const ApprovalGateNode; export const ActionNode; export const customNodeTypes; function fmtElapsed; function NodeRuntimeOverlay; function getRuntime; function getDomainIcon
  imports: lucide-react, react, reactflow
`frontend/src/components/Workflows/NodeConfigPanel.tsx` (tsx, 143 loc)
  symbols: export function NodeConfigPanel
  imports: lucide-react, reactflow
`frontend/src/components/Workflows/WorkflowGraph.tsx` (tsx, 299 loc) — Estado en vivo de cada nodo proveniente del WS (useWorkflowExecution)…
  symbols: export function WorkflowGraph; function WorkflowGraphInner
  imports: react, reactflow
  → usa: frontend/src/components/Workflows/CustomNodes.tsx, frontend/src/components/Workflows/WorkflowToolbar.tsx, frontend/src/components/Workflows/NodeConfigPanel.tsx
`frontend/src/components/Workflows/WorkflowToolbar.tsx` (tsx, 52 loc)
  symbols: export function WorkflowToolbar
  imports: lucide-react
`frontend/src/components/_hooks/useGenerativeUI.ts` (ts, 170 loc)
  symbols: export function sanitizeHTML; export function useGenerativeUI; function resolveAction; function pollTask
  imports: @/lib, @/stores, dompurify, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts
`frontend/src/components/ai/AIDisclosureBanner.tsx` (tsx, 73 loc) — AI.BAN — Banner de transparencia Art…
  symbols: export function AIDisclosureBanner
  imports: lucide-react, react
`frontend/src/components/ai/AIGenerationFooter.tsx` (tsx, 38 loc) — AI.BAN — Footer de trazabilidad mostrado bajo cada respuesta del agente…
  symbols: export function AIGenerationFooter
`frontend/src/components/ai/CostModal.tsx` (tsx, 180 loc) — UI.COST — modal post-abort que muestra tokens y coste estimado…
  symbols: export function CostModal
  imports: @/lib, lucide-react, react
  → usa: frontend/src/lib/api/taskStream.ts
`frontend/src/components/data-table/DataTable.tsx` (tsx, 127 loc)
  symbols: export function DataTable
  imports: @/components, @tanstack/react-table, react
  → usa: frontend/src/components/ui/table.tsx, frontend/src/components/data-table/DataTablePagination.tsx, frontend/src/components/data-table/DataTableToolbar.tsx, frontend/src/components/data-table/DataTableSkeleton.tsx
`frontend/src/components/data-table/DataTableColumnHeader.tsx` (tsx, 63 loc)
  symbols: export function DataTableColumnHeader
  imports: @/components, @/lib, @tanstack/react-table, lucide-react
  → usa: frontend/src/lib/utils.ts, frontend/src/components/ui/button.tsx, frontend/src/components/ui/dropdown-menu.tsx
`frontend/src/components/data-table/DataTableFacetedFilter.tsx` (tsx, 114 loc)
  symbols: export function DataTableFacetedFilter
  imports: @/components, @/lib, @tanstack/react-table, lucide-react
  → usa: frontend/src/lib/utils.ts, frontend/src/components/ui/badge.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/ui/command.tsx, frontend/src/components/ui/popover.tsx, frontend/src/components/ui/separator.tsx
`frontend/src/components/data-table/DataTablePagination.tsx` (tsx, 58 loc)
  symbols: export function DataTablePagination
  imports: @/components, @tanstack/react-table, lucide-react
  → usa: frontend/src/components/ui/button.tsx, frontend/src/components/ui/select.tsx
`frontend/src/components/data-table/DataTableSkeleton.tsx` (tsx, 34 loc)
  symbols: export function DataTableSkeleton
  imports: @/components
  → usa: frontend/src/components/ui/skeleton.tsx
`frontend/src/components/data-table/DataTableToolbar.tsx` (tsx, 100 loc)
  symbols: export function DataTableToolbar
  imports: @/components, @tanstack/react-table, lucide-react
  → usa: frontend/src/components/ui/button.tsx, frontend/src/components/ui/input.tsx, frontend/src/components/ui/dropdown-menu.tsx, frontend/src/components/data-table/DataTableFacetedFilter.tsx
`frontend/src/components/data-table/__tests__/DataTable.test.tsx` (tsx, 115 loc)
  imports: @/test-utils, @tanstack/react-table, vitest
  → usa: frontend/src/test-utils/render.tsx, frontend/src/components/data-table/DataTable.tsx
`frontend/src/components/data-table/index.ts` (ts, 7 loc)
`frontend/src/components/documentos/ContractWizard.tsx` (tsx, 193 loc) — Asistente conversacional: la IA entrevista al usuario una pregunta a la vez y al terminar redacta el contrato profesional, que se puede guar…
  symbols: export function ContractWizard
  imports: @/lib, @/stores, lucide-react, react
  → usa: frontend/src/lib/api/documents.ts, frontend/src/stores/toast.ts, frontend/src/lib/logger.ts
`frontend/src/components/documentos/DocCard.tsx` (tsx, 182 loc)
  symbols: export function DocCard; function handleDownload; function handleCancel; function handleDelete
  imports: @/lib, @/stores, lucide-react, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/components/documentos/shared.ts
`frontend/src/components/documentos/DocRow.tsx` (tsx, 136 loc)
  symbols: export function DocRow; function handleDownload; function handleCancel; function handleDelete
  imports: @/lib, @/stores, lucide-react, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts, frontend/src/stores/confirm.ts, frontend/src/components/documentos/shared.ts
`frontend/src/components/documentos/DocSemanticSearch.tsx` (tsx, 84 loc) — Búsqueda semántica (RAG) sobre los documentos del tenant: devuelve los fragmentos más relevantes con su similitud…
  symbols: export function DocSemanticSearch
  imports: @/lib, lucide-react, react
  → usa: frontend/src/lib/api/documents.ts, frontend/src/lib/logger.ts
`frontend/src/components/documentos/RagChatBox.tsx` (tsx, 126 loc)
  symbols: export function RagChatBox; function handleChat
  imports: @/lib, lucide-react, react
  → usa: frontend/src/lib/api.ts
`frontend/src/components/documentos/RestoreModal.tsx` (tsx, 98 loc)
  symbols: export function RestoreModal
  imports: @/lib, @/stores, lucide-react, react
  → usa: frontend/src/lib/api.ts, frontend/src/stores/toast.ts
`frontend/src/components/documentos/shared.ts` (ts, 24 loc)
  symbols: export const STATUS_STYLE; export function fileIcon; export function formatSize
  imports: lucide-react
`frontend/src/components/layout/Breadcrumbs.tsx` (tsx, 46 loc)
  symbols: export function Breadcrumbs
  imports: lucide-react, next
  → usa: frontend/src/components/layout/nav-config.ts
`frontend/src/components/layout/GlobalSearch.tsx` (tsx, 175 loc)
  symbols: export function GlobalSearch; function groupResults
  imports: @/components, @/lib, lucide-react, next, react
  → usa: frontend/src/components/ui/command.tsx, frontend/src/components/layout/nav-config.ts, frontend/src/lib/api.ts
`frontend/src/components/layout/Header.tsx` (tsx, 22 loc)
  symbols: export function Header
  imports: @/components
  → usa: frontend/src/components/layout/Breadcrumbs.tsx, frontend/src/components/layout/GlobalSearch.tsx, frontend/src/components/layout/ThemeToggle.tsx, frontend/src/components/NotificationBell.tsx, frontend/src/components/ProfileMenu.tsx
`frontend/src/components/layout/Sidebar.tsx` (tsx, 332 loc)
  symbols: export function Sidebar
  imports: @/components, @/hooks, @/lib, @/stores, lucide-react, next, react
  → usa: frontend/src/components/ui/logo-svg.tsx, frontend/src/lib/utils.ts, frontend/src/components/ui/scroll-area.tsx, frontend/src/components/layout/nav-config.ts, frontend/src/components/layout/_hooks/useSidebar.ts, frontend/src/hooks/useUserRole.ts, frontend/src/stores/license.ts, frontend/src/lib/plans.ts, frontend/src/lib/hooks/usePendingApprovalsCount.ts
`frontend/src/components/layout/ThemeToggle.tsx` (tsx, 29 loc)
  symbols: export function ThemeToggle
  imports: @/components, lucide-react, next-themes, react
  → usa: frontend/src/components/ui/button.tsx
`frontend/src/components/layout/_hooks/useSidebar.ts` (ts, 112 loc)
  symbols: export function useSidebar
  imports: @/stores, next, react
  → usa: frontend/src/components/layout/nav-config.ts, frontend/src/stores/confirm.ts, frontend/src/stores/navigationGuard.ts
`frontend/src/components/layout/index.ts` (ts, 6 loc)
`frontend/src/components/layout/nav-config.ts` (ts, 217 loc) — Marca el item como núcleo de la app — se renderiza con un color destacado en el sidebar
  symbols: export const NAV_SECTIONS; export const ROUTE_LABELS
  imports: lucide-react
`frontend/src/components/settings/UpdateChannelSelector.tsx` (tsx, 123 loc) — DIS.UPD — selector de canal de actualización (stable / beta)…
  symbols: export function UpdateChannelSelector; function _api; function choose
  imports: @/stores, lucide-react, react
  → usa: frontend/src/stores/toast.ts
`frontend/src/components/shared/FormField.tsx` (tsx, 26 loc)
  symbols: export function FormField
  imports: @/components, @/lib
  → usa: frontend/src/components/ui/label.tsx, frontend/src/lib/utils.ts
`frontend/src/components/shared/FormModal.tsx` (tsx, 67 loc)
  symbols: export function FormModal
  imports: @/components, lucide-react
  → usa: frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/button.tsx
`frontend/src/components/shared/ImportCsvModal.tsx` (tsx, 258 loc)
  symbols: export function ImportCsvModal
  imports: @/components, @/lib, lucide-react, react
  → usa: frontend/src/components/ui/dialog.tsx, frontend/src/components/ui/button.tsx, frontend/src/lib/utils/parse-csv.ts, frontend/src/lib/utils/export-csv.ts
`frontend/src/components/shared/KpiCard.tsx` (tsx, 55 loc)
  symbols: export function KpiCard
  imports: @/components, @/lib, lucide-react
  → usa: frontend/src/components/ui/card.tsx, frontend/src/lib/utils.ts
`frontend/src/components/shared/LlmNotConfiguredBanner.tsx` (tsx, 58 loc) — Aviso cuando el tenant no tiene ninguna clave de IA configurada…
  symbols: export function LlmNotConfiguredBanner
  imports: @/lib, lucide-react, next, react
  → usa: frontend/src/lib/api.ts
`frontend/src/components/shared/PageContainer.tsx` (tsx, 40 loc) — Wrapper único de página (auditoría UIX #11): padding y max-width consistentes en todas las page.tsx del dashboard…
  symbols: export function PageContainer
  imports: @/lib
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/shared/PageHeader.tsx` (tsx, 30 loc)
  symbols: export function PageHeader
  imports: lucide-react
`frontend/src/components/shared/StatusBadge.tsx` (tsx, 80 loc)
  symbols: export function StatusBadge
  imports: @/components, @/lib
  → usa: frontend/src/components/ui/badge.tsx, frontend/src/lib/utils.ts
`frontend/src/components/shared/__tests__/PageContainer.test.tsx` (tsx, 45 loc) — Tests del wrapper único de página `shared/PageContainer` (auditoría UIX #11)
  imports: @testing-library/react, vitest
  → usa: frontend/src/components/shared/PageContainer.tsx
`frontend/src/components/shared/__tests__/PageHeader.test.tsx` (tsx, 43 loc) — Tests del componente canónico `shared/PageHeader`…
  imports: @testing-library/react, vitest
  → usa: frontend/src/components/shared/PageHeader.tsx
`frontend/src/components/shared/index.ts` (ts, 6 loc)
`frontend/src/components/ui/EmptyState.tsx` (tsx, 130 loc) — UI.EMP — componente reutilizable de empty state productivo…
  symbols: export function EmptyState; function PrimaryButton; function SecondaryButton
  imports: lucide-react, next
`frontend/src/components/ui/ErrorBoundary.tsx` (tsx, 53 loc)
  symbols: export class ErrorBoundary
  imports: react
`frontend/src/components/ui/ToastContainer.tsx` (tsx, 58 loc) — Renderer global del toast store (stores/toast.ts)…
  symbols: export function ToastContainer
  imports: @/stores, lucide-react
  → usa: frontend/src/stores/toast.ts
`frontend/src/components/ui/__tests__/EmptyState.test.tsx` (tsx, 82 loc) — Tests del componente reutilizable EmptyState (UI.EMP)
  imports: @testing-library/react, @testing-library/user-event, lucide-react, vitest
  → usa: frontend/src/components/ui/EmptyState.tsx
`frontend/src/components/ui/avatar.tsx` (tsx, 51 loc)
  imports: @/lib, @radix-ui/react-avatar, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/badge.tsx` (tsx, 43 loc)
  symbols: function Badge
  imports: @/lib, class-variance-authority, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/button.tsx` (tsx, 57 loc)
  imports: @/lib, @radix-ui/react-slot, class-variance-authority, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/card.tsx` (tsx, 80 loc)
  imports: @/lib, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/command.tsx` (tsx, 156 loc)
  imports: @/components, @/lib, @radix-ui/react-dialog, cmdk, lucide-react, react
  → usa: frontend/src/lib/utils.ts, frontend/src/components/ui/dialog.tsx
`frontend/src/components/ui/dialog.tsx` (tsx, 123 loc)
  imports: @/lib, @radix-ui/react-dialog, lucide-react, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/dropdown-menu.tsx` (tsx, 201 loc)
  imports: @/lib, @radix-ui/react-dropdown-menu, lucide-react, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/input.tsx` (tsx, 26 loc)
  imports: @/lib, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/label.tsx` (tsx, 27 loc)
  imports: @/lib, @radix-ui/react-label, class-variance-authority, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/logo-svg.tsx` (tsx, 92 loc) — Logo de AutomatizaCore inline…
  symbols: export function LogoSvg
`frontend/src/components/ui/popover.tsx` (tsx, 32 loc)
  imports: @/lib, @radix-ui/react-popover, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/scroll-area.tsx` (tsx, 49 loc)
  imports: @/lib, @radix-ui/react-scroll-area, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/select.tsx` (tsx, 161 loc)
  imports: @/lib, @radix-ui/react-select, lucide-react, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/separator.tsx` (tsx, 32 loc)
  imports: @/lib, @radix-ui/react-separator, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/sheet.tsx` (tsx, 141 loc)
  imports: @/lib, @radix-ui/react-dialog, class-variance-authority, lucide-react, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/skeleton.tsx` (tsx, 16 loc)
  symbols: function Skeleton
  imports: @/lib
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/social-icons.tsx` (tsx, 79 loc) — Mapa plataforma → icono, indexable por el id de SocialAccount
  symbols: export const InstagramIcon; export const FacebookIcon; export const LinkedInIcon; export const XIcon; export const TikTokIcon; export const YouTubeIcon; export const RedditIcon; export const PinterestIcon; export const ThreadsIcon; export const GoogleBusinessIcon; export const PLATFORM_ICONS
  imports: react
`frontend/src/components/ui/table.tsx` (tsx, 118 loc)
  imports: @/lib, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/tabs.tsx` (tsx, 56 loc)
  imports: @/lib, @radix-ui/react-tabs, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/components/ui/tooltip.tsx` (tsx, 31 loc)
  imports: @/lib, @radix-ui/react-tooltip, react
  → usa: frontend/src/lib/utils.ts
`frontend/src/hooks/__tests__/useDensity.test.tsx` (tsx, 59 loc) — Tests del hook UI.DEN
  imports: @testing-library/react, vitest
  → usa: frontend/src/hooks/useDensity.ts
`frontend/src/hooks/__tests__/useLocale.test.tsx` (tsx, 58 loc) — Tests del hook I18N.SEL
  symbols: function clearLocaleCookie
  imports: vitest
  → usa: frontend/src/hooks/useLocale.ts
`frontend/src/hooks/useAgentStream.ts` (ts, 95 loc) — UI.AGT — hook React que consume el stream SSE de una task del agente…
  symbols: export function useAgentStream
  imports: @/lib, react
  → usa: frontend/src/lib/api/taskStream.ts
`frontend/src/hooks/useAuthGuard.ts` (ts, 22 loc) — Redirige a /login cuando no hay token de auth tras la hidratación…
  symbols: export function useAuthGuard
  imports: @/lib, next, react
  → usa: frontend/src/lib/api/client.ts
`frontend/src/hooks/useDensity.ts` (ts, 56 loc) — UI.DEN — preferencia de densidad de UI persistida en localStorage…
  symbols: export function getStoredDensity; export function applyDensity; export function useDensity; function setDensity
  imports: react
`frontend/src/hooks/useFormat.ts` (ts, 53 loc) — I18N.FMT — bind del locale activo sobre los helpers de `lib/format.ts`…
  symbols: export function useFormat
  imports: @/hooks, @/lib, next-intl, react
  → usa: frontend/src/hooks/useLocale.ts, frontend/src/lib/format.ts
`frontend/src/hooks/useLocale.ts` (ts, 40 loc) — I18N.SEL — preferencia de idioma persistida en cookie…
  symbols: export const SUPPORTED_LOCALES; export function getStoredLocale; export function setStoredLocale
`frontend/src/hooks/useUserRole.ts` (ts, 24 loc)
  symbols: export function useUserRole; function computeRole
  imports: @/lib, react
  → usa: frontend/src/lib/api/client.ts
`frontend/src/i18n/request.ts` (ts, 29 loc)
  symbols: function _resolveLocale
  imports: next, next-intl
`frontend/src/i18n/routing.ts` (ts, 7 loc)
  symbols: export const routing
  imports: next-intl
`frontend/src/lib/api.ts` (ts, 11 loc) — Re-export from modular api/ directory for backward compatibility…
  imports: @/lib
`frontend/src/lib/api/__tests__/client.test.ts` (ts, 214 loc)
  symbols: function setupTokens
  imports: vitest
`frontend/src/lib/api/__tests__/contracts.test.ts` (ts, 501 loc) — QA.FRO — contract tests de los módulos lib/api/*.ts…
  symbols: function lastCall; function lastUrl; function lastInit; function lastBody
  imports: vitest
  → usa: frontend/src/lib/api/auth.ts, frontend/src/lib/api/autonomy.ts, frontend/src/lib/api/onboarding.ts, frontend/src/lib/api/regap.ts, frontend/src/lib/api/notifications.ts, frontend/src/lib/api/verifactuConfig.ts, frontend/src/lib/api/tasks.ts, frontend/src/lib/api/system.ts, frontend/src/lib/api/erp.ts
`frontend/src/lib/api/__tests__/errors.test.ts` (ts, 57 loc)
  symbols: function freshErrors
  imports: vitest
`frontend/src/lib/api/accounting.ts` (ts, 93 loc)
  symbols: export const accounting
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/admin.ts` (ts, 19 loc)
  symbols: export const admin
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/aeat.ts` (ts, 86 loc) — AEAT — custodia de certificado digital + presentación electrónica de modelos…
  symbols: export const aeat
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/ai_employees.ts` (ts, 114 loc) — Ajusta el tope de gasto mensual (USD)…
  symbols: export const aiEmployees
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/albaranes.ts` (ts, 44 loc)
  symbols: export const albaranes
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/alerts.ts` (ts, 16 loc)
  symbols: export const alertsApi
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/analytics.ts` (ts, 193 loc)
  symbols: export const analytics
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/auth.ts` (ts, 31 loc)
  symbols: export const auth
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/autonomy.ts` (ts, 32 loc) — SEC.AUT — cliente de política de autonomía por dominio
  symbols: export const autonomy
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/banking.ts` (ts, 82 loc) — Razón legible por la que un par tx↔factura ha sumado puntos (F2.6)
  symbols: export const banking
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/base.ts` (ts, 42 loc) — Resolución en runtime de la base del backend…
  symbols: export function resolveApiBase; export function resolveWsBase; function isDirect
`frontend/src/lib/api/calendar_unified.ts` (ts, 20 loc)
  symbols: export const calendarUnified
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/client.ts` (ts, 275 loc) — Base HTTP client — shared by all domain modules…
  symbols: export const BASE; export function getToken; export async function setTokens; export async function clearTokens; export async function request; export async function requestUpload; export async function fetchBlob; export async function downloadBlob; function parseDetail; function tryRefresh; function safeFetch
  → usa: frontend/src/lib/api/errors.ts, frontend/src/lib/api/base.ts, frontend/src/lib/secureStore.ts
`frontend/src/lib/api/client_portal.ts` (ts, 115 loc)
  symbols: export const clientPortalAdmin; export const clientPortal; function getPortalJwt; function portalRequest
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/collections.ts` (ts, 72 loc) — Inteligencia de cobros (F3.9) — ranking de morosidad + recordatorios
  symbols: export const collections
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/crm.ts` (ts, 113 loc)
  symbols: export const crm
  → usa: frontend/src/lib/api/client.ts, frontend/src/lib/api/erp.ts
`frontend/src/lib/api/documents.ts` (ts, 162 loc) — Respuesta de GET .../contract-templates/:id/preview-html (mammoth)
  symbols: export const documents
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/email_marketing.ts` (ts, 78 loc)
  symbols: export const emailMarketingApi
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/erp.ts` (ts, 463 loc) — Borrador de factura escaneada, listo para revisión + import al ERP
  symbols: export const erp
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/errors.ts` (ts, 69 loc) — Error tipado para respuestas de la API…
  symbols: export class ApiError; export const AI_DEGRADATION_MESSAGE; export function isConnectivityError; export function surfaceIfConnectivity
`frontend/src/lib/api/generative_ui.ts` (ts, 37 loc)
  symbols: export const generativeUI
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/hr.ts` (ts, 233 loc)
  symbols: export const hr
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/hr_documents.ts` (ts, 56 loc) — Descarga el PDF server-side (incluye el folio); también es la base para firmar
  symbols: export const hrDocuments
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/index.ts` (ts, 238 loc) — Barrel re-export — reconstructs the `api` object with the exact same shape as the original monolithic api.ts for full backward compatibility…
  symbols: export const api
  imports: @/lib
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/auth.ts, frontend/src/lib/api/tasks.ts, frontend/src/lib/api/documents.ts, frontend/src/lib/api/erp.ts, frontend/src/lib/api/banking.ts, frontend/src/lib/api/analytics.ts, frontend/src/lib/api/crm.ts, frontend/src/lib/api/hr.ts, frontend/src/lib/api/projects.ts (+35)
`frontend/src/lib/api/integrations.ts` (ts, 102 loc)
  symbols: export const integrations
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/inventory_analytics.ts` (ts, 77 loc) — Analítica de inventario (valoración, stock muerto, más vendidos)
  symbols: export const inventoryAnalytics
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/inventory_lots.ts` (ts, 68 loc) — Gestión de lotes de producto (caducidad / FEFO)…
  symbols: export const lots
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/labels.ts` (ts, 17 loc) — Impresión de etiquetas con código de barras (devuelve el PDF como Blob)
  symbols: export const labels
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/license.ts` (ts, 21 loc)
  symbols: export const licenseApi
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/llm_usage.ts` (ts, 29 loc)
  symbols: export const llmUsage
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/marketing.ts` (ts, 164 loc)
  symbols: export const marketingApi
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/marketplace.ts` (ts, 66 loc) — Marketplace de workflows (F3.10) — plantillas curadas + YAML import/export
  symbols: export const marketplace
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/messaging.ts` (ts, 144 loc) — API client — Messaging (Telegram, Email, Drive)
  symbols: export const messaging
  → usa: frontend/src/lib/api/client.ts, frontend/src/lib/api/documents.ts
`frontend/src/lib/api/metrics.ts` (ts, 22 loc)
  symbols: export const metricsApi
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/modelosAeat.ts` (ts, 130 loc) — MOD.130/347/390/111/190 — cliente de los endpoints de cálculo de modelos AEAT…
  symbols: export const modelosPdf; export const modelosAeat
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/notifications.ts` (ts, 37 loc) — UI.NOT — cliente de notificaciones persistentes
  symbols: export const notificationsApi
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/onboarding.ts` (ts, 99 loc) — UI.ONB + UI.SIM — cliente del wizard onboarding focado + simulación 303
  symbols: export const onboarding
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/pos.ts` (ts, 97 loc) — TPV (Punto de Venta) API
  symbols: export const pos
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/presentacion.ts` (ts, 43 loc) — PRES.ASS — cliente de presentación asistida AEAT (Modelos 131 y 200)
  symbols: export const presentacion
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/projects.ts` (ts, 45 loc)
  symbols: export const projects
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/recruitment.ts` (ts, 65 loc)
  symbols: export const recruitment
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/regap.ts` (ts, 51 loc) — PRES.REG — cliente del wizard REGAP (apoderamiento AEAT)
  symbols: export const regap
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/reorder.ts` (ts, 38 loc) — Reposición automática: sugerencias de pedido y generación de pedidos de compra borrador…
  symbols: export const reorder
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/reports.ts` (ts, 140 loc)
  symbols: export const reports; export const advisory
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/scanner.ts` (ts, 126 loc) — Scanner API…
  symbols: export const scanner; export const mobileScanner; function scannerFetch
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/signing.ts` (ts, 74 loc) — Firma electrónica AutoFirma del Estado (F3.11)…
  symbols: export const signing
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/system.ts` (ts, 84 loc)
  symbols: export const system
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/taskStream.ts` (ts, 134 loc) — UI.AGT — cliente del endpoint SSE `/api/v1/tasks/{task_id}/stream`…
  symbols: export async function streamTaskEvents; export async function cancelTask; export async function fetchTaskCost
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/tasks.ts` (ts, 75 loc) — Salida final agregada (backend Task.output_data)
  symbols: export const tasks; export const approvals
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/templates.ts` (ts, 61 loc)
  symbols: export const templatesApi
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/tenant.ts` (ts, 97 loc)
  symbols: export const tenant
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/treasury.ts` (ts, 166 loc) — Tesorería (F2.7) — cashflow proyectado + remesas SEPA pain.001
  symbols: export const treasury; function triggerXmlDownload
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/users.ts` (ts, 102 loc)
  symbols: export const users
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/verifactuConfig.ts` (ts, 24 loc) — FAC.MODE — cliente del modo de remisión Verifactu
  symbols: export const verifactuConfig
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/warehouses.ts` (ts, 64 loc) — Almacenes / tiendas y stock por almacén (multi-almacén)…
  symbols: export const warehouses
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/api/workflows.ts` (ts, 56 loc)
  symbols: export const workflows
  → usa: frontend/src/lib/api/client.ts
`frontend/src/lib/error-reporter.ts` (ts, 46 loc) — Frontend error reporter — sends errors to the backend for centralized logging…
  symbols: export function reportError
  → usa: frontend/src/lib/api/base.ts
`frontend/src/lib/format.ts` (ts, 70 loc) — I18N.FMT — helpers de formato locale-aware (migración i18n real, #1 fase 2)…
  symbols: export function formatCurrency; export function formatNumber; export function formatDate; export function formatDateTime; export function formatTime; function intlLocale
  imports: @/hooks
  → usa: frontend/src/hooks/useLocale.ts
`frontend/src/lib/hooks/__tests__/usePolling.test.tsx` (tsx, 99 loc) — Tests del hook compartido `usePolling` (auditoría UIX #10)
  symbols: function setVisibility
  imports: @testing-library/react, vitest
  → usa: frontend/src/lib/hooks/usePolling.ts
`frontend/src/lib/hooks/useNotificationSocket.ts` (ts, 67 loc) — Connects to /ws/notifications and dispatches messages by type…
  symbols: export function useNotificationSocket; function connect
  imports: @/lib, react
  → usa: frontend/src/lib/api/client.ts, frontend/src/lib/api/base.ts
`frontend/src/lib/hooks/usePendingApprovalsCount.ts` (ts, 35 loc) — Número de aprobaciones pendientes del tenant…
  symbols: export function usePendingApprovalsCount
  imports: @/lib, react
  → usa: frontend/src/lib/api.ts, frontend/src/lib/hooks/useNotificationSocket.ts, frontend/src/lib/hooks/usePolling.ts
`frontend/src/lib/hooks/usePolling.ts` (ts, 77 loc) — Si es false, no se programa ningún intervalo…
  symbols: export function usePolling
  imports: react
`frontend/src/lib/i18n-static.ts` (ts, 30 loc) — I18N.STATIC — traductor síncrono para código no-React…
  symbols: export function tStatic
  imports: @/hooks, @/messages
  → usa: frontend/src/messages/es.json, frontend/src/messages/en.json, frontend/src/hooks/useLocale.ts
`frontend/src/lib/logger.ts` (ts, 18 loc) — Logs errors only in development…
  symbols: export function logError; export function logDebug
`frontend/src/lib/plans.ts` (ts, 16 loc)
  symbols: export function canAccess; export const PLAN_LABELS
`frontend/src/lib/secureStore.ts` (ts, 120 loc) — SEC.JWT — Secure storage for JWT tokens…
  symbols: export function hydrateSecureStore; export function getCachedToken; export async function setSecureToken; export async function removeSecureToken; export async function clearAllSecureTokens; function getElectronApi; function warnFallbackOnce
`frontend/src/lib/utils.ts` (ts, 7 loc)
  symbols: export function cn
  imports: clsx, tailwind-merge
`frontend/src/lib/utils/error.ts` (ts, 9 loc) — Safely extract an error message from an unknown caught value
  symbols: export function getErrorMessage
`frontend/src/lib/utils/export-csv.ts` (ts, 28 loc)
  symbols: export function exportToCsv
`frontend/src/lib/utils/parse-csv.ts` (ts, 43 loc) — Parses a CSV string into an array of row arrays…
  symbols: export function parseCsvRows; export function csvToObjects
`frontend/src/messages/ca.json` (json, 460 loc)
  symbols: key: common; key: auth; key: nav; key: dashboard; key: ventas; key: clientes; key: errors
`frontend/src/messages/en.json` (json, 6015 loc)
  symbols: key: common; key: auth; key: nav; key: dashboard; key: ventas; key: clientes; key: errors; key: rrhh; key: configuracion; key: banca; key: tesoreria; key: miEquipo … (+8)
`frontend/src/messages/es.json` (json, 6015 loc)
  symbols: key: common; key: auth; key: nav; key: dashboard; key: ventas; key: clientes; key: errors; key: rrhh; key: configuracion; key: banca; key: tesoreria; key: miEquipo … (+8)
`frontend/src/messages/eu.json` (json, 460 loc)
  symbols: key: common; key: auth; key: nav; key: dashboard; key: ventas; key: clientes; key: errors
`frontend/src/messages/gl.json` (json, 460 loc)
  symbols: key: common; key: auth; key: nav; key: dashboard; key: ventas; key: clientes; key: errors
`frontend/src/stores/__tests__/navigationGuard.test.ts` (ts, 66 loc)
  imports: @testing-library/react, vitest
  → usa: frontend/src/stores/navigationGuard.ts
`frontend/src/stores/__tests__/notifications.test.ts` (ts, 122 loc)
  imports: @testing-library/react, vitest
  → usa: frontend/src/stores/notifications.ts
`frontend/src/stores/__tests__/toast.test.ts` (ts, 111 loc)
  imports: @testing-library/react, vitest
  → usa: frontend/src/stores/toast.ts
`frontend/src/stores/confirm.ts` (ts, 47 loc) — Función de conveniencia usable fuera de componentes React
  symbols: export const useConfirmStore; export const showConfirm
  imports: zustand
`frontend/src/stores/license.ts` (ts, 18 loc)
  symbols: export const useLicenseStore
  imports: zustand
`frontend/src/stores/navigationGuard.ts` (ts, 14 loc)
  symbols: export const useNavigationGuard
  imports: zustand
`frontend/src/stores/notifications.ts` (ts, 120 loc) — UI.NOT — true cuando viene de BD (persistente cross-session)
  symbols: export const useNotificationStore; function _persistedToLocal
  imports: @/lib, zustand
  → usa: frontend/src/lib/api.ts, frontend/src/lib/api/notifications.ts
`frontend/src/stores/toast.ts` (ts, 46 loc) — Hook shortcut for components
  symbols: export const useToastStore; export const useToast
  imports: zustand
`frontend/src/test-utils/msw-handlers.ts` (ts, 43 loc)
  symbols: export const handlers
  imports: msw
`frontend/src/test-utils/msw-server.ts` (ts, 11 loc)
  symbols: export const server
  imports: msw, vitest
  → usa: frontend/src/test-utils/msw-handlers.ts
`frontend/src/test-utils/render.tsx` (tsx, 32 loc) — Custom render that wraps components with any needed providers
  symbols: function AllProviders; function customRender
  imports: @testing-library/react, @testing-library/user-event, next-intl, react
  → usa: frontend/src/messages/es.json
`frontend/src/test/a11y/AIDisclosureBanner.a11y.test.tsx` (tsx, 34 loc) — QA.AXE — auditoría WCAG 2.1 AA del banner Art…
  imports: @/components, @testing-library/react, vitest
  → usa: frontend/src/components/ai/AIDisclosureBanner.tsx, frontend/src/test/a11y/setup.ts
`frontend/src/test/a11y/AIGenerationFooter.a11y.test.tsx` (tsx, 34 loc) — QA.AXE — auditoría WCAG 2.1 AA del footer de trazabilidad LLM…
  imports: @/components, @testing-library/react, vitest
  → usa: frontend/src/components/ai/AIGenerationFooter.tsx, frontend/src/test/a11y/setup.ts
`frontend/src/test/a11y/login.a11y.test.tsx` (tsx, 32 loc) — QA.AXE — auditoría WCAG 2.1 AA de la página de login…
  imports: @/app, @/test-utils, vitest
  → usa: frontend/src/test-utils/render.tsx, frontend/src/app/(auth)/login/page.tsx, frontend/src/test/a11y/setup.ts
`frontend/src/test/a11y/setup.ts` (ts, 36 loc) — U.6 WCAG / QA.AXE — setup compartido para tests de accesibilidad…
  symbols: export const axe
  imports: vitest, vitest-axe
`frontend/src/types/electron.d.ts` (ts, 51 loc) — Augmentación global de `window.electronAPI` (DIS.UPD / SEC.JWT)…
`frontend/tailwind.config.js` (js, 96 loc) — @type {import('tailwindcss').Config}
  imports: tailwindcss-animate
`frontend/tsconfig.json` (json, 43 loc)
  symbols: key: compilerOptions; key: include; key: exclude
`frontend/vitest.config.ts` (ts, 41 loc) — /*.test.{ts,tsx}"], coverage: { provider: "v8", reporter: ["text", "json", "html"], include: ["src/*
  imports: @vitejs/plugin-react, path, vitest
`frontend/vitest.setup.ts` (ts, 77 loc)
  symbols: class ResizeObserverMock; class IntersectionObserverMock
  imports: vitest

## scripts/  (3 archivos)
`scripts/audit_domain_completeness.py` (python, 188 loc) — Audita la sincronización del coordinador para garantizar el principio ERP…
  symbols: def _load_state(); def _check_sync(valid, dispatchers, keywords); def _check_tool_registry(); def _print_table(findings); def main()
  imports: __future__, pathlib, sys
`scripts/generate_market_study.py` (python, 1265 loc) — Genera un PDF de estudio de mercado de AutomatizaCore para presentar…
  symbols: def _style(name, parent); def cell(text); def cell_header(text); def _on_page(canvas, doc); def H1(text); def H2(text); def H3(text); def P(text); def Quote(text); def BulletList(items); def DataTable(data, col_widths, header_row); def SectionBreak() … (+15)
  imports: __future__, datetime, os, pathlib, reportlab
`scripts/generate_sbom.py` (python, 178 loc) — DIS.SBOM — generador de SBOM CycloneDX unificado…
  symbols: def _parse_requirements(path); def _parse_package_json(path, scope); def _parse_embedded(path); def build_sbom(version); def main()
  imports: __future__, argparse, datetime, hashlib, json, pathlib, re, sys, uuid

## tasks/  (54 archivos)
`tasks/audit/RESUMEN.md` (markdown, 125 loc) — Auditoría profunda — AutomatizaCore (2026-06-19)
  symbols: # Auditoría profunda — AutomatizaCore (2026-06-19); ## Veredicto; ## CRÍTICO — actuar antes de más clientes; ## ALTO; ## MEDIO; ## BAJO / deuda; ## Cobertura de tests — huecos críticos; ## Plan de acción recomendado (orden)
`tasks/audit/architecture.md` (markdown, 159 loc) — Architecture Compliance Audit
  symbols: # Architecture Compliance Audit; ## Summary scorecard; ## Rule 1 — Routes must validate + return HTTP only (ZERO business logic); ## Rule 2 — Services receive `db: AsyncSession` as a param (no global session); ## Rule 3 — Agents: isolation, structure, AgentResult; ## Rule 4 — Frontend: no direct `fetch()` in components; ## Rule 5 — Layering: models with business logic, god files; ## Rule 6 — Naming orchestrator vs coordinator; ## Cross-cutting: module count vs cohesion, duplication, dead code; ## Top priorities (fix order)
`tasks/audit/arquitectura-2026-06-25.md` (markdown, 48 loc) — Auditoría de Arquitectura — Backend (FastAPI + LangGraph)
  symbols: # Auditoría de Arquitectura — Backend (FastAPI + LangGraph); ## Resumen de violaciones por tipo y severidad; ## Detalle de hallazgos; ### R1 — Routes con lógica de negocio (HIGH); ### R2 — Domain services con sesión propia (HIGH); ### R4 — Tools que lanzan en vez de devolver AgentResult (MEDIUM); ### R5 — Nómina duplicada agente↔servicio (HIGH); ## Las 3 peores
`tasks/audit/code-quality.md` (markdown, 124 loc) — Code Quality Audit — Automatiza-pyme-main
  symbols: # Code Quality Audit — Automatiza-pyme-main; ## 1. Dead code; ## 2. TODO / FIXME / HACK / XXX markers; ## 3. God files / complexity (Python > 600 LOC, top 15); ## 4. Error handling — swallowed exceptions; ## 5. Async correctness; ## 6. Duplication; ## 7. Type safety; ## 8. Config / magic numbers / print(); ## Priority recommendations
`tasks/audit/cross-cutting-2026-06-25.md` (markdown, 60 loc) — Auditoría transversal — 2026-06-25
  symbols: # Auditoría transversal — 2026-06-25; ## Resumen por severidad; ## HIGH; ### H1 — Reset de contraseña: fail-open + token en logs; ## MEDIUM; ### M1 — 7 clientes httpx.AsyncClient persistentes nunca se cierran; ### M2 — SECRET_KEY corta/débil; ### M3 — Drift requirements.txt: `langfuse` no se instala en desktop; ### M4 — 117 `except Exception` que devuelven el mensaje crudo de la excepción; ### M5 — NIF en logs (RGPD); ## LOW; ## Aspectos sólidos (sin hallazgos)
`tasks/audit/dependencies.md` (markdown, 80 loc) — Dependency / Build / Release-Health Audit
  symbols: # Dependency / Build / Release-Health Audit; ## 1. Dependency versions & supply-chain; ### Backend (`backend/requirements.txt`) — HIGH severity; ### Frontend (`frontend/package.json`) — lockfile committed (`package-lock.json`), good.; ### Desktop (`desktop/package.json`) — lockfile committed (`package-lock.json`), good.; ## 2. Frontend build / typecheck; ## 3. Electron desktop security posture; ## 4. Committed build artifacts; ## 5. Config hygiene — `.env.example` completeness; ## 6. i18n parity — CRITICAL finding; ## Severity summary
`tasks/audit/fiscal-nuevo-2026-06-25.md` (markdown, 71 loc) — Auditoría fiscal/contable — hallazgos NUEVOS (2026-06-25)
  symbols: # Auditoría fiscal/contable — hallazgos NUEVOS (2026-06-25); ## CRITICAL; ### N1 — Las facturas en estado `draft` (y `pending`/`sent`) ENTRAN en los modelos 303/130/347/390 y en el snapshot fiscal; ### N2 — Las rectificativas (abono) se suman como devengo POSITIVO en 303/390/snapshot, inflando el IVA repercutido; ## HIGH; ### N3 — El asiento de nómina IGNORA la cuota patronal de Seguridad Social (642) → coste de personal y P&G infravalorados; ### N4 — Modelo 130: ingresos/gastos = `amount_base` sin restar la retención IRPF soportada; casilla 06 forzada a 0; ### N5 — `compute_invoice_totals` redondea por línea pero el desglose del 303 reagrupa con criterio distinto → micro-descuadres base vs cuota; ## MEDIUM; ### N6 — `create_journal_entry` valida cuadre con tolerancia `> 0.01` sobre floats → asientos con descuadre de 1 céntimo pasan; ### N7 — `delete_invoice` permite borrar una factura emitida SIN registro Verifactu, dejando hueco en la numeración correlativa; ## Confirmaciones / refutaciones de Bnn
`tasks/audit/fiscal.md` (markdown, 112 loc) — Auditoría de corrección fiscal (AEAT + VeriFactu)
  symbols: # Auditoría de corrección fiscal (AEAT + VeriFactu); ## Resumen ejecutivo; ## 1. Corrección de cálculo por modelo; ### 303 IVA — `casillas_303.py`; ### 130 IRPF — `casillas_130.py`; ### 111 — `modelos_aeat.py` (~L228) y `casillas_111.py`; ### 115 / 190 / 347 / 390 — `casillas_115/190/347/390.py`; ### 100 / 200; ### 131 (módulos); ## 2. VeriFactu — envío real (commit 2a2075d); ## 3. Invariante BORRADOR / no falsificar justificante; ## 4. Modo de redondeo (ROUND_HALF_UP)
`tasks/audit/frontend-2026-06-25.md` (markdown, 70 loc) — Auditoría Frontend — `frontend/src/` (2026-06-25)
  symbols: # Auditoría Frontend — `frontend/src/` (2026-06-25); ## Resumen por severidad; ## HIGH; ### H1 — `.then()` sin `.catch()` masivo: promesas API que pueden quedar sin manejar; ## MEDIUM; ### M1 — Redondeo de importes calculado por línea en cliente puede descuadrar el total mostrado; ### M2 — PVP/IVA calculado en cliente sobre `price` float en catálogo; ### M3 — `any` en vistas de modelos fiscales 130/303; ### M4 — Lectura de total de factura vía `as any` sin tipo; ## LOW; ### L1 — Fecha de factura: `new Date(date).toISOString()` reinterpreta date-only como UTC; ### L2 — `console.log` activo vía `lib/logger.ts:16`
`tasks/audit/rls-bypass-changes.md` (markdown, 50 loc) — RLS fail-closed — bypass/set wiring changes
  symbols: # RLS fail-closed — bypass/set wiring changes; ## Webhooks / public callbacks; ## Scheduler / startup global reads (initial cross-tenant enumeration only); ## Startup (lifespan, pre-traffic); ## Extra finding (pre-existing bug fixed); ## Files NOT touched (per instructions, already done)
`tasks/audit/rls-notenant-flows.md` (markdown, 170 loc) — RLS fail-closed — no-tenant DB flows audit
  symbols: # RLS fail-closed — no-tenant DB flows audit; ## 1. Auth / login (user/tenant loaded BEFORE tenant known) — MUST-BYPASS; ## 2. Client portal — MUST-BYPASS (token lookup only); ## 3. Webhooks (external callbacks, no JWT) — MUST-BYPASS for the lookup; ## 4. Scheduler / workers — mostly SAFE (already wrap per-tenant); ## 5. Startup / bootstrap / health / license — MUST-BYPASS (startup) / SAFE (license); ## 6. Middleware — NO TenantContextMiddleware exists; ## 7. The 67 direct-session sites — categorization; ### SUSPICIOUS (probable real bugs to flag, not blanket-bypass); ## Recommended next steps
`tasks/audit/sec-backend-2026-06-25.md` (markdown, 56 loc) — Auditoría de Seguridad — Backend Python (FastAPI/SQLAlchemy/LangGraph)
  symbols: # Auditoría de Seguridad — Backend Python (FastAPI/SQLAlchemy/LangGraph); ## Resumen por severidad; ## HIGH; ## MEDIUM; ## LOW; ### Top 3 más graves
`tasks/audit/security.md` (markdown, 207 loc) — Security Audit — AutomatizaCore
  symbols: # Security Audit — AutomatizaCore; ## CRITICAL; ### C1 — RLS policy is fail-OPEN when tenant GUC is unset; ## HIGH; ### H1 — Scanner JWT scope is advisory, not enforced at the data layer; ### H2 — `/auth/refresh` issues fresh tokens from stale claims with no revocation; ## MEDIUM; ### M1 — Stored XSS via Outlook email body rendered without sanitization; ### M2 — JWT tokens stored in localStorage (XSS → full account takeover); ### M3 — DB restore shells out with attacker-influenced env, admin-only; ### M4 — `register` blocks remote by IP, but relies solely on `is_local_request`; ## LOW / INFORMATIONAL
`tasks/audit/testing.md` (markdown, 57 loc) — Testing & CI Audit — 2026-06-19
  symbols: # Testing & CI Audit — 2026-06-19; ## Test counts; ## Run results (local subset, SQLite); ## Coverage map (test files referencing each critical service); ### Gaps / thin critical paths; ## Test quality; ## CI assessment (`.github/workflows/ci.yml`)
`tasks/auditoria_codigo_2026-06-25.md` (markdown, 190 loc) — Auditoría de código — informe consolidado (2026-06-25)
  symbols: # Auditoría de código — informe consolidado (2026-06-25); ## Resumen ejecutivo; ## 🔴 CRITICAL — corregir antes de que un cliente presente un modelo; ### N1 · El 303/130/347/390 no filtran `Invoice.status` → cuentan borradores y anuladas; ### N2 · Las rectificativas quedan fuera del devengo del 303/390 → el cliente ingresa de más; ## 🟠 HIGH; ### Fiscal; ### Seguridad; ### Arquitectura; ### Frontend / Transversal; ## 🟡 MEDIUM (resumen — detalle en sub-informes); ## ⚪ LOW / higiene
`tasks/auditoria_licencias_2026-06-12.md` (markdown, 103 loc) — Auditoría de integridad — Validación de licencias (2026-06-12)
  symbols: # Auditoría de integridad — Validación de licencias (2026-06-12); ## Arquitectura actual; ## Fortalezas (bien hechas); ## Debilidades (por severidad); ### 🔴 CRÍTICA; ### 🟠 ALTA; ### 🟡 MEDIA; ## Relación con auto-update; ## Recomendaciones priorizadas
`tasks/backlog.md` (markdown, 306 loc) — Backlog operativo — AutomatizaCore MVP
  symbols: # Backlog operativo — AutomatizaCore MVP; ## Convenciones; ## DEC — Decisiones humanas; ## ALB — Alembic + datos; ## SEC — Seguridad; ## FAC — Verifactu + facturación; ## MOD — Modelos AEAT generación; ## PRES — Presentación telemática AEAT; ## UI — UI/UX frontend; ## OPS — Customer operations; ## AI — AI Act compliance; ## INT — Integraciones bancarias / N43
`tasks/bug-triage.md` (markdown, 91 loc) — Triaje de bugs — revisión de módulos (2026-06-21)
  symbols: # Triaje de bugs — revisión de módulos (2026-06-21); ## ✅ ARREGLADO en esta pasada (seguro, sin tu intervención, verificado); ## ⏸️ REQUIERE TU DECISIÓN (no tocado: fiscal/legal/migración/comportamiento/dependencia); ### A. Cálculo fiscal de importes — tu línea roja, no toco sin tu OK; ### B. ERP — numeración fiscal y stock (riesgo de datos / migración); ### C. RRHH — cálculo/convenio; ### D. Capa IA / scheduler (concurrencia / migración); ### E. Seguridad frontend (requiere dependencia / decisión); ## Verificado como CORRECTO (no son bugs); ## Siguiente lote sugerido (si me das luz verde)
`tasks/bugs-pendientes.md` (markdown, 25 loc) — Auditoría de `tasks/lessons.md` vs código actual
  symbols: # Auditoría de `tasks/lessons.md` vs código actual; ## Notas de verificación
`tasks/cleanup-candidates.md` (markdown, 298 loc) — Cleanup candidates — informe consolidado
  symbols: # Cleanup candidates — informe consolidado; ## Estado de ejecución (2026-06-17); ## TIER 1 — Código muerto (helpers privados Python `_*` sin refs en el grafo); ### Hallazgo crítico: los 35 REVISAR son casi todos FALSOS POSITIVOS; ### ALTA confianza — 78 helpers (0 apariciones fuera de su fichero); ### Comando de limpieza propuesto (NO ejecutado); # 1) confirmar 0 usos (incl. strings/getattr) en TODO el repo:; # 2) solo si 0 usos reales y no es callback de librería ni fixture → borrar la def a mano.; ### 2º pase — verdictos (verificación de referencias indirectas); ## TIER 2 — Imports/exports sin uso; ### Backend Python — herramienta usada: **ruff 0.7.4** (`ruff check --select F401`); ### Frontend TS — ts-prune ejecutado (`npx --yes ts-prune`, sin instalar global)
`tasks/cuadre/state.md` (markdown, 9 loc) — Estado del bucle /cuadre (memoria fiscal en disco)
  symbols: # Estado del bucle /cuadre (memoria fiscal en disco)
`tasks/diagnostico-backend.md` (markdown, 66 loc) — Diagnóstico salud estática del backend
  symbols: # Diagnóstico salud estática del backend; ## 1. Ruff lint (BLOQUEANTE) — PASA; ## 2. Ruff format --check (advisory) — DIVERGE; ## 3. Mypy --strict (advisory) en app/agents + app/services — 1587 errores; ### Nota: name-defined (13) — los únicos que huelen a bug, no a deuda de tipos; ### unused-ignore (11) ficheros:; ## 4. Pytest --collect-only (sin BD) — OK
`tasks/diagnostico-resumen.md` (markdown, 55 loc) — Diagnóstico de salud del proyecto — 2026-06-22
  symbols: # Diagnóstico de salud del proyecto — 2026-06-22; ## Veredicto en una frase; ## Resultados (espejo del CI, `.github/workflows/ci.yml`); ## Hallazgos verificados; ## Recomendaciones priorizadas (valor / esfuerzo / riesgo); ## Recomendación
`tasks/e2e_agent_audit_2026-06-23.md` (markdown, 168 loc) — Auditoría E2E de agentes con LLM real — 2026-06-23
  symbols: # Auditoría E2E de agentes con LLM real — 2026-06-23; ## Veredictos por dominio; ## Causas raíz (con referencia a código); ### A. Clasificador insensible a tildes — `classifier.py:333`; ### B. Keywords genéricos sobre-capturan — `classifier_data.py`; ### C. Huecos de cobertura — `classifier_data.py`; ### D. El match keyword "confiado-pero-erróneo" cortocircuita al LLM — `classifier.py:399`; ### E. `report` fabrica y miente éxito — `dispatchers/reports.py:30`; ### F. El guard de fallo es bueno pero incompleto — `dispatchers/_outcome.py`; ### G. Las tools SÍ están enlazadas; falla la **elicitación** del provider — `accounting/agent.py:23-59`; ### H. (META) CI no ejerce el camino que falla; ## Patrón transversal (resumen ejecutivo)
`tasks/eje12_runbook.md` (markdown, 72 loc) — Runbook eje 12 — Presentación telemática AEAT (PRES.RB)
  symbols: # Runbook eje 12 — Presentación telemática AEAT (PRES.RB); ## §1 Las dos fases; ### Fase A — Homologación (sin esperar PRES.0); ### Fase B — Producción (después de PRES.0); ## §2 Conmutación entre fases; # Pre-producción (Fase A); # Producción (Fase B); ## §3 Checklist pre-launch comercial (1-jul / 22-jul / 9-ago según rama); ## §4 Procedimiento si AEAT rechaza un envío; ## §5 Mantenimiento del cert producción
`tasks/erp_review_2026-06-24.md` (markdown, 97 loc) — Revisión ERP — informe consolidado (2026-06-24)
  symbols: # Revisión ERP — informe consolidado (2026-06-24); ## A. Síntomas reportados (uso real) — causa raíz; ## B. Hallazgos confirmados de la revisión profunda (23); ### 🔴 HIGH — correctitud fiscal/contable (prioridad máxima); ### 🟠 MEDIUM; ### 🟢 LOW; ## C. Veredictos de flujo de datos ERP (todos **PARCIAL**); ## D. Plan de arreglo sugerido (por prioridad); ## E. Actualización 2026-06-25 — barrera fiscal del agente
`tasks/evaluacion-proyecto.md` (markdown, 63 loc) — Evaluación global del proyecto — AutomatizaCore / Zernio
  symbols: # Evaluación global del proyecto — AutomatizaCore / Zernio; ## Nota global: **7.2 / 10** — _producción temprana, alta (early production, upper tier)_; ## Tabla de dimensiones; ## Justificación de la ponderación; ## 3 fortalezas clave; ## 3 riesgos/debilidades clave; ## Qué subiría / bajaría la nota; ## Veredicto
`tasks/exhaustive-deps.md` (markdown, 39 loc) — react-hooks/exhaustive-deps — resolución de los 16 warnings
  symbols: # react-hooks/exhaustive-deps — resolución de los 16 warnings; ## Recuento de tipos de fix
`tasks/holded-vs-automatizapyme.md` (markdown, 147 loc) — Holded vs…
  symbols: # Holded vs. AutomatizaPyme — Análisis 360º; ## 0. TL;DR; ## 1. Holded en una frase; ## 2. Comparativa por área; ### 2.1 Contabilidad / Fiscal; ### 2.2 Inventario / ERP; ### 2.3 RRHH; ### 2.4 CRM / IA / Automatización; ### 2.5 Capacidades operativas de los agentes (la fuerza de trabajo); ## 3. Tus puntos fuertes (dónde ganas); ## 4. Donde Holded te gana (roadmap); ## 5. Posicionamiento comercial
`tasks/iteraciones-cliente-real.md` (markdown, 166 loc) — Iteraciones de cliente real — gestión y seguimiento
  symbols: # Iteraciones de cliente real — gestión y seguimiento; ## 1. Por qué este documento; ## 2. El ciclo de iteración; ## 3. Dónde vive el test que blinda cada flujo; ## 4. Tabla de seguimiento; ### Por dónde empezar (prioridad); ## 5. Estado de la suite (línea base); ## 6. Cómo registrar una iteración (plantilla); ### [FECHA] <Módulo> — <Flujo>; ## Registro de iteraciones; ### 2026-06-15 · Marketing OAuth · no crear cuentas 'unknown' (red→green); ### 2026-06-15 · Email-marketing · contar fallos de envío (red→green)
`tasks/lessons.md` (markdown, 1297 loc) — Lecciones aprendidas
  symbols: # Lecciones aprendidas; ## 2026-06-23 — "Prompt caching = margen" es falso por dos vías (verificar antes de barrer); ## 2026-06-23 — El CI verde miente: probar agentes E2E con el LLM real revela otra app; ## 2026-06-23 — La capa RLS ya estaba sellada; el riesgo real era otro; ## 2026-06-22 — requirements.txt no era la fuente de verdad: el backend usa Poetry; ## 2026-06-21 — Inventariar IA por sus @tool, no por nombres de carpeta; ## 2026-06-21 — "Pestaña rota" = tabla nunca poblada (helper sin call-sites); ## 2026-06-19 — No ordenar por UUID aleatorio para aserciones de orden; ## 2026-06-19 — Tests sobre BD: assert por SQLSTATE, no por el texto del mensaje; ## 2026-06-19 — No afirmar hechos externos ni estado del código sin verificar primero; ## 2026-06-11 — Subagentes de migración i18n reportan "Done" con trabajo a medias; ## 2026-06-10 — Un custom 'Perfil' (sin capacidades) NO debe interceptar el routing del Coordinador
`tasks/llm-capabilities.md` (markdown, 102 loc) — Capacidades del LLM en AutomatizaCore
  symbols: # Capacidades del LLM en AutomatizaCore; ## Cómo funciona; ## Por dominio; ### 💰 Billing (facturación) — 15 tools; ### 👥 HR (recursos humanos) — 7 tools; ### 🏦 Banking — 4 tools; ### 📒 Accounting (contabilidad) — 5 tools; ### 📄 Documents — 6 tools (2 propias + 4 shared); ### 🤝 CRM — 5 tools; ### 📧 Email — 3 tools; ### 📊 Excel — 5 tools; ### 📜 Compliance fiscal — 3 tools
`tasks/marketing_zernio_migration.md` (markdown, 84 loc) — Migración: marketing social propio → Zernio (BYO)
  symbols: # Migración: marketing social propio → Zernio (BYO); ## API de Zernio (verificada en docs); ## Etapas (additivo → recablear → demoler; verificar en cada una); ## ✅ SMOKE en vivo con la API key real (verificado 2026-06-16); ## NO se toca
`tasks/onboarding-agent-spec.md` (markdown, 83 loc) — Spec — Agente de Onboarding para conversión en los primeros 5 minutos
  symbols: # Spec — Agente de Onboarding para conversión en los primeros 5 minutos; ## 1. Qué existe hoy (auditoría, no suposición); ### 1.1 Wizard de onboarding focado — `UI.ONB`; ### 1.2 Wizard REGAP (apoderamiento AEAT) — `PRES.REG`; ### 1.3 Ambos están registrados solo como rutas; ## 2. El gap; ## 3. Diseño propuesto (incremental, 3 fases); ### Fase 1 — Telemetría primero (NO arquitectura); ### Fase 2 — Agente de onboarding (`agents/onboarding/`); ### Fase 3 — Cableado al orquestador (Coordinador); ## 4. Criterios de aceptación; ## 5. Hilos de investigación abiertos (del informe)
`tasks/plan-go-to-market-byok-2026-06-04.md` (markdown, 106 loc) — Plan de acción go-to-market — modelo BYOK
  symbols: # Plan de acción go-to-market — modelo BYOK; ## 0. Qué cambia al fijar BYOK; ## 1. Bloqueantes de CÓDIGO (tuyos · horas–días); ## 2. FIABILIDAD del motor IA (medir antes de invertir); ## 3. ENDURECER EL CAMINO DEL DINERO (antes del primer cliente de pago); ## 4. TRÁMITES y DECISIONES externas (tuyas · semanas — empezar YA en paralelo); ## 5. SECUENCIA RECOMENDADA; ## 6. Riesgos abiertos a vigilar
`tasks/remote_access_fase1.md` (markdown, 55 loc) — Acceso remoto — Fase 1 (prospecto que lo pide: 10+ empleados, sin instalar)
  symbols: # Acceso remoto — Fase 1 (prospecto que lo pide: 10+ empleados, sin instalar); ## Hecho (código, verificado); ## Operativa (no-código, lo hace Marcos); ## Pendiente antes de cuentas de empleado no-admin (Fase 1.5); ## Fase 2 (diferido — solo con 2º cliente)
`tasks/reports/auditoria-arquitectura-2026-06-14.md` (markdown, 125 loc) — Auditoría arquitectónica AutomatizaCore — 2026-06-14
  symbols: # Auditoría arquitectónica AutomatizaCore — 2026-06-14; ## Resumen ejecutivo; ## 1. Flujo de información y conectividad; ## 2. Profundidad, estabilidad y acoplamiento; ## 3. Flujos y contratos de agentes; ## 4. Documentación; ## 5. Normas ambiguas (con propuestas de resolución concretas); ## 6. Huérfanos y código muerto; ## Plan de acción priorizado; ### P0 — Romper ciclos y corregir contrato (esfuerzo: ~1-2 días); ### P1 — Deriva doc y violaciones de capa (esfuerzo: ~1-2 días); ### P2 — Higiene y gaps de producto (esfuerzo: ~1 día)
`tasks/restructuracion-modulos.md` (markdown, 159 loc) — Reestructuración de módulos a medias
  symbols: # Reestructuración de módulos a medias; ## 1. Gestoría / generación documental → hacerla CONVERSACIONAL; ### Estado actual; ### Plan; ### Flujos a probar (→ tabla de iteraciones); ## 2. Marketing → corregir bugs que **engañan al usuario**; ### Bugs confirmados (prioridad); ### Flujos a probar; ## 3. Modelos fiscales AEAT → entregar el modelo **OFICIAL**; ### Estado actual; ### Plan (elegir vía); ### Pasos transversales (ambas vías)
`tasks/roadmap.md` (markdown, 339 loc) — Roadmap AutomatizaCore — MVP comercial 22-jul-2026
  symbols: # Roadmap AutomatizaCore — MVP comercial 22-jul-2026; ## Addendum 2026-05-17 — Estado real verificado; ## §1 Supuestos; ## §2 Decisiones administrativas esta semana — fechas-tope; ## §3 Critical path — sprint plan (9 sprints + buffer); ### Sprint 1 (18-22 may) — Fundación; ### Sprint 2 (25-29 may) — Seguridad + numeración; ### Sprint 3 (1-5 jun) — Verifactu chain hash; ### Sprint 4 (8-12 jun) — Tests AEAT + modelos AEAT.1; ### Sprint 5 (15-19 jun) — Modelos AEAT.2 + presentación homologación; ### Sprint 6 (22-26 jun) — Presentación PRES.3'+PRES.4' + backend service; ### Sprint 7 (29 jun - 3 jul) — Customer ops + backup + migración
`tasks/roadmap_global_2026-06-11.md` (markdown, 125 loc) — Roadmap GLOBAL unificado — AutomatizaCore (2026-06-11)
  symbols: # Roadmap GLOBAL unificado — AutomatizaCore (2026-06-11); ## Método y advertencia; # FASE 1 — Desbloquear venta legal + piloto (P0); # FASE 2 — Completar producto para go-to-market (P1); ### Fiscal; ### Facturación / Contabilidad; ### Documentos / Gestoría; ### Onboarding; ### Banca; ### Inventario; ### BYOK / IA / Pricing; ### Frontend / i18n
`tasks/ronda/inbox/2026-06-25-rls-dependientes.md` (markdown, 26 loc) — Inbox /ronda — hallazgos que dependen de confirmar RLS (2026-06-25)
  symbols: # Inbox /ronda — hallazgos que dependen de confirmar RLS (2026-06-25)
`tasks/ronda/state.md` (markdown, 24 loc) — Estado del bucle /ronda (memoria del proyecto en disco)
  symbols: # Estado del bucle /ronda (memoria del proyecto en disco); ## Resolución (2026-06-25, misma sesión) — todos los REJECT atendidos
`tasks/run_one_order_real_llm.md` (markdown, 68 loc) — Run ONE order E2E with the REAL Claude Code LLM (Windows, no API key)
  symbols: # Run ONE order E2E with the REAL Claude Code LLM (Windows, no API key); ## Interpreter (has all backend deps); ## Safe tenant in THIS DB (PG :5433) — use Demo Masivo, never the real fiscal tenant; ## TWO blockers the raw smoke script hits (and the fixes baked in below); ## Recipe — change only PROMPT to run any single order; ## Verified result (read-only "Dame el resumen contable del mes pasado")
`tasks/templates/issue-template.md` (markdown, 49 loc) — Issue — [XXX.NN] [Título]
  symbols: # Issue — [XXX.NN] [Título]; ## Metadata; ## Descripción; ## Definition of Done; ## Contexto técnico; ## Riesgos; ## Referencias
`tasks/templates/pr-template.md` (markdown, 66 loc) — PR — [tipo]: [descripción corta]
  symbols: # PR — [tipo]: [descripción corta]; ## Contexto; ## Qué cambia; ## Impacto; ## Tests; ## Migración / schema; ## Seguridad / AI Act; ## Detect changes; ## Checklist final; ## Notas para el revisor
`tasks/templates/sprint-retro-template.md` (markdown, 68 loc) — Sprint N — Retrospectiva ([fechas])
  symbols: # Sprint N — Retrospectiva ([fechas]); ## Metadata; ## ¿Qué cerramos? (items DONE); ## ¿Qué quedó WIP o pasó a próximo sprint?; ## Bloqueos encontrados; ## Sorpresas técnicas (cosas no previstas); ## Decisiones operativas tomadas durante el sprint; ## Lecciones aprendidas; ## Acciones para el próximo sprint; ## Calendario vs realidad; ## Salud del equipo
`tasks/test-backend.md` (markdown, 46 loc) — Backend test run — report
  symbols: # Backend test run — report; ## DB isolation (safeguard); ## Totals; ## Failures (grouped); ### test_api_ai_employees.py (1); ## Skipped (2); ## Notes
`tasks/test-frontend.md` (markdown, 37 loc) — Frontend test suite (test:ci) — diagnóstico
  symbols: # Frontend test suite (test:ci) — diagnóstico; ## Conteos; ## Fichero que falla; ## Causa raíz (común a los 5); ### Tests fallidos y causa concreta; ### Claves faltantes (locale es)
`tasks/test_funcional_completo.py` (python, 1310 loc) — ╔══════════════════════════════════════════════════════════════════════════════╗ ║ AUTOMATIZAPYME — TEST FUNCIONAL COMPLETO ║ ║ Simula un us…
  symbols: class TestResult; def ok(phase, test_name, detail, ms, http_status); def fail(phase, test_name, detail, ms, http_status); def skip(phase, test_name, reason); def info(msg); def section(title); async def timed_request(client, method, url); async def poll_task(client, task_id, max_wait); async def phase_health(client); async def phase_auth(client); async def phase_clients(client); async def phase_products(client) … (+20)
  imports: argparse, asyncio, dataclasses, datetime, httpx, json, os, pathlib, sys, time, uuid
`tasks/testing-protocol.md` (markdown, 426 loc) — Protocolo de prueba del sistema de agentes
  symbols: # Protocolo de prueba del sistema de agentes; ## Filosofía; ## Flujo de una iteración; ## Credenciales locales (solo desarrollo); ## IDs de los empleados IA built-in + custom; ## 🔵 Probar TAREAS (acción puntual); ### Plantilla PowerShell; ### Catálogo de tools a cubrir (un prompt por tool); ## 🟢 Probar AUTOMATIZACIONES (regla persistente); ### Tipos de trigger a cubrir; ### Modos de ejecución a cubrir; ### Cosas a vigilar en automatizaciones
`tasks/tiktok-integration-spec.md` (markdown, 80 loc) — Integración TikTok — guía de implementación
  symbols: # Integración TikTok — guía de implementación; ## 0. Decisión (recap); ## 1. ⚠️ La diferencia grande: TikTok es VÍDEO/FOTO, no texto; ## 2. Prerrequisitos (portal TikTok for Developers) — lo que TÚ configuras; ## 3. Cambios de código (ficheros exactos); ### a) `backend/app/services/marketing/oauth.py`; ### b) license-server `main.py` (Render); ### c) `backend/app/services/marketing/oauth_tokens.py`; ### d) `backend/app/services/marketing/publisher.py`; ### e) `frontend/.../marketing/_components/constants.ts`; ### f) DB; ## 4. Camino mínimo recomendado (iterativo)
`tasks/todo.md` (markdown, 539 loc) — Tareas activas — AutomatizaCore
  symbols: # Tareas activas — AutomatizaCore; ## 2026-06-22 — Contraste del consejo + Item 10 (reproducibilidad de deps); ### ✅ HECHO — Item 10: requirements.txt pineado y reproducible; ### ✅ HECHO — Item 4: Onboarding "datos de ejemplo" (seed demo-empresa) (2026-06-23); ### Items 6 + 1 + 3 — hardening RLS (2026-06-23) — investigado y acotado; ## ✅ HECHO — Dar de baja stock por rotura/merma (unidades o cajas); ### Analíticas de mermas/bajas (ambos sitios) — ✅ HECHO; ### Portal "ver como empleado" (admin) salía EN BLANCO — ✅ HECHO (raíz real); ### Modal de consumo de IA — fix de raíz (provider no reportaba tokens) — ✅ HECHO; ## Fiscal; ## Gestoría / Firma; ## AIEmployee — Contrato del custom (RETIRADO 2026-06-18)
`tasks/verifactu_envio_spec.md` (markdown, 115 loc) — VeriFactu — envío a la AEAT: spec de la costura
  symbols: # VeriFactu — envío a la AEAT: spec de la costura; ## 1. Estado y alcance; ## 2. La costura (`backend/app/services/billing/verifactu_submit.py`); ## 3. Cadena del envío real (cuando haya certificado); ## 4. Formato del acuse — CONFIRMADO (anclado a `RespuestaSuministro.xsd` del repo); ## 5. POR CONFIRMAR (necesita certificado + preproducción) — no asumir como verdad; ## 6. Punto de enganche (cuando haya cert) — NO conectado hoy; # ... commit ...; ## 7. Cómo probar cuando llegue el certificado; ## 8. Línea roja (máxima cautela)
`tasks/verifactu_xsd_reference.md` (markdown, 440 loc) — Referencia XSD oficial AEAT VeriFactu (Suministro de Registros de Facturación)
  symbols: # Referencia XSD oficial AEAT VeriFactu (Suministro de Registros de Facturación); ## 0. URLs canónicas oficiales (página de desarrolladores AEAT); ## 1. Namespaces y prefijos (CLAVE — versión del path ≠ versión del namespace); ## 2. Elemento raíz `RegFactuSistemaFacturacion` (sfLR); ## 3. `RegistroAlta` — ORDEN EXACTO (sf:RegistroFacturacionAltaType); ### Sub-tipos del Alta; ## 4. `RegistroAnulacion` — ORDEN EXACTO (sf:RegistroFacturacionAnulacionType); ## 5. `Encadenamiento` (idéntico en Alta y Anulación); ## 6. `SistemaInformatico` (SistemaInformaticoType) — orden exacto; ## 7. Enumeraciones clave (valores literales del XSD); ### Patrones / longitudes; ## 8. Cálculo de la Huella (SHA-256) — payload canónico

## tools/  (1 archivos)
`tools/dev-tunnel-proxy.js` (js, 71 loc) — dev-tunnel-proxy.js — SOLO para la prueba de acceso remoto SIN dominio (Fase 1)…
  symbols: function target
  imports: http, net
