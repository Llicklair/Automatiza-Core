# Diagnóstico de salud del proyecto — 2026-06-22

Objetivo de la sesión: entender el estado real ("uso propio / explorar") y decidir
dónde afinar. Foco: diagnóstico primero, sin presión externa.

## Veredicto en una frase

**La base está sana.** Todos los checks que BLOQUEAN el CI están en verde. Lo que
queda es deuda *intencional* (formato/tipos en rampa) y un puñado de mejoras
concretas de calidad — nada roto.

## Resultados (espejo del CI, `.github/workflows/ci.yml`)

| Check | Bloqueante | Estado | Detalle |
|-------|-----------|--------|---------|
| Frontend `tsc --noEmit` | Sí | ✅ PASS | 0 errores |
| Frontend ESLint (`--max-warnings 20`) | Sí | ✅ PASS | 0 errors, **16 warnings** (margen 4) |
| Backend Ruff lint | Sí | ✅ PASS | 0 violaciones |
| Backend Ruff format `--check` | No (advisory) | ⚠️ | 365/656 ficheros divergen del estilo |
| Backend mypy `--strict` (agents+services) | No (advisory) | ⚠️ | ~1587 gaps de tipo |
| Pytest recogida (`--collect-only`) | — | ✅ | 2239/2280 recogidos, 0 errores de import |

> Pendiente de ejecutar de verdad: las suites de tests (frontend `test:ci` y backend
> `pytest` contra Postgres). "Recogido" ≠ "pasa". Coverage floor actual: 57% (objetivo 70%).

## Hallazgos verificados

1. **Falso positivo descartado:** los 13 `name-defined` de mypy (`models.Workflow`,
   `models.Task`, `models.WorkflowExecution` en `services/workflow/`) NO son bug.
   `app/db/models/models.py` re-exporta esas clases (líneas 51 y 62). Es la regla
   `--no-implicit-reexport` de mypy strict quejándose de un re-export sin `as`/`__all__`.
   Coste de silenciarlo limpiamente: trivial (añadir `__all__` a `models.py`).

2. **16 warnings ESLint `react-hooks/exhaustive-deps`** (1 por fichero, repartidos por
   dashboard). NO son cosmética: deps incompletas en `useEffect`/`useCallback` son la
   causa clásica de "la pantalla no se actualiza / muestra datos viejos". Alineado con
   "que funcione mejor". Margen del gate: 16/20 (cualquier hook nuevo lo rompe).

## Recomendaciones priorizadas (valor / esfuerzo / riesgo)

| # | Acción | Valor para "funcione mejor" | Esfuerzo | Riesgo |
|---|--------|------------------------------|----------|--------|
| 1 | **Correr las suites de tests** (front + back) para confirmar que pasan, no solo que compilan | Alto (confianza real) | Bajo-Medio | Bajo |
| 2 | **Arreglar los 16 `exhaustive-deps`** (bugs latentes de UI) y bajar el margen del gate | Alto | Medio | Bajo |
| 3 | Revisar los "bugs pendientes" anotados en `tasks/lessons.md` (p.ej. surfacing de fallos de migración Alembic en Electron) y verificar cuáles siguen abiertos | Medio-Alto | Medio | Bajo |
| 4 | Añadir `__all__` a `models.py` → limpia 13 falsos positivos de mypy | Bajo | Trivial | Nulo |
| 5 | `ruff format` por tandas (subir a bloqueante) | Bajo (cosmético) | Alto | Bajo |
| 6 | Reducir gaps de tipo mypy por módulo (empezar por `pdf_reports/`) | Bajo-Medio (largo plazo) | Alto | Bajo |

## Recomendación

Empezar por **#1 y #2**: confirmar que los tests pasan (no asumirlo) y arreglar los
exhaustive-deps, que son los únicos con olor a "algo no funciona bien" de verdad.
El resto (#4-#6) es higiene que puede ir por tandas sin prisa.
