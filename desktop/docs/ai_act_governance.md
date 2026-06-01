# Gobernanza de prompts y datos — AI.GOV

> Cumplimiento Reglamento UE 2024/1689 (AI Act) Art. 10 (data governance) + Art. 14 (human oversight) + Art. 12 (record-keeping). Política aplicable a AutomatizaPyme como **proveedor del sistema de IA integrado**.

## §1 Prompts versionados en repositorio

### Ubicación canónica

Todos los prompts del sistema viven en `backend/app/prompts/*.txt` (un archivo por dominio: `billing.txt`, `hr_agent.txt`, `compliance_agent.txt`, etc.). Los prompts versionados en código y NO en BD por las razones siguientes:

* **Versionable**: `git log` da auditoría exacta de cuándo y quién cambió un prompt.
* **Revisable**: PRs obligatorias para tocar `prompts/*.txt` con regla `pre-commit` (futuro).
* **Reproducible**: una build concreta del software contiene un set congelado de prompts. Auditor AEAT/AI Office puede pedir "muéstrame el prompt activo cuando se generó este modelo 303 el 2026-04-20" y la respuesta sale del commit/tag asociado a la versión instalada (`app_version` en `audit_log`).

### Trazabilidad por ejecución

Cada invocación de agente registra en `AgentExecutionTrace` (SEC.WORM):

| Campo | Origen | Uso |
|---|---|---|
| `prompt_hash` | SHA-256 del prompt completo expandido | Permite verificar qué prompt se usó sin almacenar el contenido |
| `prompt_version` | Commit hash o tag de la build instalada | Localiza el prompt exacto en `git log` |
| `llm_provider` / `llm_model` | Runtime | Trazabilidad del modelo concreto (cambios de proveedor son visibles) |
| `tokens_in` / `tokens_out` / `cost_eur` | Respuesta del LLM | Coste real y volumen procesado por invocación |
| `output_hash` | SHA-256 del output | Verifica que el output no se manipuló post-generación |

### Política de cambio de prompt

Cambiar un prompt requiere:

1. PR con cambio en `backend/app/prompts/<dominio>.txt` y descripción del **motivo**.
2. **Test de regresión** correspondiente (snapshot del prompt) actualizado si la modificación es intencional, fallando si no.
3. Revisión por al menos un dev senior (no el autor del cambio).
4. Si el prompt afecta a un agente high-risk del Anexo III AI Act (caso `hr` con plantilla termination), revisión adicional documentada en `docs/ai_act_scoping.md`.

## §2 Datos de entrenamiento

AutomatizaPyme **no entrena modelos propios**. Usa LLMs de terceros (Anthropic, OpenAI, Groq) como proveedores GPAI. Por tanto las obligaciones de Art. 10 AI Act sobre data governance del training set **no aplican a AutomatizaPyme** — recaen sobre el proveedor GPAI.

### Datos few-shot enviados al LLM

Los prompts pueden contener ejemplos few-shot. Reglas:

* **Cero datos reales de clientes** en los ejemplos. Si un prompt incluye un ejemplo de factura, los nombres/NIFs/IBANs son sintéticos (`B12345678`, `Acme SL`, `ES91 ... 0000`).
* **Revisión periódica**: cada 6 meses se revisa la lista de prompts para detectar PII residual.

### Memoria conversacional

Los agentes mantienen contexto de la conversación actual dentro de la sesión del usuario. Este contexto:

* **Se almacena localmente en el equipo del cliente** (Postgres local). Nunca sale al VPS (MULTI.2).
* **No se reusa entre tenants**: aislamiento por `tenant_id` con RLS Postgres real (SEC.RLS, sprint 3).
* **No se reusa entre ejecuciones** salvo si pertenece al mismo `workflow_execution_id`.

## §3 Supervisión humana (Art. 14)

`autonomy_policy(tenant_id, domain, mode)` consensuada en el debate (Ronda 6):

| Dominio | Modo default | Justificación |
|---|---|---|
| `banking` write | `MANUAL` | Movimientos bancarios = riesgo financiero alto, siempre confirmación humana |
| `accounting` | `CONFIRM` | Asientos contables afectan declaraciones fiscales |
| `marketing` | `CONFIRM` + beta | Comunicación con clientes, riesgo reputacional |
| `recruitment` | `CONFIRM` + beta | Anexo III AI Act, scoring retirado (Escenario A) |
| `hr` | `CONFIRM` para evaluación; `AUTO` para nómina/permisos | Termination plantilla structure-only |
| `billing` | `AUTO` para emisión; `MANDATORY_HUMAN_FISCAL` para presentación AEAT (SEC.APR) | Presentación fiscal exige aprobación humana firmada |
| Resto | `AUTO` | Operaciones administrativas reversibles |

El usuario puede cambiar el modo en `Settings → Agentes → Autonomía` (sprint 8). El modo `MANUAL` significa que el agente nunca ejecuta acciones de escritura sin que el usuario haga clic explícito en "Confirmar".

## §4 Registro de incidentes AI Act

Si un agente:

* Produce un output que el usuario reporta como **erróneo, sesgado, peligroso o ilegal**, se registra en `audit_log` con `status="error"` + `error_detail` describiendo el reporte.
* Es **bloqueado por un validador determinista** (`_invoice_validators.py` u otro), se registra con `status="rejected_by_validator"`.

Un usuario interno designado (DPD si existe, o el fundador) revisa **mensualmente** la lista de incidentes para detectar patrones (mismo agente fallando reiteradamente, mismo tipo de error, etc.). Patrones se traducen a:

* Ajuste de prompt (`backend/app/prompts/*.txt`).
* Validador determinista nuevo o ampliado.
* Cambio de modelo LLM si el problema es del proveedor.

## §5 Tabla resumen de cumplimiento

| Obligación AI Act | Implementación |
|---|---|
| Art. 10 — data governance | N/A (no entrenamos modelos propios) + cero PII en prompts |
| Art. 11 — technical documentation | Este documento + `docs/ai_act_scoping.md` + ARCHITECTURE.md |
| Art. 12 — record-keeping | `AgentExecutionTrace` con prompt_hash + output_hash + tokens (SEC.WORM, retención ≥ 6 meses) |
| Art. 13 — transparency to deployer | Cláusula EULA (AI.EULA) + landing page + documentación de uso |
| Art. 14 — human oversight | `autonomy_policy` configurable + `MANDATORY_HUMAN_FISCAL` para actos fiscales |
| Art. 15 — accuracy/robustness | Tests deterministas + validadores post-tool-call + `autonomy_policy` por defecto restrictivo |
| Art. 50 — transparency to end user | Banner *"Estás interactuando con un sistema de IA"* (AI.BAN, sprint 8) |

## §6 Revisión periódica

Este documento se revisa **trimestralmente** y tras cualquier cambio sustantivo en:

* Lista de agentes activos.
* `autonomy_policy` defaults.
* Proveedores LLM utilizados.
* Modelo de retención de trazas (`AgentExecutionTrace`).

Revisión registrada en `git log` de este archivo.
