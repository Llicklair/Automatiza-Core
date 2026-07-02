"""Create notifications — bandeja persistente cross-session (UI.NOT).

Las notificaciones existentes vivían solo en memoria del store frontend.
UI.NOT añade persistencia BD para que el usuario las recupere tras
cerrar/abrir la app.

`kind` clasifica para iconografía y filtro: info | success | warning | error.
`payload` JSONB para evolución futura del esquema sin migración (link,
context, actor, etc.). `read_at` NULL = pendiente, timestamp = leída.

Revision ID: 0022_notifications
Revises: 0021_tenant_onboarding
"""

from alembic import op

revision = "0022_notifications"
down_revision = "0021_tenant_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    payload_type = "JSONB" if bind.dialect.name == "postgresql" else "TEXT"

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS notifications (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL,
            user_id UUID,
            kind VARCHAR(32) NOT NULL DEFAULT 'info',
            title VARCHAR(200) NOT NULL,
            body TEXT,
            payload {payload_type},
            read_at TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_tenant_created " "ON notifications(tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notifications_unread "
        "ON notifications(tenant_id, read_at) " + ("WHERE read_at IS NULL" if bind.dialect.name == "postgresql" else "")
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notifications_unread")
    op.execute("DROP INDEX IF EXISTS ix_notifications_tenant_created")
    op.execute("DROP TABLE IF EXISTS notifications")
