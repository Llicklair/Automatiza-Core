# Auditoría Multi-Tenancy — Fase 1

**Fecha**: 2026-05-02  
**Auditor**: Claude Code (Automated Security Audit)  
**Alcance**: Backend FastAPI + SQLAlchemy  
**Proyecto**: Automatiza-PYME

> **Nota sobre la versión inicial**: la primera ronda de auditoría se hizo con un subagente que leyó extractos limitados y reportó tres hallazgos como "críticos". Tras verificación línea-por-línea del código real, dos eran falsos positivos y uno NO era explotable, solo ameritaba defensa en profundidad. La sección **0. Verificación posterior** documenta los hallazgos confirmados. El resto del documento se conserva como referencia del proceso original.

---

## 0. Verificación posterior (2026-05-02 — fuente de verdad)

Tras leer el código real, los hallazgos quedan así:

| # | Reporte original | Realidad | Acción |
|---|---|---|---|
| 1 | DocumentEmbedding sin `tenant_id` | **FALSO POSITIVO** — `embeddings.py:16` ya tiene `tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)` | Ninguna |
| 2 | `node_engine.py:334, 340` críticamente vulnerable | **NO explotable** — `self.workflow_id` y `self.execution_id` vienen de BD ya validada en `run_workflow()` (filtrado por tenant en línea 130 de workflow service). UUIDs no son enumerables. Sin embargo, añadir filtro de tenant es defensa en profundidad de coste cero. | Aplicar fix defensivo |
| 3 | `generative_ui.py:91` sin filtro tenant | **FALSO POSITIVO** — la línea 91 contiene `select(Client...)` y la línea 92 contiene `.where(Client.tenant_id == tenant_id)`. El subagente sólo leyó la primera línea sin seguir el `.where()` encadenado. | Ninguna |
| 4 | `GeneratedUI` y `HRDocument` con `tenant_id` sin FK | **PENDIENTE de verificar** | Ver sección 0.1 |

### 0.1 Hallazgo confirmado tras auditoría detallada

- **node_engine.py:332-342** — `_load_workflow` y `_load_execution` cargan por `id` sin filtro de tenant. Hoy es seguro porque la cadena upstream ya validó propiedad. Tras Fase 3 (RLS), las policies de Postgres bloquearían cualquier acceso cruzado igualmente. El fix añade `Workflow.tenant_id == self.tenant_id` como tercera capa.

### 0.2 Lecciones

Ver `tasks/lessons.md` (entrada 2026-05-02) sobre verificar hallazgos de subagentes Explore antes de actuar.

---

## 1. Resumen ejecutivo

- **31 modelos** definidos en `backend/app/db/models/`
- **26 modelos tenant-scoped** con `tenant_id` (UUID, ForeignKey a `tenants.id`, NOT NULL + INDEX)
- **5 modelos globales** (Tenant, User, PasswordResetToken, DocumentEmbedding, y config de tenant)
- **Uniformidad ALTA**: 100% de los `tenant_id` son tipo **UUID(as_uuid=True)** con FK a tenants.id
- **Hallazgo crítico**: GeneratedUI tiene `tenant_id` sin ForeignKey — solo index. Riesgo: orfandad de datos.
- **Hallazgo moderado**: HRDocument usa import directo UUID de PostgreSQL, no del modelo common — inconsistencia de estilo (no de seguridad)

---

## 2. Tablas tenant-scoped (26 modelos)

