# Gates de calidad en CI (QA.CI)

> **Versión 1.0 — 2026-05-15**.

El workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)
implementa gates que **bloquean el merge** a `main`/`develop` si no se
cumplen. Esta guía documenta qué gates hay, por qué, y cómo subirlos.

## §1 Pinning de versión Python

```yaml
env:
  PYTHON_VERSION: "3.11.9"
```

Coincide con la versión del binario embebido en el instalador Electron
(ver `dependencies/embedded_binaries.json`). **Bumpear ambos a la vez**
o el código del backend testado en CI no será idéntico al ejecutado en
cliente.

## §2 Mypy estricto en agents/ y services/

```yaml
- name: Mypy strict en agents y services
  run: poetry run mypy app/agents app/services --strict --ignore-missing-imports
```

Decisión Ronda 32: los dominios donde vive la lógica de negocio
(agents, services) requieren tipos estrictos. Rutas API y migrations
toleran tipos laxos (`continue-on-error: true`) porque su superficie
cambia mucho y el coste de tipar todo a estricto no compensa.

Reglas activadas por `--strict`:
- `disallow_untyped_defs` — todas las funciones tipadas.
- `disallow_incomplete_defs` — no se permiten anotaciones parciales.
- `no_implicit_optional` — `def f(x: str = None)` falla.
- `warn_unused_ignores` — los `# type: ignore` huérfanos fallan.
- `warn_return_any` — `Any` implícito de un return.

## §3 Coverage backend ≥ 70%

```yaml
poetry run pytest tests/ --cov=app --cov-fail-under=70
```

Subido del 50% inicial. Si una PR baja la cobertura del 70%, CI falla.

**Cómo subir**: cuando añades una feature nueva, añades tests. Los PR
de bugfix también deben añadir el test de regresión que evidencia el
bug ANTES del fix.

## §4 Coverage frontend ≥ 20% (target 40%)

Configurado en `frontend/vitest.config.ts`:

```ts
thresholds: { lines: 20, functions: 20, branches: 20, statements: 20 }
```

Empieza en 20% conservador para no romper CI. **Ramp-up planificado**:
cada quarter se sube 5 puntos hasta el target consenso de 40%.

| Trimestre | Objetivo lines |
|---|---|
| Q2 2026 (actual) | 20% |
| Q3 2026 | 25% |
| Q4 2026 | 30% |
| Q1 2027 | 40% |

El responsable de subir el threshold antes de cerrar el sprint final
del quarter es el dev3 (frontend). Si el threshold queda por encima de
la cobertura actual del momento, CI falla — eso fuerza el ramp.

## §5 Job a11y bloqueante

`frontend-a11y` (UI.A11Y / QA.AXE) corre `npm run test:a11y` con preset
WCAG 2.1 AA. Bloquea `frontend-build`. Sin tests verdes, no hay
instalador.

## §6 Excepciones documentadas

| Gate | Excepción | Justificación |
|---|---|---|
| Mypy strict | Solo agents+services | Routes y migrations tienen forma cambiante; el coste-beneficio del strict no compensa |
| Cov frontend 20% | Empieza bajo | Bootstrapping incremental, ramp documentado arriba |
| `app.isPackaged` skip en autoUpdater test | Tests no son binarios firmados | Test no aplica fuera de release real |

## §7 Cómo desactivar localmente un gate (uso excepcional)

- Mypy strict en local: omitir el flag `--strict` al correr a mano.
- Cov backend en local: `pytest tests/ --no-cov` desactiva el gate.
- Cov frontend en local: `npx vitest run` (no `test:ci`) — sin
  `--coverage` no se aplican thresholds.

CI siempre aplica los gates. Si necesitas saltar uno en CI para
desbloquear un PR urgente:

1. Justificar en la PR description por qué.
2. Marcar el gate como `continue-on-error: true` en el job afectado.
3. Abrir issue follow-up para restaurar el gate.
4. Reviewer debe confirmar la excepción.

## §8 Métricas de la ejecución

Tras cada run de CI, codecov publica el resumen de cobertura. Útil
para detectar regresiones graduales antes de que el threshold falle.

## §9 Próximos gates a añadir (post-MVP)

- **`poetry run alembic check`** — detecta modelos cambiados sin migración (cross-ref ALB.6 hace lo mismo pre-commit).
- **OSV-Scanner** sobre dependencies — CVE matching automático.
- **eslint --max-warnings=0** (hoy `--max-warnings 20`).
- **bundle size check** — frontend build no debe pasar de N KB sin
  justificación.
