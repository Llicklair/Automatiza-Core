"""Add recruitment tables: recruitment_positions, candidates

Revision ID: f2a3b4c5d6e7
Revises: e9f0a1b2c3d4
Create Date: 2026-04-02

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = 'f2a3b4c5d6e7'
down_revision = 'e9f0a1b2c3d4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'recruitment_positions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('department', sa.String(100)),
        sa.Column('description', sa.Text),
        sa.Column('required_skills', postgresql.JSONB, server_default='[]'),
        sa.Column('experience_min_years', sa.Numeric(4, 1), server_default='0'),
        sa.Column('salary_range_min', sa.Numeric(10, 2)),
        sa.Column('salary_range_max', sa.Numeric(10, 2)),
        sa.Column('status', sa.String(50), server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )

    op.create_table(
        'candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tenants.id'), nullable=False, index=True),
        sa.Column('position_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('recruitment_positions.id'), index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255)),
        sa.Column('phone', sa.String(50)),
        sa.Column('skills', postgresql.JSONB, server_default='[]'),
        sa.Column('experience_years', sa.Numeric(4, 1)),
        sa.Column('languages', postgresql.JSONB, server_default='[]'),
        sa.Column('education', sa.Text),
        sa.Column('summary', sa.Text),
        sa.Column('raw_cv_text', sa.Text),
        sa.Column('cv_file_path', sa.String(500)),
        sa.Column('score', sa.Numeric(5, 2)),
        sa.Column('score_breakdown', postgresql.JSONB),
        sa.Column('status', sa.String(50), server_default='new'),
        sa.Column('notes', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('candidates')
    op.drop_table('recruitment_positions')
