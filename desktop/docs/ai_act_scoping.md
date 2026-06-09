# AI Act Scoping Memo — AutomatizaCore MVP

> **Fecha**: 2026-05-14
> **Marco normativo**: Reglamento UE 2024/1689 (AI Act) — aplicación high-risk Anexo III: **2-ago-2026**
> **Auditoría**: AI.AUDIT (Sprint 1, dev2). Cobertura: 3 capas (`agents/`, `services/`, `db/models/`).
> **Output**: clasificación por agente + lista de columnas DB AI Act-related + acciones de cumplimiento.

## §1 Resumen ejecutivo

| Categoría | Cantidad | Acción MVP |
|---|---|---|
| **Agentes high-risk Anexo III** | 2 (`recruitment`, `hr`) | Escenario A: retirar `score_candidate()` + plantilla termination structure-only |
| **Agentes limited risk** (Art. 50 transparencia) | Todos los demás con interacción usuario | Banner *"Estás interactuando con un sistema de IA"* (AI.2) |
| **Agentes minimal risk** | Auxiliares / no conversacionales | Sin obligaciones específicas |
| **Columnas DB AI Act-related** | 2 (`Candidate.score`, `Candidate.score_breakdown`) | `DROP COLUMN` en Alembic baseline (ALB.3) |

## §2 Clasificación por agente

### Agentes high-risk Anexo III (4) "Empleo, gestión de trabajadores"

#### `agents/recruitment`

- **Hallazgos**: `score_candidate()` invocado en `tools.py:96,122,139,156,179,180` + ranking `ORDER BY Candidate.score DESC` en `:178-180`.
- **Cita Anexo III (4)(a)**: *"sistemas de IA destinados a usarse para... analizar y filtrar solicitudes de empleo, y evaluar candidatos"*.
- **Excepción Art. 6(3) ¿aplica?**: **NO**. Art. 6(3) párrafo 2: *"un sistema de IA del anexo III se considerará siempre de alto riesgo cuando realice perfilado de personas físicas"*. El scoring de candidatos por skills+experience con breakdown JSON es perfilado bajo Art. 4(4) RGPD.
- **Acción MVP — Escenario A**: retirar `score_candidate()` + `Candidate.score` + `Candidate.score_breakdown` por feature flag. Cierra Anexo III completamente.
- **Reintroducción v1.2**: solo con compliance completo (QMS, marcado CE, registro UE, ~30-60d + 5-15k€ organismo notificado + 1-2k€/año mantenimiento).

#### `services/hr` (parte de evaluación de personal)

- **Hallazgos**:
  - `commands.py:233,269,284-285` — invoca `score_candidate()` y persiste `score` y `score_breakdown`.
  - `queries.py:377` — `ORDER BY Candidate.score DESC NULLSLAST` para ranking.
  - `queries.py:125,171-176` — plantilla `termination` con cita ET Art. 52/54.
- **Cita Anexo III (4)(a)**: scoring/ranking → mismo que `recruitment`.
- **Cita Anexo III (4)(b)**: *"sistemas de IA destinados a usarse para tomar decisiones que afecten a... la terminación de relaciones contractuales laborales"*.
- **Acción MVP — Escenario A ampliado**:
  - Retirar `score_candidate()` también de `services/hr/commands.py:269` y `queries.py:377`.
  - Plantilla `termination` reducida a **estructura formal vacía** (LLM emite encabezado/identificación/cita normativa/fecha/firma; NO motiva el cuerpo).
  - UI gate `ENTIENDO` tipado (no checkbox) + disclaimer modal *"Esta plantilla no constituye asesoramiento jurídico. La motivación del despido debe ser redactada y revisada por un abogado laboralista. AutomatizaCore no se responsabiliza del contenido."*.
  - Coste: 0.5d implementación + dictamen abogado laboralista (decisión humana 12, ~500€).
