# Sprint 1 — Fundación (18-22 may 2026)

> **Objetivo del sprint**: descongelar lo bloqueante. Sin estas tareas cerradas, los Sprints 2-9 trabajan sobre cimientos rotos.
>
> **Definition of Done del sprint**: M1 alcanzado (Alembic baseline + AI.AUDIT memo + JWT en safeStorage + numeración correlativa lista para Sprint 2 + CONT.0 fallback eliminado).

## Asignación de devs

- **dev1** backend senior — Alembic + ALB.*
- **dev2** fullstack — AI.AUDIT exhaustivo + SEC.IBAN + CONT.0
- **dev3** frontend/UX — SEC.JWT (migración localStorage → safeStorage) + setup CI frontend

## Decisiones admin que deben cerrarse antes del lunes

- [ ] **vie 15-may o sáb 16-may** — DEC.02 firmada (autónomo)
- [ ] **dom 17-may** — gestor y abogado pre-contactados, llamada agendada para lunes
- [ ] **dom 17-may** — repo accesible para los 3 devs + onboarding técnico breve

## Day-by-day

### Lunes 18-may

**dev1** — Alembic baseline arranque

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | `alembic init` + configuración `env.py` con conexión Postgres local | Verificar que `alembic upgrade head` corre contra BD vacía |
| 14:00-18:00 | `alembic revision --autogenerate -m "baseline"` + revisión manual | Comparar contra `_ensure_schema()` actual; documentar discrepancias |

**dev2** — AI.AUDIT planning + primeros 3 agentes

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | Lectura `agents/recruitment/` + `agents/hr/` + `agents/compliance/` ya auditados como referencia. Plantilla memo `docs/ai_act_scoping.md` | Definir patrones grep exactos antes de empezar |
| 14:00-18:00 | Grep + análisis 3 agentes: `banking`, `crm`, `marketing` (capas agents/services/db/models) | Anotar hallazgos en draft del memo |

**dev3** — SEC.JWT planning + safeStorage wrapper

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | Leer `frontend/src/lib/api/client.ts` + tests existentes + diseñar wrapper `lib/secureStore.ts` que abstraiga `electron.safeStorage` con fallback a `localStorage` solo en `import.meta.env.DEV` | Mantener compatibilidad con tests jsdom |
| 14:00-18:00 | Implementar `secureStore.ts` + tests vitest mockeando electron API | TDD: tests primero, implementación después |

**Daily standup (18:00-18:15)**: cada dev cuenta qué cerró, qué tiene pendiente para mañana, qué bloqueos hay.

---

### Martes 19-may

**dev1** — Alembic baseline cierre + drift detection

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-12:00 | Refinar `versions/0001_baseline.py` hasta que `alembic upgrade head` en BD vacía produzca esquema idéntico al actual | Verificar con `pg_dump --schema-only` antes/después |
| 12:00-13:00 | Pre-flight cert pruebas FNMT: `dev1` o gestor solicita online (10 min, gratis) para que homologación AEAT esté lista | Cubre PRES.HOM |
| 14:00-18:00 | ALB.2 script de drift detection (compara `db.metadata.create_all()` contra BD real, reporta diferencias) | Útil para detectar BDs de testers en estado intermedio |

**dev2** — AI.AUDIT 3 agentes más

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | Grep + análisis `accounting`, `email`, `documents` | Misma metodología que lunes |
| 14:00-18:00 | Grep + análisis `uploads`, `validators`, `rag` | Cierre del scan inicial |

**dev3** — SEC.JWT migración

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | Sustituir `localStorage.getItem/setItem` por `secureStore` en `client.ts:23,27,37,38` | Verificar refresh token flow (línea 36-38) sigue funcionando |
| 14:00-18:00 | Actualizar tests `__tests__/client.test.ts` (10 referencias a localStorage) | Mock secureStore en setup global |

---

### Miércoles 20-may

**dev1** — DROP COLUMN + eliminar `_ensure_schema`

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | ALB.3 añadir `DROP COLUMN Candidate.score, Candidate.score_breakdown` a baseline + cualquier columna detectada por AI.AUDIT como AI Act-related | Coordinar con dev2 para conocer hallazgos AI.AUDIT |
| 14:00-18:00 | ALB.4 eliminar `_ensure_schema()` del lifespan en `backend/app/main.py` + verificar arranque limpio | Buffer 1h para fixes derivados |

**dev2** — AI.AUDIT memo + cierre

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | Consolidar hallazgos en `docs/ai_act_scoping.md` con clasificación por agente (prohibido/high-risk/limited/minimal) + justificación Art. 6(3) si aplica | Una fila por agente |
| 14:00-16:00 | Revisión cruzada con dev1: pasar lista de columnas AI Act-related a ALB.3 | Coordinación crítica |
| 16:00-18:00 | Empezar SEC.IBAN: función `mask_iban()` en `core/security.py` | TDD recomendado |

**dev3** — SEC.JWT tests + setup CI

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | Verificación end-to-end: arrancar app, login, verificar que tokens van por safeStorage (Electron DevTools network + storage inspector) | Bug bash propio |
| 14:00-18:00 | Setup CI gates frontend: `vitest run --coverage` + `axe-core` (preparación para QA.AXE) + `eslint --max-warnings 0` | Crear `.github/workflows/frontend.yml` o equivalente |

