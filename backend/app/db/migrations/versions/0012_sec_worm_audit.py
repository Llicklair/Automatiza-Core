"""SEC.WORM — append-only enforced para audit_log y agent_execution_trace.

Crea la tabla `agent_execution_trace` y añade triggers PL/pgSQL que rechazan
UPDATE y DELETE en ambas tablas (cumplimiento AI Act Art. 12 + RD 1007/2023).

En SQLite (tests) los triggers no se crean — la inmutabilidad solo está
enforced en producción Postgres. El patrón es consistente con la migración
`0011_verifactu_chain.py`.

Revision ID: 0012_sec_worm_audit
Revises: 0011_verifactu_chain
"""

from alembic import op

revision = "0012_sec_worm_audit"
down_revision = "0011_verifactu_chain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabla agent_execution_trace
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_execution_trace (
            id BIGSERIAL PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            execution_id UUID,
            task_id UUID REFERENCES tasks(id),
            agent_name VARCHAR(100) NOT NULL,
            llm_provider VARCHAR(50),
            llm_model VARCHAR(100),
            prompt_hash VARCHAR(64),
            prompt_version VARCHAR(100),
            tool_calls_json JSONB,
            output_hash VARCHAR(64),
            tokens_in INT,
            tokens_out INT,
            cost_eur NUMERIC(10, 4),
            duration_ms INT,
            status VARCHAR(30) NOT NULL DEFAULT 'ok',
            error_class VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_exec_trace_tenant_created "
        "ON agent_execution_trace(tenant_id, created_at)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_exec_trace_execution " "ON agent_execution_trace(execution_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_exec_trace_task " "ON agent_execution_trace(task_id)")

    # Triggers append-only (solo Postgres)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Función reutilizable (puede haberla creado ya 0011_verifactu_chain;
        # CREATE OR REPLACE es idempotente).
        op.execute(
            """
            CREATE OR REPLACE FUNCTION sec_worm_reject_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'Append-only table: % is immutable (SEC.WORM)', TG_TABLE_NAME;
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        for tname in ("audit_log", "agent_execution_trace"):
            op.execute(f"DROP TRIGGER IF EXISTS {tname}_no_update ON {tname}")
            op.execute(
                f"""
                CREATE TRIGGER {tname}_no_update
                BEFORE UPDATE ON {tname}
                FOR EACH ROW EXECUTE FUNCTION sec_worm_reject_mutation();
                """
            )
            op.execute(f"DROP TRIGGER IF EXISTS {tname}_no_delete ON {tname}")
            op.execute(
                f"""
                CREATE TRIGGER {tname}_no_delete
                BEFORE DELETE ON {tname}
                FOR EACH ROW EXECUTE FUNCTION sec_worm_reject_mutation();
                """
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for tname in ("audit_log", "agent_execution_trace"):
            op.execute(f"DROP TRIGGER IF EXISTS {tname}_no_update ON {tname}")
            op.execute(f"DROP TRIGGER IF EXISTS {tname}_no_delete ON {tname}")
        # No dropear la función `sec_worm_reject_mutation` — la puede usar
        # `verifactu_chain` (0011); su downgrade la elimina si procede.
    op.execute("DROP INDEX IF EXISTS ix_agent_exec_trace_task")
    op.execute("DROP INDEX IF EXISTS ix_agent_exec_trace_execution")
    op.execute("DROP INDEX IF EXISTS ix_agent_exec_trace_tenant_created")
    op.execute("DROP TABLE IF EXISTS agent_execution_trace")