- **Defensa Art. 6(3) párrafo 1**: con structure-only sin motivación, la herramienta es *"tarea preparatoria estricta"* — el LLM no decide, no motiva, no influye en contenido. Validar con dictamen.

### Agentes limited risk (transparencia Art. 50)

Todos los agentes conversacionales con LLM activo. Obligación única: banner *"Estás interactuando con un sistema de IA"* en primera apertura + footer permanente *"Generado por [proveedor LLM] · [modelo] · [tokens]"*.

| Agente | Función | Justificación clasificación |
|---|---|---|
| `agents/billing` | Facturación, Verifactu | Genera facturas. No evalúa personas físicas. Limited risk transparencia. |
| `agents/crm` | CRM B2B | Ver §3 análisis especial `qualify_leads`. Limited risk. |
| `agents/banking` | Conciliación bancaria N43 | Reconcilia movimientos bancarios contra facturas. No scoring crediticio. *"type: credit"* es tipo de movimiento (abono), no scoring. |
| `agents/accounting` | Contabilidad | Asientos contables. No evalúa personas. |
| `agents/email` | Email management | Envía/lee emails. `/me/profile` URL Microsoft Graph (falso positivo). |
| `agents/compliance` | Alertas fiscales | Calendario AEAT, no decide sobre personas. |
| `agents/documents` | Gestión documental | Almacena documentos. Sin scoring. |
| `agents/marketing` | Marketing | Generación de copy. Sin profiling avanzado verificado en código. **Beta + `autonomy_policy=CONFIRM` ya consensuado**. Re-verificar si añade segmentación demográfica futura. |
| `agents/orchestrator` | Coordinador | Decide qué agente invocar. Sin perfilado de personas. |
| `agents/rag` | Búsqueda semántica | Búsqueda contextual. Sin scoring de personas. |
| `agents/excel` | Manipulación Excel | Formato, no decisión. |
| `agents/uploads` | Subida de ficheros | Sin lógica de decisión. |

### Agentes minimal risk

| Agente | Función | Justificación |
|---|---|---|
| `agents/agent_tools/semantic_search` | Ranking semántico documental | Ranking de documentos, no personas. |
| `agents/tool_timeout` | Timeout helper | Utilidad técnica. |
| `agents/validators` | Validadores deterministas | Reglas, no IA. |
| `agents/workers` | Workers async | Infraestructura. |
| `agents/workflow` | Ejecución de workflows | Coordinación, no decisión sobre personas. |

## §3 Análisis especial — `crm.qualify_leads`

### Evidencia

- `agents/crm/agent.py:29`: *"qualify_leads: para analizar leads nuevos y rankear a quién contactar"*.
- `agents/crm/tools.py:176-183`: docstring *"Analiza todas las oportunidades en fase 'new' y sugiere cuáles cualificar **basándose en el valor esperado y el tiempo en pipeline**"*.

### Clasificación AI Act

**Limited risk, no high-risk Anexo III.**

Razonamiento:

1. La función rankea **oportunidades comerciales (deals)**, no individuos. La unidad evaluada es la `Opportunity`, entidad de negocio.
2. Los criterios son **métricas comerciales** (valor esperado del deal, tiempo en pipeline), no características personales del lead.
3. Anexo III (5)(b) cubre *"sistemas usados para evaluar la solvencia crediticia de personas físicas o establecer su puntuación crediticia"* — no aplica porque qualify_leads no decide acceso a servicios esenciales.
4. Anexo III (4) cubre empleo — no aplica.
5. Aunque el cliente sea persona física (autónomo), el ranking no se basa en características protegidas o de identidad, sino en valor económico del deal.

### Acción

- Mantener `qualify_leads` en MVP.
- Banner Art. 50 ya cubre transparencia (AI.2).
- **Si en v1.X se añade segmentación por características demográficas/personales del lead**, re-evaluar clasificación.

## §4 Columnas DB AI Act-related

Búsqueda en `db/models/` con patrones `_score|_risk|_profile|_ranking|_evaluation|_credit|_rating`:

