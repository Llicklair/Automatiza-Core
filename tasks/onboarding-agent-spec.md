# Spec — Agente de Onboarding para conversión en los primeros 5 minutos

> Entregable de la tarea #10 del Consejo de los 7 Sabios (informe 2026-05-31).
> Objetivo: diseñar un agente de onboarding que lleve al usuario a su primera
> acción de valor en <5 min, **construyendo sobre la infraestructura que ya
> existe** — no reinventándola.

## 1. Qué existe hoy (auditoría, no suposición)

Dos flujos guiados ya implementados como rutas REST aisladas, sin conexión con
el orquestador (`agents/orchestrator/`) ni el layer de workflows
(`services/workflow/`):

### 1.1 Wizard de onboarding focado — `UI.ONB`
- Ruta: `backend/app/api/v1/routes/onboarding_wizard.py` (prefix `/onboarding/wizard`).
- Servicio: `app/services/onboarding/wizard.py` (`get_state`, `set_step`, `skip_to_end`, `reset`, `to_dict`).
- Estado por tenant con 4 pasos booleanos: `step_company`, `step_cert`, `step_data`, `step_use_case` + `completed_at` / `skipped_at` / `is_dismissed`.
- Extra: `GET /simulate/303` → `simulate_modelo_303` muestra un Modelo 303 calculado sobre un autónomo prototípico **antes** de que el usuario meta sus datos (gancho de valor inmediato).

### 1.2 Wizard REGAP (apoderamiento AEAT) — `PRES.REG`
- Ruta: `backend/app/api/v1/routes/onboarding_regap.py` (prefix `/onboarding/regap`, **admin-only**).
- Servicio: `app/services/onboarding/regap.py`.
- Máquina de estados: `not_started → identifying → cert_pending → power_granted → verified` (+ `rejected`).
- Métodos de auth: `clave_pin | clave_permanente | cert_fnmt`.
- `verify_regap_consulta` está **mockeado (v1.0)** — no consulta REGAP real todavía.

### 1.3 Ambos están registrados solo como rutas
`grep` confirma que `onboarding_wizard` / `onboarding_regap` aparecen únicamente
en `api/v1/router.py`. **Cero referencias desde `agents/orchestrator/` o
`services/workflow/`.** El usuario avanza el wizard a mano, paso a paso.

## 2. El gap

El wizard es **pasivo**: registra qué pasos completó el usuario, pero no *hace*
nada por él. El valor del producto (descomponer "prepárame mi primera factura"
en tareas del orquestador) no se demuestra durante el trial. El agente de
onboarding cierra ese gap convirtiendo cada paso del wizard en una acción
ejecutada por el orquestador.

## 3. Diseño propuesto (incremental, 3 fases)

### Fase 1 — Telemetría primero (NO arquitectura)
**No diseñar el agente hasta saber dónde abandonan los usuarios.** Instrumentar
los flujos existentes:
- Emitir evento por transición de paso del wizard (`company`, `cert`, `data`, `use_case`) y por cada estado REGAP.
- Métrica clave: tasa de abandono por paso + time-to-first-value.
- Hipótesis a validar: ¿el 80% cae en el paso `cert` (subida de certificado / REGAP)? Si es así, el agente debe priorizar simplificar el apoderamiento, no descomponer plantillas de factura.

### Fase 2 — Agente de onboarding (`agents/onboarding/`)
Estructura obligatoria (ARCHITECTURE.md):
```
agents/onboarding/
├── __init__.py       ← exporta solo run_agent()
├── agent.py          ← LangGraph + run_agent()
├── tools.py          ← @tool: get_wizard_state, advance_step, simulate_303, start_regap...
├── prompts.py        ← system prompt: "guía al usuario a su 1ª factura en <5 min"
└── _*.py             ← privados
```
- **No** llama a otros agentes (regla de comunicación): orquesta vía `services/workflow/` o servicios compartidos.
- Las `tools` envuelven los servicios YA existentes (`wizard.py`, `regap.py`, `simulate_303.py`) — no se reimplementa lógica.
- Devuelve `AgentResult(success=False)` ante errores, nunca lanza al orquestador.

### Fase 3 — Cableado al orquestador (Coordinador)
- El Coordinador (`agents/orchestrator/`) reconoce intents de onboarding ("configura mi empresa", "enséñame con un ejemplo") y delega al agente de onboarding.
- El agente descompone "prepara mi primera factura" → tareas concretas (alta de empresa → simulación 303 → plantilla factura) y las ejecuta, mostrando valor en la primera sesión.
- Reutilizar `simulate_303` como primer "momento ajá" antes de pedir datos reales.

## 4. Criterios de aceptación
- [ ] Telemetría de abandono por paso desplegada y con ≥1 semana de datos antes de construir el agente.
- [ ] `agents/onboarding/` sigue la estructura mandatoria; único export público `run_agent()`.
- [ ] Las tools son envoltorios finos sobre `services/onboarding/*` (sin duplicar lógica de estado).
- [ ] El agente no importa otros agentes.
- [ ] Un usuario nuevo llega a una acción de valor (303 simulado o 1ª factura) sin salir del chat.

## 5. Hilos de investigación abiertos (del informe)
- Journey real trial→primera acción: instrumentar antes de arquitecturar.
- `verify_regap_consulta` está mockeado: decidir si el agente puede prometer verificación real o solo guiar el apoderamiento manual en Sede AEAT.

## 6. Fuera de alcance de esta spec
- Implementación del agente (esto es solo el diseño).
- Wiring real de REGAP contra AEAT.
- Cableado del metering de interacciones (tarea independiente; ver `metering.py`).
