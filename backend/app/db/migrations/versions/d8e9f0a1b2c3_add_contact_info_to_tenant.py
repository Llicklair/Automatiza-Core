"""Add contact info to tenant

Revision ID: d8e9f0a1b2c3
Revises: a7b8c9d0e1f2
Create Date: 2026-03-13 14:39:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d8e9f0a1b2c3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("tenants", sa.Column("address", sa.String(length=500), nullable=True))
    op.add_column("tenants", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("tenants", sa.Column("contact_email", sa.String(length=255), nullable=True))


def downgrade():
    op.drop_column("tenants", "contact_email")
    op.drop_column("tenants", "phone")
    op.drop_column("tenants", "address")