---

### Jueves 21-may

**dev1** — `alembic upgrade head` en arranque + revisión

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | ALB.5 ejecutar `alembic upgrade head` desde `desktop/python-manager.js` antes de levantar FastAPI | Manejar errores de migración con UI explicativa al usuario |
| 14:00-18:00 | Pre-commit hook (ALB.6) que verifica si se modifica `db/models/` exista migración asociada en el commit | Husky o pre-commit framework |

**dev2** — SEC.IBAN integración

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | Integrar `mask_iban()` en formatter del logger global (`core/logging.py`) — todos los logs IBAN saldrán enmascarados automáticamente | Tests con casos límite (IBAN corto, vacío, malformado) |
| 14:00-18:00 | Auditar logs existentes que ya emiten IBAN sin máscara + sustituir + smoke test | Buscar `.log\b.*iban\b` y similares |

**dev3** — CI frontend cierre

| Bloque | Tarea | Notas |
|---|---|---|
| 09:00-13:00 | Configurar threshold cobertura ≥40% inicial (subirá a 80% en sprint 9) | Excluir Generated UI components |
| 14:00-18:00 | Documentar workflow CI en `tasks/dev/ci-frontend.md` (cómo arrancar, qué falla bloquea merge) | Onboarding doc para devs futuros |

---

### Viernes 22-may — Cierre Sprint 1

**Todos** — Revisión cruzada + smoke + retrospectiva

| Bloque | Tarea | Owner | Notas |
|---|---|---|---|
| 09:00-11:00 | CONT.0 — eliminar fallback `2026-04-20` literal en `agents/compliance/tools.py:53,58`. Sustituir por cache + `data_stale=true` propagado al UI | dev2 | Es el último día del sprint, perfecto para una tarea contenida |
| 11:00-13:00 | Smoke test end-to-end conjunto: instalador → primer arranque → migración Alembic → login → JWT en safeStorage → logout | dev1+dev2+dev3 | Bug bash conjunto |
| 14:00-16:00 | Fix bugs encontrados en smoke | quien proceda | |
| 16:00-17:00 | Retrospectiva sprint 1 — usar `tasks/templates/sprint-retro-template.md` | todos | Documentar en `tasks/sprints/sprint-1-retro.md` |
| 17:00-18:00 | Planning Sprint 2 — repaso de tareas + asignación + bloqueos detectados | todos | |

## Definition of Done — checklist final

Sprint 1 cierra si y solo si:

- [ ] **ALB.1** Alembic baseline aplica limpio en BD vacía y produce esquema idéntico al actual
- [ ] **ALB.2** Drift detection script ejecuta sin errores
- [ ] **ALB.3** Columnas AI Act-related identificadas en AI.AUDIT incluidas en `DROP COLUMN` de baseline
- [ ] **ALB.4** `_ensure_schema()` eliminado del lifespan; `main.py` no aplica esquema en runtime
- [ ] **ALB.5** `alembic upgrade head` corre desde `python-manager.js` antes de FastAPI
- [ ] **ALB.6** Pre-commit hook bloquea PRs que modifican `db/models/` sin migración
- [ ] **AI.AUDIT** `docs/ai_act_scoping.md` entregado con clasificación de los 9 agentes restantes + lista de columnas AI Act-related encontradas
- [ ] **SEC.JWT** `client.ts` no usa `localStorage` para tokens; tests pasan en CI
- [ ] **SEC.IBAN** `mask_iban()` integrado en logger; logs emiten IBANs enmascarados
- [ ] **CONT.0** Fallback `2026-04-20` eliminado; UI muestra banner `data_stale` cuando aplica
- [ ] **CI frontend** Pipeline ejecuta vitest + axe-core + eslint y bloquea PRs si falla
- [ ] **Decisiones admin** DEC.02, DEC.06, DEC.14a, DEC.01, DEC.04 firmadas; DEC.14 iniciada; cert pruebas FNMT solicitado

## Riesgos del sprint

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| AI.AUDIT detecta un agente con scoring real no previsto | 25% | Coordinación dev1↔dev2 el miércoles para incluir DROP COLUMN inmediato; ajustar Escenario A en sprint 2 si necesario |
| Migración Alembic detecta drift entre BD de tester y modelos | 60% | ALB.2 está diseñado para esto; el drift se documenta y se resuelve con migración cero antes del baseline |
| `safeStorage` Electron no disponible en dev mode jsdom | 40% | Wrapper con fallback a `localStorage` cuando `process.env.NODE_ENV === 'development'` |
| Algún dev arranca tarde por DEC.* no firmadas | 15% | Si lunes 18-may a las 10:00 no hay DEC.02 firmada, el sprint se desliza 1 día — comunicar al fundador el viernes 15 |

## Notas operativas

- **Standup diario 18:00**: 15 min, formato "qué cerré / qué hago mañana / bloqueos".
- **Canal comunicación**: Slack/Discord/Teams a elección, separar canales por dominio (#sprint-1, #incidencias).
- **Commits**: convención `<categoría>(<componente>): <descripción>`, por ej. `feat(alembic): baseline migration generated from current schema`.
- **PRs**: usar `tasks/templates/pr-template.md` — incluye checklist `gitnexus_impact` + tests + migración si toca models.
