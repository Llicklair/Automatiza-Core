"""Create user_invitations table (move from _ensure_schema to Alembic).

La tabla `user_invitations` y sus tres índices se creaban en runtime mediante
`_ensure_schema()` en `app/main.py`. Esta migración consolida esa creación en
Alembic para que el esquema completo viva en migraciones (ALB.4).

Idempotente: `CREATE TABLE IF NOT EXISTS` y `CREATE INDEX IF NOT EXISTS` para
soportar BDs de testers que ya tienen la tabla creada por `_ensure_schema()`.

Revision ID: 0009_user_invitations
Revises: 0008_drop_candidate_ai_act
"""

from alembic import op

revision = "0009_user_invitations"
down_revision = "0008_drop_candidate_ai_act"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_invitations (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'employee',
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            used_at TIMESTAMP WITH TIME ZONE,
            used_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_invitations_tenant_id ON user_invitations(tenant_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_invitations_email ON user_invitations(email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_invitations_token_hash ON user_invitations(token_hash)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_invitations_token_hash")
    op.execute("DROP INDEX IF EXISTS ix_user_invitations_email")
    op.execute("DROP INDEX IF EXISTS ix_user_invitations_tenant_id")
    op.execute("DROP TABLE IF EXISTS user_invitations")
