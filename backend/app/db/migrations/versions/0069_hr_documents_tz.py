"""Columnas de fecha -> timestamptz en hr_documents y generated_uis.

Las columnas eran TIMESTAMP WITHOUT TIME ZONE (naive), pero el modelo y los
servicios insertan datetime.now(UTC) (tz-aware), igual que el resto de la app.
asyncpg rechazaba el INSERT en Postgres con DataError "can't subtract
offset-naive and offset-aware datetimes":
  - hr_documents → la generación de documentos laborales fallaba con
    "Documento generado pero no guardado".
  - generated_uis → mismo bug latente en el sandbox generativo.
SQLite no distingue naive/aware, por eso los tests no lo detectaban. Alineamos a
timestamptz. `IF EXISTS` por si alguna tabla no está creada en un entorno dado.

Revision ID: 0069_hr_documents_tz
Revises: 0068_drop_metering_tables
"""

from alembic import op

revision = "0069_hr_documents_tz"
down_revision = "0068_drop_metering_tables"
branch_labels = None
depends_on = None

# (tabla, columnas) a convertir.
_TARGETS = (
    ("hr_documents", ("created_at", "approved_at")),
    ("generated_uis", ("created_at", "updated_at")),
)


def _alter(to_tz: bool) -> None:
    tz = "WITH TIME ZONE" if to_tz else "WITHOUT TIME ZONE"
    for table, cols in _TARGETS:
        for col in cols:
            op.execute(
                f"ALTER TABLE IF EXISTS {table} "
                f"ALTER COLUMN {col} TYPE TIMESTAMP {tz} "
                f"USING {col} AT TIME ZONE 'UTC'"
            )


def upgrade() -> None:
    _alter(to_tz=True)


def downgrade() -> None:
    _alter(to_tz=False)
