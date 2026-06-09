# Plan de iteración con el LLM — listo para correr (2026-06-09)

**Estado: el harness YA existe y cubre todo.** No hay que construir nada nuevo;
solo darle al play cuando confirmes (consume tokens). Harness =
`backend/scripts/smoke_orchestrator.py` (Task real en DB + veredicto PASS/FAIL
estricto + `--only/--skip/--strict`).

## Cobertura actual (matriz de casos)

**Ronda 1 — aislamiento por dominio (13 dominios):**
crm · billing · recruitment · reports · email (×3: send/summarize/search) ·
documents · hr (nómina) · banking (conciliación) · compliance (vencimientos+BOE) ·
accounting (libro diario) · **marketing (plan→borradores)** · excel · rag · uploads.

**Ronda 2 — end-to-end multiagente (cadenas):**
recruitment→calendar→email · documents→accounting→banking · crm→contrato→email ·
+ casos base (multi_billing_email, complex_chain) y negativos (ambiguous, impossible).

## Prerrequisitos (ANTES de correr)
1. **LLM configurado**: API key Anthropic en el entorno/app (BYOK). Sin clave los
   agentes no llaman al LLM → todo falla. (Ver pilot-readiness #1.)
2. **BD arrancada**: la app abierta levanta Postgres en 5433. Export
   `DATABASE_URL=postgresql+asyncpg://pyme_user:pyme_pass@localhost:5433/pyme_db`.
3. **Orden / seed**: algunos casos encadenan (`billing_simple` asume el cliente
   "Acme Smoke" de `crm_simple`). Correr en orden o sembrar antes.
4. **Cache classifier (24 h)**: si se itera sobre keywords, invalidar
   (`c:\tmp\clear_classify_cache.py`) o esperar.
5. Tras cualquier cambio de backend, **reiniciar la app** (backend embebido) o
   correr el script standalone con el venv del repo.

## Cómo correr
```
# batería completa, modo test (exit 1 si algún FAIL)
DATABASE_URL=...  python backend/scripts/smoke_orchestrator.py --strict
# solo unos casos
python backend/scripts/smoke_orchestrator.py --only iter10_marketing,iter8_compliance
# saltar casos
python backend/scripts/smoke_orchestrator.py --skip e2e1_recruit_email_calendar
```

## Qué valida el veredicto
PASS/FAIL por caso: **clasificación de dominio correcta + status `done` + ningún
agente `success=False`**. Negativos (ambiguous/impossible): PASS si pide aclaración
o falla elegante (FAIL si alucina tools). Salida = tabla + reporte en `tasks/`.

## Telemetría a capturar por iteración (del plan previo en todo.md)
- ¿clasificador acertó el dominio? (logs `classifier.py`)
- ¿tool ejecutada = esperada? (registry hit en `tool_registry.py`)
- tokens consumidos + latencia LLM
- ¿activity log / task_event_hub registraron el evento?
- Fallo → entrada en `tasks/lessons.md` con regla de prevención.

## Notas de esta sesión (los 2 dominios que mencionaste)
- **Marketing** (ya es dominio, lo reforzamos): caso `iter10_marketing` actualizado
  al flujo real (`create_post`, no el inexistente `generate_copy`). La publicación
  real necesita una **cuenta social conectada** (OAuth) → el smoke valida
  *routing + creación de borrador*, no el publish a Meta/X.
- **Fiscal**: la generación de modelos AEAT (303/130/111/…) **NO es conversacional**
  hoy — va por rutas API + UI `/impuestos`, no por tools del agente. Por eso **no
  está en el smoke del Coordinador**; se valida con `test_modelo*`/`test_aeat*`
  (route/service). Si se decide **promover fiscal a dominio** (decisión #3, ver
  depth-audit.md), entonces añadir aquí casos tipo "genérame el 303 del Q2".

## Coste estimado
~30 casos × 1-5 llamadas = **~75-90 llamadas LLM**; esperar 30-40% cache-hit del
classifier dentro de una misma ronda.

## Resultado esperado / criterio Go-No-Go
Matriz dominio×tool con verde/rojo. Si <90% verde en Ronda 1, no pasar a Ronda 2;
cada FAIL → causa raíz + fix + lección. (Última corrida registrada: 8/8 v2, 0 fails.)
