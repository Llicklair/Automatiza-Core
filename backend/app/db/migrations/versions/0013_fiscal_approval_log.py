"""SEC.APR — Crea fiscal_approval_log append-only para actos fiscales AEAT.

Ningún modelo AEAT (303/130/347/390/111/190) puede presentarse sin un
registro firmado en esta tabla por la persona autorizada. Append-only
enforced en Postgres mediante triggers PL/pgSQL.

Revision ID: 0013_fiscal_approval_log
Revises: 0012_sec_worm_audit
"""

from alembic import op

revision = "0013_fiscal_approval_log"
down_revision = "0012_sec_worm_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fiscal_approval_log (
            id BIGSERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            user_id UUID NOT NULL REFERENCES users(id),
            pending_approval_id UUID REFERENCES pending_approvals(id),
            model_aeat VARCHAR(10) NOT NULL,
            period_quarter INT,
            period_year INT NOT NULL,
            payload_hash VARCHAR(64) NOT NULL,
            pdf_path VARCHAR(500),
            approval_text TEXT NOT NULL,
            decision VARCHAR(20) NOT NULL,
            rejection_reason TEXT,
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fiscal_appr_tenant_created " "ON fiscal_approval_log(tenant_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_fiscal_appr_model_period "
        "ON fiscal_approval_log(tenant_id, model_aeat, period_year, period_quarter)"
    )

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Reutiliza la función creada en 0012.
        op.execute("DROP TRIGGER IF EXISTS fiscal_approval_log_no_update ON fiscal_approval_log")
        op.execute(
            """
            CREATE TRIGGER fiscal_approval_log_no_update
            BEFORE UPDATE ON fiscal_approval_log
            FOR EACH ROW EXECUTE FUNCTION sec_worm_reject_mutation();
            """
        )
        op.execute("DROP TRIGGER IF EXISTS fiscal_approval_log_no_delete ON fiscal_approval_log")
        op.execute(
            """
            CREATE TRIGGER fiscal_approval_log_no_delete
            BEFORE DELETE ON fiscal_approval_log
            FOR EACH ROW EXECUTE FUNCTION sec_worm_reject_mutation();
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS fiscal_approval_log_no_update ON fiscal_approval_log")
        op.execute("DROP TRIGGER IF EXISTS fiscal_approval_log_no_delete ON fiscal_approval_log")
    op.execute("DROP INDEX IF EXISTS ix_fiscal_appr_model_period")
    op.execute("DROP INDEX IF EXISTS ix_fiscal_appr_tenant_created")
    op.execute("DROP TABLE IF EXISTS fiscal_approval_log")