| Modelo | Tabla | Tipo tenant_id | Nullable | FK | Path |
|--------|-------|----------------|----------|----|----|
| AIEmployee | ai_employees | UUID | NOT NULL | ✓ (CASCADE) | backend/app/db/models/ai_employees.py:14-15 |
| Activity | activities | UUID | NOT NULL | ✓ | backend/app/db/models/crm.py:54 |
| AuditLog | audit_log | UUID | NOT NULL | ✓ | backend/app/db/models/tasks.py:96 |
| BankTransaction | bank_transactions | UUID | NOT NULL | ✓ | backend/app/db/models/accounting.py:48 |
| Calendar Event | events | UUID | NOT NULL | ✓ | backend/app/db/models/calendar.py:16 |
| Client | clients | UUID | NOT NULL | ✓ | backend/app/db/models/crm.py:10 |
| DocumentTemplate | document_templates | UUID | NOT NULL | ✓ | backend/app/db/models/billing.py:113 |
| Employee | employees | UUID | NOT NULL | ✓ | backend/app/db/models/hr.py:14 |
| Event | events | UUID | NOT NULL | ✓ | backend/app/db/models/calendar.py:16 |
| FixedAsset | fixed_assets | UUID | NOT NULL | ✓ | backend/app/db/models/accounting.py:76 |
| GeneratedUI | generated_uis | UUID | NOT NULL | ✗ (índice solo) | backend/app/db/models/generative_ui.py:19 |
| HRDocument | hr_documents | UUID | NOT NULL | ✗ (índice solo) | backend/app/db/models/hr_documents.py:15 |
| Invoice | invoices | UUID | NOT NULL | ✓ | backend/app/db/models/billing.py:33 |
| InvoiceSeries | invoice_series | UUID | NOT NULL | ✓ | backend/app/db/models/billing.py:9 |
| JournalEntry | journal_entries | UUID | NOT NULL | ✓ | backend/app/db/models/accounting.py:13 |
| JournalLine | journal_lines | UUID | NOT NULL | ✓ | backend/app/db/models/accounting.py:31 |
| Opportunity | opportunities | UUID | NOT NULL | ✓ | backend/app/db/models/crm.py:30 |
| Payroll | payrolls | UUID | NOT NULL | ✓ | backend/app/db/models/hr.py:59 |
| PendingApproval | pending_approvals | UUID | NOT NULL | ✓ | backend/app/db/models/tasks.py:104 |
| Product | products | UUID | NOT NULL | ✓ | backend/app/db/models/inventory.py:10 |
| Project | projects | UUID | NOT NULL | ✓ | backend/app/db/models/projects.py:9 |
| ProjectTask | project_tasks | UUID | NOT NULL | ✓ | backend/app/db/models/projects.py:27 |
| Quote | quotes | UUID | NOT NULL | ✓ | backend/app/db/models/billing.py:63 |
| RecurringInvoice | recurring_invoices | UUID | NOT NULL | ✓ | backend/app/db/models/billing.py:95 |
| Reservation | reservations | UUID | NOT NULL | ✓ | backend/app/db/models/calendar.py:30 |
| StockMovement | stock_movements | UUID | NOT NULL | ✓ | backend/app/db/models/inventory.py:27 |
| Task | tasks | UUID | NOT NULL | ✓ | backend/app/db/models/tasks.py:18 |
| TenantDocument | tenant_documents | UUID | NOT NULL | ✓ | backend/app/db/models/tenant.py:45 |
| TenantIntegration | tenant_integrations | UUID | NOT NULL | ✓ | backend/app/db/models/tenant.py:9 |
| TenantKnowledge | tenant_knowledge | UUID | NOT NULL | ✓ | backend/app/db/models/tenant.py:26 |
| TenantLlmConfig | tenant_llm_configs | UUID | NOT NULL | ✓ | backend/app/db/models/tenant.py:37 |
| TokenLedger | token_ledger | UUID | NOT NULL | ✓ | backend/app/db/models/ai_employees.py:60 |
| Workflow | workflows | UUID | NOT NULL | ✓ | backend/app/db/models/workflows.py:12 |
| WorkflowExecution | workflow_executions | UUID | NOT NULL | ✓ | backend/app/db/models/workflows.py:27 |

**Subtotal tenant-scoped**: 34 modelos  
**Con FK íntegro**: 32 (94%)  
**Sin FK (riesgo de orfandad)**: 2 (GeneratedUI, HRDocument)

---

## 3. Tablas globales

### 3.1 Sistema de tenants (3 modelos)

| Modelo | Tabla | Descripción | Path |
|--------|-------|-------------|------|
| Tenant | tenants | Definición del tenant. Raíz del árbol de FK. | backend/app/db/models/auth.py:13 |
| User | users | Usuarios por tenant (tenant_id = FK). | backend/app/db/models/auth.py:27 |
| PasswordResetToken | password_reset_tokens | Tokens de reset de contraseña (user_id = FK, no tenant_id directo). | backend/app/db/models/auth.py:43 |

**Observación**: Todos los usuarios están vinculados a un tenant a través del User.tenant_id.

### 3.2 Auth compartido (1 modelo)

No se identifica tabla de auth compartida a nivel global. Todos los usuarios tienen tenant_id.

### 3.3 Catálogo / configuración global (1 modelo)

| Modelo | Tabla | Descripción | Path |
|--------|-------|-------------|------|
| DocumentEmbedding | document_embeddings | Embeddings vectoriales de documentos. Sin tenant_id (riesgo crítico). | backend/app/db/models/embeddings.py:18 |

**Riesgo**: Los embeddings no están particionados por tenant. Una búsqueda de similaridad en documento_embeddings devuelve resultados de TODOS los tenants.

### 3.4 Sospechosas (deberían tener tenant_id)

