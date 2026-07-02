"""Backfill the reports.create_pdf_text_report skill for every AIEmployee.

Pair migration to 0004: keeps the agent_skills catalog in sync with the
runtime tool registry. Without this row, the dynamic agent compiler
silently drops the skill and the LLM never sees the markdown PDF tool.

Revision ID: 0005_pdf_text_report_skill
Revises: 0004_tenant_logo_pdf_skill
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_pdf_text_report_skill"
down_revision = "0004_tenant_logo_pdf_skill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO agent_skills (id, employee_id, tool_module)
            SELECT gen_random_uuid(), e.id, 'reports.create_pdf_text_report'
            FROM ai_employees e
            WHERE NOT EXISTS (
              SELECT 1 FROM agent_skills s
              WHERE s.employee_id = e.id
                AND s.tool_module = 'reports.create_pdf_text_report'
            )
            """
        )
    )


def downgrade() -> None:
    op.get_bind().execute(sa.text("DELETE FROM agent_skills WHERE tool_module = 'reports.create_pdf_text_report'"))
