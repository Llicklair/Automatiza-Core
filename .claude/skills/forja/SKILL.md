---
name: forja
description: "Loop completo de Loop Engineering (Secc. XII del documento) para TODO el proyecto: descubre trabajo (inbox -> gates), GENERA el arreglo en un worktree aislado, lo VERIFICA con un evaluador escéptico independiente (/goal: repite hasta que los gates pasan), abre PR (NUNCA auto-merge) y vuelve a empezar. Portable a cualquier producto. Úsalo como /loop forja."
---

# /forja — el loop que escribe, verifica y abre PR (sin que teclees tú)

Loop completo del documento: el **generador** (`fixer`) escribe; el **evaluador**
(`code-reviewer`/`fiscal-reviewer`, otro modelo, escéptico, **ejecuta** los gates) juzga con
condición de parada **/goal** y repite hasta verde; **worktree por tarea**; **PR abierto,
NUNCA auto-merge**; estado en disco. El generador no se auto-aprueba: el evaluador es el que
dice "no". **Tú sigues siendo el ingeniero**: revisas y mergeas los PRs (la "puerta abierta").

## Portabilidad (cualquier producto)
Detecta los gates del proyecto, no los hardcodees: lee `.github/workflows/*.yml`,
`package.json` (scripts) y `pyproject.toml`. En ESTE repo hoy:
- backend/: `poetry run pytest -q` · `poetry run ruff check app/ --select E,W,F,I --ignore E501,E402,E701,E702,E731,W293` (bloqueante) · `poetry run mypy app/agents app/services --strict --ignore-missing-imports` (señal)
- frontend/: `npx tsc --noEmit` · `npx eslint src/ --max-warnings 20` · `npm run test:ci`

## Modo y caps (circuit breakers — el loop se equivoca solo)
- **Rama acumuladora**: TODOS los fixes van a UNA rama `loop/forja/auto` con UN solo PR que
  crece (no PR por item). Worktree persistente `.claude/worktrees/forja-auto`, reutilizado
  entre turnos (no recheckout por turno).
- **1 item por turno. Continuo SIN tope**: encadena turnos (~2 min) hasta agotar cuota.
- Máx **3 rondas** generador↔evaluador por item; si no pasa → revierte ese commit en la
  rama (`git reset --hard HEAD~1` en el worktree) y manda el item a `tasks/ronda/inbox/`.
- **Para por cuota**: si los agentes fallan por límite/cuota, detén el loop y presenta el
  resumen (protocolo en `tasks/forja/state.md`).

## Los 5 movimientos (un turno)

### 1. DISCOVERY — EXPLORA el proyecto y descubre defectos reales (nonstop)
> "Discovery sets the ceiling on the whole loop's quality." (documento, Secc. III)
El loop **NO espera a que cambie el código: explora activamente**, como las Minions del
documento. Cada turno avanza y descubre; nunca idle salvo cuota.

Orden:
1. **Primero lo urgente (si lo hay)**: fallos BLOQUEANTES en vuelo (test rojo, ruff/tsc/eslint
   con error — re-corre gates solo si master cambió desde `last_clean_sha`) e **inbox**
   substantivo (`tasks/ronda/inbox/`, sin "RESUELTO").
2. **Barrido de exploración (rotativo)**: si no hay urgente, coge el SIGUIENTE área del sweep
   (lista + `cursor` en `tasks/forja/state.md`). Lanza un FINDER (`code-reviewer` no-fiscal /
   `fiscal-reviewer` fiscal) a EXPLORAR esa área en el worktree acumulador y listar **defectos
   reales**: bugs de correctitud, casos borde sin manejar, fugas de recursos, falta de filtro
   de tenant, agujeros de seguridad, manejo de errores ausente, código muerto con riesgo.
   **Avanza el cursor cada turno** → con el tiempo cubre todo el proyecto, y al terminar la
   lista vuelve a empezar (pasadas más profundas).