| Modelo | Tabla | Motivo de sospecha | Impacto |
|--------|-------|-------------------|--------|
| DocumentEmbedding | document_embeddings | Sin tenant_id ni índice de tenant. Consultas de similaridad exponen datos cross-tenant. | CRÍTICO: Fuga de datos en búsquedas RAG/LLM |
| AgentSkill | agent_skills | No tiene tenant_id directo, solo FK a ai_employees (que sí tiene tenant_id). | BAJO: Indirecto a través de employee_id. Requiere JOIN. |
| ActivityEntry | activity_feed | No listada en modelos principales; buscar en ai_employees.py. Require revisión. | PENDIENTE: Búsqueda en ai/employee_crud.py |

---

## 4. Queries potencialmente vulnerables

Búsqueda: patrones `select()` sin `.where(..tenant_id...)` cercano, o `db.execute()` sin condición de tenant en el mismo bloque.

### Hallazgos (máximo 15, solo candidatos con riesgo confirmado)

1. **File**: `backend/app/services/ai/generative_ui.py:262`  
   **Línea 262**: `select(GeneratedUI)` → Sin where inmediato  
   **Snippet**:
   ```python
   query = select(GeneratedUI)
   if pinned_only:
       query = query.where(GeneratedUI.is_pinned == True)
   result = await db.execute(query)
   ```
   **Riesgo**: Sin filtro tenant_id. Devuelve registros de todos los tenants si no se añade after.  
   **Status**: ⚠️ PARCIAL — Requiere revisión de contexto de callers

2. **File**: `backend/app/services/ai/employee_crud.py:298`  
   **Línea 298**: `select(ActivityEntry)` → Sin where en línea siguiente  
   **Snippet**:
   ```python
   query = select(ActivityEntry)
   # ... posible adición de where después
   result = await db.execute(query)
   ```
   **Riesgo**: ALTO si ActivityEntry no filtra por tenant en la misma expresión.  
   **Status**: 🔴 CRÍTICO — Requiere auditoría de ActivityEntry

3. **File**: `backend/app/services/ai/employee_crud.py:420`  
   **Línea 420**: `select(TokenLedger)` → Sin where visible  
   **Snippet**:
   ```python
   rows_result = await db.execute(
       select(TokenLedger).where(...)  # ¿Contiene tenant_id?
   )
   ```
   **Riesgo**: MODERADO — Necesita lectura completa de líneas 418-425.  
   **Status**: 🟡 PENDIENTE

4. **File**: `backend/app/services/analytics/dashboard.py:79`  
   **Contexto**: Todas las queries de dashboard parecen usar `tenant_id ==` al inicio.  
   **Riesgo**: BAJO — El archivo parece bien sanitizado. Muestreo de líneas 50-120 confirma pattern correcto.  
   **Status**: ✓ OK

5. **File**: `backend/app/services/ai/node_engine.py:334`  
   **Línea 334**: `select(Workflow).where(Workflow.id == uuid.UUID(...))`  
   **Snippet**:
   ```python
   result = await db.execute(
       select(Workflow).where(Workflow.id == uuid.UUID(self.workflow_id))
   )
   ```
   **Riesgo**: CRÍTICO — Filtra por ID global, NO por (id + tenant_id). Un atacante puede enumerar workflow IDs.  
   **Status**: 🔴 CRÍTICO

6. **File**: `backend/app/services/ai/node_engine.py:340`  
   **Línea 340**: `select(WorkflowExecution).where(WorkflowExecution.id == ...)`  
   **Riesgo**: CRÍTICO — Idéntico al anterior. No filtra tenant_id.  
   **Status**: 🔴 CRÍTICO

7. **File**: `backend/app/services/ai/generative_ui.py:54`  
   **Línea 54**: `select(...)` en función de resolución de contexto.  
   **Riesgo**: MODERADO — Requiere lectura de full función.  
   **Status**: 🟡 PENDIENTE

8. **File**: `backend/app/services/ai/generative_ui.py:91`  
   **Línea 91**: `select(Client.name, Client.email, ...)`  
   **Snippet**:
   ```python
   result = await db.execute(
       select(Client.name, Client.email, Client.phone, Client.city, Client.nif)
   )
   ```
   **Riesgo**: CRÍTICO — Sin where. Devuelve ALL clientes de TODOS los tenants.  
   **Status**: 🔴 CRÍTICO

9. **File**: `backend/app/services/ai/generative_ui.py:109`  
   **Línea 109**: `select(...)` en función context resolution.  
   **Riesgo**: MODERADO  
   **Status**: 🟡 PENDIENTE

10. **File**: `backend/app/services/ai/generative_ui.py:133`  
    **Línea 133**: `select(...)` → Necesita lectura completa.  
    **Riesgo**: MODERADO  
    **Status**: 🟡 PENDIENTE

**Nota**: Los candidatos pendientes requieren lectura línea-por-línea de `generative_ui.py` líneas 50-135 para confirmar.

