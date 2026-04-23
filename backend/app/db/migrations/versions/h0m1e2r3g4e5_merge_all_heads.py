"""merge_all_heads — unifica todas las ramas sueltas antes de generative_ui

Revision ID: h0m1e2r3g4e5
Revises: a0b1c2d3e4f5, a6bf183c8e0c, c3d4e5f6a7b8, f2a3b4c5d6e7
Create Date: 2026-04-08
"""

revision = "h0m1e2r3g4e5"
# Solo los 4 heads reales; a1b2c3d4e5f6, f3a4b5c6d7e8 y m3r6g2024odl son
# ancestors transitivos de a0b1c2d3e4f5 / c3d4e5f6a7b8 — incluirlos causaba
# un loop infinito en _topological_sort de alembic 1.14+
down_revision = (
    "a0b1c2d3e4f5",
    "a6bf183c8e0c",
    "c3d4e5f6a7b8",
    "f2a3b4c5d6e7",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
