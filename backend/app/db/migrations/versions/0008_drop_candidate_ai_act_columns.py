"""Drop Candidate.score and Candidate.score_breakdown (AI Act compliance).

Retira las columnas de scoring/profiling de candidatos para cumplir con el
Reglamento UE 2024/1689 (AI Act), Anexo III punto 4 — sistemas destinados a
evaluar candidatos en procesos de empleo se consideran high-risk.

La decisión consensuada (Escenario A, decisión humana 10) es retirar el
scoring automático en MVP. La reintroducción en v1.2 requiere full compliance
(QMS, evaluación de conformidad, marcado CE, registro UE) y se hará con su
propia migración.

El código que invocaba `score_candidate()` ha sido retirado previamente
(AI.SCO en backlog). Esta migración cierra la defensa Art. 6(3) eliminando
también el schema, no solo la invocación.

Ver `docs/ai_act_scoping.md` para el contexto completo.

Revision ID: 0008_drop_candidate_ai_act
Revises: 0007_payroll_unique
"""

from alembic import op

revision = "0008_drop_candidate_ai_act"
down_revision = "0007_payroll_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE candidates DROP COLUMN IF EXISTS score")
    op.execute("ALTER TABLE candidates DROP COLUMN IF EXISTS score_breakdown")


def downgrade() -> None:
    # Reintroducción defensiva: la reactivación real en v1.2 debe pasar por
    # compliance Anexo III completo, no por un simple downgrade.
    op.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS score NUMERIC(5, 2)")
    op.execute("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS score_breakdown JSONB")