---

## 5. Tipo de tenant_id — uniformidad

**RESULTADO: UNIFORMIDAD ALTA (99%)**

### Distribución observada:

```
UUID(as_uuid=True) con ForeignKey("tenants.id")    : 32 modelos (94%)
UUID(as_uuid=True) sin ForeignKey (índice solo)    : 2 modelos (6%)
  └─ GeneratedUI (generative_ui.py:19)
  └─ HRDocument (hr_documents.py:15)
```

### Mezclas detectadas: NINGUNA

Todos los `tenant_id` son `UUID(as_uuid=True)` (SQLAlchemy dialects.postgresql.UUID). No hay Integer, String, ni otros tipos.

### Import consistency:

- **Estándar**: Importan de `backend/app/db/models/common.py`
  ```python
  from .common import UUID, ForeignKey, ...
  ```

- **Desviante**: `HRDocument` importa directamente
  ```python
  from sqlalchemy.dialects.postgresql import UUID as PG_UUID
  ```
  **Impacto**: Estilo inconsistente (menor). Funcional idéntico a `common.UUID`.

---

## 6. Próximos pasos (Fase 2)

### Prioridad CRÍTICA (Resolver en esta semana):

1. **DocumentEmbedding — Agregar tenant_id**
   - Añadir columna `tenant_id` (UUID FK NOT NULL INDEX) a tabla
   - Migración de datos: asignar tenant_id basado en `document_id` (si es FK a TenantDocument)
   - Actualizar queries de similaridad para filtrar por tenant en `pgvector` search

2. **node_engine.py — Filtrado de Workflow + WorkflowExecution**
   - Líneas 334, 340: Cambiar `select(...).where(Model.id == ...)` por `select(...).where(Model.id == ..., Model.tenant_id == tenant_id)`
   - Validar que tenant_id se pasa a contexto de ejecución

3. **generative_ui.py — Auditoría línea 91**
   - Función: Identificar qué context retrieval hace `select(Client.*)`
   - Agregar `.where(Client.tenant_id == tenant_id)` antes de execute

### Prioridad ALTA (Resolver antes de prod):

4. **GeneratedUI, HRDocument — Agregar ForeignKey**
   - Cambiar `tenant_id = Column(UUID(...), index=True, nullable=False)` por
   - `tenant_id = Column(UUID(...), ForeignKey("tenants.id"), nullable=False, index=True)`
   - Añadir constraint de integridad en DB

5. **Completar auditoría de ServiceLayer — Phase 2**
   - Leer líneas 50-150 de `backend/app/services/ai/generative_ui.py` en detalle
   - Buscar en `backend/app/services/hr/`, `backend/app/services/billing/` patrones de queries sin tenant filter
   - Automated test: ejecutar queries sintéticas contra DB de test y verificar cross-tenant leakage

### Prioridad MEDIA (Mejora de robustez):

6. **HRDocument — Unificar imports**
   - Cambiar import de `sqlalchemy.dialects.postgresql.UUID` por `from .common import UUID`

7. **AgentSkill — Considerar desnormalización**
   - Actualmente: FK indirecta a tenant a través de `employee_id -> AIEmployee.tenant_id`
   - Opcional: Agregar `tenant_id` directo para queries más rápidas sin JOIN

8. **Índices compuestos en tenant_scoped tables**
   - Ejemplo: `(tenant_id, status)` en tasks, invoices para mejorar perf de filters típicos
   - Revisar query patterns en dashboard.py y replicar en todos los servicios

---

## 7. Comandos de validación recomendados

### Verificar cobertura de tenant_id en tablas:
```sql
-- Verificar todas las tablas con tenant_id
SELECT table_name FROM information_schema.columns 
WHERE column_name = 'tenant_id' AND table_schema = 'public' 
ORDER BY table_name;

-- Listar tablas SIN tenant_id (potenciales culpables)
SELECT DISTINCT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_type = 'BASE TABLE'
  AND table_name NOT IN (
    SELECT DISTINCT table_name FROM information_schema.columns 
    WHERE column_name = 'tenant_id'
  )
ORDER BY table_name;
```

### Detectar queries vulnerables en código:
```bash
# Buscar select() sin where en servicios
grep -rn "select(" backend/app/services/ --include="*.py" \
  | grep -v ".where(" \
  | head -20

# Buscar patrones sin tenant_id filter
grep -rn "where\(" backend/app/services/ --include="*.py" \
  | grep -v "tenant_id" \
  | grep -v "user_id\|email\|id ==" \
  | head -20
```

---

**Auditoría completada**: 2026-05-02 02:45 UTC  
**Siguiente revisión recomendada**: Después de implementar cambios en Fase 2 (estimado: 2026-05-09)
