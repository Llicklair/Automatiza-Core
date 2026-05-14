# Hooks de BD — drift detection + pre-commit (ALB.2 / ALB.6)

> **Versión 1.0 — 2026-05-14**.

## ALB.2 · Drift detection BD vs modelos

### Cuándo usar

- **Antes** de aplicar la baseline `alembic upgrade head` en una BD de
  tester que existe desde antes de la migración 0001.
- **Después** de cada despliegue en producción, para verificar que la BD
  quedó coherente con `Base.metadata`.
- En CI tras `alembic upgrade head` como sanity check.

### Cómo correrlo

```bash
cd backend
python scripts/db_drift.py
# o contra una BD remota:
python scripts/db_drift.py --db-url "postgresql+asyncpg://user:pass@host:5432/dbname"

# En CI, con código de salida:
python scripts/db_drift.py --exit-code
```

### Salida

- **Sin drift**: `OK — sin drift entre BD y modelos.` + exit 0.
- **Con drift**: informe por categoría + exit 1 (si `--exit-code`):
  - **Tablas declaradas pero ausentes en BD** → falta migración aplicada.
  - **Tablas en BD sin modelo declarado** → tabla legacy o `_ensure_schema`
    vestigial; investigar antes de DROP.
  - **Columnas faltantes** → migración parcial; revisar histórico.

### Limitaciones conscientes

- No compara tipos (`VARCHAR(50)` vs `VARCHAR(100)`) — SQLAlchemy
  normaliza por dialect y una comparación rígida daría falsos positivos
  entre Postgres y SQLite.
- No compara índices ni constraints. Lo añadido por Postgres (índices
  auto en FKs) no se considera drift.
- Tablas `alembic_version` y `spatial_ref_sys` se ignoran (infra).

Para chequeos más estrictos en CI, usar `alembic check` o
`alembic revision --autogenerate` y verificar que el diff es vacío.

## ALB.6 · Pre-commit hook: migración obligatoria si tocas modelos

### Qué hace

Bloquea el commit si:
- El staging incluye cambios en `backend/app/db/models/**.py`
- **Y** el diff toca líneas con `Column(`, `__tablename__`,
  `relationship(`, `ForeignKey(`, `Index(`, `UniqueConstraint(`
- **Y NO** incluye un archivo en `backend/app/db/migrations/versions/`

### Instalación local

Añadir el siguiente bloque a `.git/hooks/pre-commit` (creándolo si no
existe) y darle permisos de ejecución:

```bash
#!/usr/bin/env bash
set -e

# ALB.6 — migration check
python backend/scripts/check_migration.py
```

```bash
chmod +x .git/hooks/pre-commit
```

Alternativa cross-team: añadir el hook a `.pre-commit-config.yaml` y
documentar `pre-commit install` en el README.

### Opt-out (uso excepcional)

Si el cambio en modelos NO afecta al esquema real (renombre de variable
interna, mover imports, refactor del `__init__.py`):

- **Variable de entorno**: `SKIP_MIGRATION_CHECK=1 git commit -m "..."`
- **Marker en commit message**: incluir literal `[skip-migration-check]`
  en el mensaje del commit.

Cualquier uso del opt-out queda en el log del commit — el reviewer puede
auditarlo en PR.

### CI

El mismo script funciona en GitHub Actions como step:

```yaml
- name: ALB.6 — verify migrations accompany model changes
  run: |
    git fetch origin main
    # Diff vs base de la PR (necesita actions/checkout con fetch-depth: 0)
    python backend/scripts/check_migration.py
```

El step lee `git diff --cached` por defecto; en CI conviene adaptarlo
para leer `git diff origin/main...HEAD`.

### Heurística vs estricto

El hook usa una heurística para no bloquear commits triviales (cambiar
un comment, ajustar formatting). La heurística tiene **falsos negativos
posibles**: si añades una `Column` indirectamente vía función helper, el
hook no la detecta. En ese caso confía en el reviewer del PR.

Para máxima estrictez, usar `alembic check` que sí detecta cualquier
desviación entre modelos y BD.

## Tests

- `backend/tests/test_db_drift.py` (6 tests): formato del report y
  detección sobre la BD de tests.
- `backend/tests/test_check_migration.py` (7 tests): cubre cada rama de
  la heurística + opciones de opt-out.
