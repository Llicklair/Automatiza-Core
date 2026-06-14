"""Paso BYOK en el wizard de onboarding — tenant_onboarding.step_llm_config.

Añade el paso "configura tu clave de IA" (BYOK) al wizard de onboarding. Existente
= False (los tenants ya creados aún no lo han marcado; se auto-sincroniza desde su
readiness real en la primera lectura del wizard).
"""

import sqlalchemy as sa
from alembic import op

revision = "0059_onboarding_llm_step"
down_revision = "0058_hr_document_number"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tenant_onboarding",
        sa.Column(
            "step_llm_config",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenant_onboarding", "step_llm_config")
