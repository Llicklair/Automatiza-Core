"""Enable Row-Level Security on tenant-scoped tables.

Revision ID: 0003_enable_rls
Revises: 0002_accounting_fks

Tras esta migración:
- Toda tabla con columna tenant_id tiene RLS habilitada con FORCE.
- La policy tenant_isolation filtra/valida filas contra el GUC
  app.current_tenant (lo setea el listener SQLAlchemy desde el ContextVar).
- generated_uis y hr_documents adquieren la ForeignKey faltante a tenants.id
  (decisión Fase 1 opción B: agrupar con esta migración de RLS).

Excluido del filtrado RLS estándar:
- users / password_reset_tokens: durante el login no hay tenant en contexto
  porque precisamente lo estamos descubriendo. Las políticas se añadirán
  con un patrón distinto en una migración futura.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_enable_rls"
down_revision = "0002_accounting_fks"
branch_labels = None
depends_on = None


# Tablas con columna tenant_id que NO reciben las políticas RLS por defecto.
EXCLUDED_TABLES: set[str] = {"users", "password_reset_tokens"}


def _tenant_scoped_tables(conn) -> list[str]:
    """Devuelve nombres de tablas con columna tenant_id, excluyendo casos especiales."""
    rows = conn.execute(
        sa.text(
            """
            SELECT DISTINCT table_name FROM information_schema.columns
            WHERE column_name = 'tenant_id'
              AND table_schema = 'public'
            ORDER BY table_name
            """
        )
    )
    return [r[0] for r in rows if r[0] not in EXCLUDED_TABLES]


def upgrade() -> None:
    conn = op.get_bind()

    # ── Bloque A: FKs faltantes (Fase 1 opción B) ──────────────────────────
    for table in ("generated_uis", "hr_documents"):
        orphans = conn.execute(
            sa.text(
                f"""
                SELECT COUNT(*) FROM {table} g
                LEFT JOIN tenants t ON t.id = g.tenant_id
                WHERE t.id IS NULL
                """
            )
        ).scalar()
        if orphans:
            raise RuntimeError(
                f"{table} tiene {orphans} filas con tenant_id huérfano. "
                "Limpia antes de aplicar la migración."
            )

    op.create_foreign_key(
        "fk_generated_uis_tenant_id",
        "generated_uis",
        "tenants",
        ["tenant_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_hr_documents_tenant_id",
        "hr_documents",
        "tenants",
        ["tenant_id"],
        ["id"],
    )

    # ── Bloque B: RLS por tabla ────────────────────────────────────────────
    # NULLIF convierte el GUC vacío en NULL para que la comparación retorne
    # NULL (=falso) cuando no hay tenant en contexto, en lugar de fallar el
    # cast '' → uuid.
    policy_expr = (
        "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"
    )

    for table in _tenant_scoped_tables(conn):
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;')
        # Sin FORCE: el owner (rol que ejecuta migraciones) bypassa RLS
        # automáticamente y puede hacer DDL/DML administrativo.
        # La app conecta con un rol distinto sin BYPASSRLS, al que sí aplican
        # las políticas. system_context() puede usar SET row_security = off
        # porque no es el owner.
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON "{table}"
            USING ({policy_expr})
            WITH CHECK ({policy_expr});
            """
        )


def downgrade() -> None:
    conn = op.get_bind()

    for table in _tenant_scoped_tables(conn):
        op.execute(f'DROP POLICY IF EXISTS tenant_isolation ON "{table}";')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY;')

    op.drop_constraint("fk_hr_documents_tenant_id", "hr_documents", type_="foreignkey")
    op.drop_constraint("fk_generated_uis_tenant_id", "generated_uis", type_="foreignkey")
