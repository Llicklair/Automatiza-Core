"""Add tenant logo support and inject reports.create_pdf_report skill.

- Adds Tenant.logo_path (nullable string) so each tenant can upload
  a corporate logo that the PDF report renderer will draw on the cover.
- Backfills the agent_skills table: every AIEmployee that doesn't yet
  have the reports.create_pdf_report skill gets it. This keeps the
  skills catalog visible in the UI consistent with the runtime
  capability (the tool is wired into every built-in agent graph).

Revision ID: 0004_tenant_logo_pdf_skill
Revises: 0003_doc_embeddings_jsonb
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_tenant_logo_pdf_skill"
down_revision = "0003_doc_embeddings_jsonb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    tenant_columns = {c["name"] for c in inspector.get_columns("tenants")}
    if "logo_path" not in tenant_columns:
        op.add_column("tenants", sa.Column("logo_path", sa.String(length=500), nullable=True))

    bind.execute(
        sa.text(
            """
            INSERT INTO agent_skills (id, employee_id, tool_module)
            SELECT gen_random_uuid(), e.id, 'reports.create_pdf_report'
            FROM ai_employees e
            WHERE NOT EXISTS (
              SELECT 1 FROM agent_skills s
              WHERE s.employee_id = e.id
                AND s.tool_module = 'reports.create_pdf_report'
            )
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM agent_skills WHERE tool_module = 'reports.create_pdf_report'"))
    inspector = sa.inspect(bind)
    tenant_columns = {c["name"] for c in inspector.get_columns("tenants")}
    if "logo_path" in tenant_columns:
        op.drop_column("tenants", "logo_path")
