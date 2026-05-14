# PR — [tipo]: [descripción corta]

> Usar este template al abrir cualquier PR. Copia/pega como descripción.

## Contexto

- **Backlog ID**: `XXX.NN` (referencia a `tasks/backlog.md`)
- **Eje**: producto técnico / seguridad / legal / pricing / UX / distribución / customer ops / AI Act / multi-actor / i18n / modelos AEAT / presentación
- **Sprint**: N
- **Categoría commit**: `feat` / `fix` / `refactor` / `docs` / `test` / `chore`

## Qué cambia

[1-3 frases describiendo el cambio. Por qué, no qué.]

## Impacto

- [ ] `gitnexus_impact({target: "<símbolo>", direction: "upstream"})` ejecutado
- [ ] Blast radius reportado: **direct callers** = N, **processes afectados** = N, **risk level** = LOW/MEDIUM/HIGH/CRITICAL
- [ ] Si risk = HIGH/CRITICAL, justificar por qué se procede igual

## Tests

- [ ] Tests unitarios añadidos/actualizados
- [ ] Tests de integración si afecta a flujo cross-domain
- [ ] Idempotencia verificada si afecta a tools de agente
- [ ] `pytest` pasa en local
- [ ] `vitest run` pasa en local (si toca frontend)
- [ ] `mypy` sin nuevos errores en `agents/` o `services/`

## Migración / schema

- [ ] **No toca `db/models/`** → marcar y saltar este bloque
- [ ] **Toca `db/models/`** → migración Alembic incluida en este PR
- [ ] Migración aplica limpio en BD vacía (`alembic upgrade head`)
- [ ] Migración revierte limpio (`alembic downgrade -1`)
- [ ] Si añade columna nueva con NOT NULL, backfill incluido o default razonable

## Seguridad / AI Act

Marcar lo que aplique:

- [ ] No toca datos personales / no toca decisiones que afecten a personas físicas
- [ ] Toca datos personales → revisado contra GDPR (logging IBAN/NIF, retención, finalidad)
- [ ] Toca evaluación / ranking / profiling de personas físicas → revisado contra AI Act Anexo III; documentado en `docs/ai_act_scoping.md`
- [ ] Toca presentación tributaria → verificación humana obligatoria conservada (`MANDATORY_HUMAN_FISCAL`)
- [ ] Toca claves / secretos → custodiados en `SecretStore`, nunca en `.env` plano ni `localStorage`

## Detect changes

- [ ] `gitnexus_detect_changes()` ejecutado
- [ ] Scope coincide con lo esperado (sin archivos sorpresa)

## Checklist final

- [ ] Commit messages siguen convención `<tipo>(<componente>): <descripción>`
- [ ] No hay `console.log` / `print` de debug
- [ ] No hay secretos hardcoded
- [ ] CLAUDE.md / ARCHITECTURE.md actualizados si cambian invariantes
- [ ] `tasks/backlog.md` actualizado con estado del item (WIP → DONE)
- [ ] Si fix de bug, lección añadida a `tasks/lessons.md`

## Notas para el revisor

[Cualquier cosa que el revisor deba saber: decisiones de diseño, alternativas descartadas, dependencias siguientes.]
