"""POS.SESSIONS — TPV: sesiones de venta y líneas de carrito.

Crea las tablas `pos_sessions` y `pos_session_lines` con el constraint
clave: índice único parcial que garantiza una sola sesión en estado
'open' por (tenant_id, user_id). Esto permite distinguir "la sesión
actual del cajero" sin estado adicional.

La integridad de status la garantiza un CHECK constraint para evitar
valores fuera de open|closed|cancelled.

RLS se aplica automáticamente en la siguiente migración que detecte
nuevas tablas con tenant_id (mecanismo dinámico de 0016_sec_rls); de
momento aplicamos RLS explícita en esta migración para no esperar.

Revision ID: 0025_pos_sessions
Revises: 0024_inventory_extensions
"""

from alembic import op


revision = "0025_pos_sessions"
down_revision = "0024_inventory_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            status VARCHAR(20) NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'closed', 'cancelled')),
            payment_method VARCHAR(20)
                CHECK (payment_method IS NULL OR payment_method IN ('cash', 'card')),
            amount_subtotal NUMERIC(10, 2) NOT NULL DEFAULT 0,
            tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
            amount_total NUMERIC(10, 2) NOT NULL DEFAULT 0,
            notes TEXT,
            opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            closed_at TIMESTAMP WITH TIME ZONE
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pos_sessions_tenant_id ON pos_sessions(tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pos_sessions_user_id ON pos_sessions(user_id)"
    )
    # Único parcial: solo UNA sesión 'open' por (tenant, user). closed/cancelled
    # pueden acumularse libremente.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_pos_sessions_one_open_per_user
            ON pos_sessions(tenant_id, user_id)
            WHERE status = 'open'
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pos_session_lines (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL
                REFERENCES pos_sessions(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            product_id UUID REFERENCES products(id),
            description VARCHAR(500) NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
            unit_price NUMERIC(10, 2) NOT NULL DEFAULT 0,
            tax_percentage NUMERIC(5, 2) NOT NULL DEFAULT 21,
            total NUMERIC(10, 2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pos_session_lines_session_id "
        "ON pos_session_lines(session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_pos_session_lines_tenant_id "
        "ON pos_session_lines(tenant_id)"
    )

    # RLS para ambas tablas (Postgres-only).
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("pos_sessions", "pos_session_lines"):
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
            op.execute(f"DROP POLICY IF EXISTS rls_tenant_isolation ON {table}")
            op.execute(
                f"""
                CREATE POLICY rls_tenant_isolation ON {table}
                    USING (
                        tenant_id::text = current_setting('app.current_tenant', true)
                        OR current_setting('app.current_tenant', true) IS NULL
                        OR current_setting('app.current_tenant', true) = ''
                    )
                    WITH CHECK (
                        tenant_id::text = current_setting('app.current_tenant', true)
                    )
                """
            )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pos_session_lines CASCADE")
    op.execute("DROP TABLE IF EXISTS pos_sessions CASCADE")