| Columna | Ubicación | Acción |
|---|---|---|
| `Candidate.score` | `db/models/hr.py:249` (comentario *"0-100 fit score"*) | **`DROP COLUMN` en Alembic baseline (ALB.3)** |
| `Candidate.score_breakdown` | `db/models/hr.py:250` (comentario *"{skills: 80, experience: 60, ...}"*) | **`DROP COLUMN` en Alembic baseline (ALB.3)** |

Cero columnas adicionales detectadas. La defensa Art. 6(3) requiere que el schema refleje la retirada efectiva, no solo desactivación de código.

## §5 Obligaciones Art. 26 (deployer) que asume el cliente

El cliente (PYME / autónomo / gestoría) actúa como **deployer** bajo AI Act. AutomatizaCore actúa como **provider** del sistema integrado.

Cláusulas a incluir en EULA (AI.6):

- El cliente debe informar a representantes de trabajadores antes de desplegar (Art. 26.7) — relevante en tier Gestoría con multi-empresa.
- El cliente conserva log automático ≥ 6 meses (cubierto técnicamente por `audit_immutable` + `AgentExecutionTrace`).
- El cliente coopera con autoridades AI Office si requerido.

Cláusulas para AutomatizaCore como provider (Art. 13, 16, 17):

- Instructions for use entregadas al deployer.
- Logs automáticos ≥ 6 meses (cubierto).
- Gobernanza de datos de entrenamiento — N/A porque AutomatizaCore no entrena modelos, usa LLMs de terceros (Anthropic/OpenAI/Groq) como proveedores GPAI.

## §6 Acciones derivadas — checklist

- [ ] **AI.SCO** Retirar `score_candidate()` de `agents/recruitment/tools.py:96,122,139,156,179,180` (Sprint 2, dev1)
- [ ] **AI.SCO** Retirar `score_candidate()` de `services/hr/commands.py:233,269,284-285` y `services/hr/queries.py:377` (Sprint 2, dev1)
- [ ] **AI.TER** Reducir plantilla `termination` en `services/hr/queries.py:125,171-176` a structure-only + gate UI (Sprint 2, dev1 + abogado)
- [ ] **ALB.3** `DROP COLUMN Candidate.score, score_breakdown` en migración Alembic baseline (Sprint 1, dev1)
- [ ] **AI.BAN** Banner Art. 50 + footer LLM trazabilidad (Sprint 8, dev3)
- [ ] **AI.EULA** Cláusula AI Act en EULA Art. 26 deployer + Art. 13 provider (paralelo, abogado)
- [ ] **AI.WRK** Plantilla legal info trabajadores onboarding Gestoría (Sprint 8, abogado + dev3)
- [ ] **CONT.1 punto 5** Checklist *"¿la nueva funcionalidad cae en Anexo III?"* obligatorio en cada PR que toque agentes con datos de personas físicas (paralelo, fundador)

## §7 Re-scoping continuo

Esta auditoría es **snapshot del MVP en 2026-05-14**. Cualquier feature posterior que añada:

- Scoring/ranking/profiling de personas físicas
- Evaluación de rendimiento de empleados
- Decisiones sobre contratación/promoción/terminación
- Acceso a servicios esenciales (crédito, seguros, educación pública)
- Identificación biométrica

…debe re-clasificarse antes de merge mediante checklist CONT.1 punto 5. Owner: dev senior con responsabilidad de compliance asignada.

## §8 Cierre AI.AUDIT

**Resultado**: cero nuevos agentes high-risk descubiertos más allá de `recruitment` y `hr` ya conocidos. Cero columnas DB adicionales a `Candidate.score`/`score_breakdown`. Plan MVP intacto: Escenario A (retirada de `score_candidate` en dos capas + termination structure-only + DROP COLUMN en baseline) cierra el cumplimiento Anexo III sin alterar el calendario.

**Estado backlog**: AI.AUDIT → **DONE**.