**JUDGE + VERIFY (lo que mantiene el PR limpio y seguro):**
- ¿DEFECTO real con arreglo CLARO y objetivo? → candidato a fix.
- ¿Subjetivo / refactor de gusto / mejora opinable? → a `tasks/ronda/inbox/` (lo PROPONES,
  NO lo auto-arreglas). El loop arregla defectos, no impone opiniones.
- ¿Advisory/cosmético (mypy type-args, formato)? → descártalo (no al PR).
- ¿Ya en vuelo (bitácora + ramas `loop/forja/*`)? → sáltalo.
- **Anti-falso-positivo**: antes de tocar nada, CONFIRMA que el defecto es real (reprodúcelo:
  un test que falla, una traza, un caso concreto). Si no lo puedes confirmar → inbox, no fix.
- Toma el defecto verificado de mayor impacto + dale su **/goal** objetivo.
- Si el área no tiene defectos reales → márcala "barrida", avanza el cursor; el siguiente
  turno explora otra. **Exploras, no te detienes.**

### 2. HANDOFF — worktree acumulador persistente
- Usa el worktree persistente `.claude/worktrees/forja-auto` en la rama `loop/forja/auto`.
  Si no existe: `git worktree add .claude/worktrees/forja-auto -b loop/forja/auto` desde master.
  Reutilízalo entre turnos (no recheckear el árbol cada vez).

### 3. GENERATE — el generador escribe
- Lanza el sub-agente `fixer` (Agent tool, `subagent_type: "fixer"`) apuntándolo a la RUTA
  del worktree, al item y a su /goal. Implementa el arreglo y commitea en la rama.

### 4. VERIFY — generador↔evaluador hasta /goal
- Lanza el evaluador: `fiscal-reviewer` si el item es FISCAL, `code-reviewer` si no.
  Corre los gates EN el worktree y comprueba el /goal (asume roto, ejecuta).
- Si REJECT → pasa los fallos de vuelta al `fixer` para otra ronda (máx 3).
- Si PASS → sigue a persistencia. Si tras 3 rondas no pasa → revierte ese commit en el
  worktree (`git -C .claude/worktrees/forja-auto reset --hard HEAD~1`), anota el item en
  `tasks/ronda/inbox/` ("el loop no pudo; necesita humano") y pasa de turno.

### 5. PERSISTENCE + PUERTA HUMANA — rama acumuladora, UN PR, nunca merge
- El commit del fixer ya está en `loop/forja/auto`. Push:
  `git -C .claude/worktrees/forja-auto push -u origin loop/forja/auto`.
- Asegura UN solo PR (créalo la primera vez; luego solo crece con cada push):
  `gh pr list --head loop/forja/auto --state open`; si no hay → `gh pr create --base master
  --head loop/forja/auto --title "loop/forja: arreglos automáticos (acumulado)"`. Si ya
  existe, NO crees otro (el push lo actualiza).
  - Si `gh` falla → deja la rama pusheada y reporta la URL; no bloquees el loop.
- **NUNCA mergees.** NO elimines el worktree (se reutiliza entre turnos).
- Anota en `tasks/forja/state.md` (bitácora): item, veredicto, PR.

### Cierre / scheduling
- Reprograma el siguiente turno (lo gestiona `/loop`). Para por cuota según el protocolo.

## Las cuatro deudas silenciosas (vigílalas — el documento, Secc. VIII)
- **Verificación** → evaluador independiente + /goal.
- **Comprensión** → TÚ revisas cada PR; el loop nunca mergea. Lee una muestra de verdad.
- **Rendición** → el loop ejecuta y propone; **tú decides** qué se mergea.
- **Token blowout** → caps de arriba + parada por cuota.

> El loop es un multiplicador del que lo construye. Está hecho para que sigas siendo el
> ingeniero: escribe y propone, pero el merge —y el juicio— son tuyos. Si /forja lleva
> muchos turnos sin que el evaluador rechace nada, sospecha del evaluador, no lo celebres.
