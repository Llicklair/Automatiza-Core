"""Add SS fields to employees/payrolls, create settlements and jornada_records tables

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-04-09

Campos añadidos según estructura real de nóminas y contratos españoles:
- employees: NAF, grupo cotización, tipo contrato, jornada, convenio, bonificacion_tipo
- payrolls: gross_salary, bases de cotización, porcentajes SS, devengos_json, cuotas_empresa_json
- settlements: finiquitos (vacaciones, prorrata, indemnización)
- jornada_records: registro diario de jornada obligatorio (Art. 34.9 ET)
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "d1e2f3a4b5c6"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── employees: campos laborales y SS ──────────────────────────────────────
    op.add_column("employees", sa.Column("phone", sa.String(50), nullable=True))
    op.add_column("employees", sa.Column("birth_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("employees", sa.Column("numero_afiliacion_ss", sa.String(20), nullable=True))
    op.add_column("employees", sa.Column("grupo_cotizacion", sa.String(2), nullable=True))
    op.add_column("employees", sa.Column("tipo_contrato", sa.String(10), nullable=True))
    op.add_column("employees", sa.Column("convenio_colectivo", sa.String(255), nullable=True))
    op.add_column("employees", sa.Column("categoria_profesional", sa.String(100), nullable=True))
    op.add_column(
        "employees",
        sa.Column("jornada_tipo", sa.String(20), server_default="completa", nullable=True),
    )
    op.add_column("employees", sa.Column("jornada_horas_semana", sa.Numeric(4, 1), nullable=True))
    op.add_column("employees", sa.Column("periodo_prueba_dias", sa.Integer, nullable=True))
    op.add_column("employees", sa.Column("bonificacion_tipo", sa.String(50), nullable=True))

    # ── payrolls: devengos, bases, porcentajes, cuotas empresa ───────────────
    op.add_column("payrolls", sa.Column("gross_salary", sa.Numeric(10, 2), nullable=True))
    op.add_column("payrolls", sa.Column("devengos_json", JSONB, nullable=True))
    op.add_column("payrolls", sa.Column("base_cotizacion_cc", sa.Numeric(10, 2), nullable=True))
    op.add_column("payrolls", sa.Column("base_irpf", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "payrolls", sa.Column("pct_cc", sa.Numeric(5, 2), server_default="4.70", nullable=True)
    )
    op.add_column(
        "payrolls",
        sa.Column("pct_desempleo", sa.Numeric(5, 2), server_default="1.55", nullable=True),
    )
    op.add_column(
        "payrolls", sa.Column("pct_fp", sa.Numeric(5, 2), server_default="0.10", nullable=True)
    )
    op.add_column(
        "payrolls", sa.Column("pct_mei", sa.Numeric(5, 2), server_default="0.10", nullable=True)
    )
    op.add_column(
        "payrolls", sa.Column("pct_irpf", sa.Numeric(5, 2), server_default="15.00", nullable=True)
    )
    op.add_column(
        "payrolls", sa.Column("anticipos", sa.Numeric(10, 2), server_default="0", nullable=True)
    )
    op.add_column("payrolls", sa.Column("cuotas_empresa_json", JSONB, nullable=True))

    # ── settlements: finiquitos ───────────────────────────────────────────────
    op.create_table(
        "settlements",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("fecha_extincion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("causa_extincion", sa.String(50), nullable=False),
        sa.Column(
            "vacaciones_pendientes_dias", sa.Numeric(5, 1), server_default="0", nullable=True
        ),
        sa.Column(
            "vacaciones_pendientes_importe", sa.Numeric(10, 2), server_default="0", nullable=True
        ),
        sa.Column("prorrata_paga_extra", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("prorrata_aguinaldo", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("indemnizacion", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("otros_conceptos_json", JSONB, nullable=True),
        sa.Column("total_percepciones", sa.Numeric(10, 2), nullable=False),
        sa.Column("deduccion_ss", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("deduccion_irpf", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("total_deducciones", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("total_liquido", sa.Numeric(10, 2), nullable=False),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
    )
    op.create_index("ix_settlements_tenant_id", "settlements", ["tenant_id"])
    op.create_index("ix_settlements_employee_id", "settlements", ["employee_id"])

    # ── jornada_records: registro diario de jornada (Art. 34.9 ET) ───────────
    op.create_table(
        "jornada_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("hora_entrada", sa.String(5), nullable=True),
        sa.Column("hora_salida", sa.String(5), nullable=True),
        sa.Column("horas_ordinarias", sa.Numeric(4, 2), server_default="0", nullable=True),
        sa.Column("horas_extra", sa.Numeric(4, 2), server_default="0", nullable=True),
        sa.Column("horas_extra_voluntarias", sa.Numeric(4, 2), server_default="0", nullable=True),
        sa.Column("notas", sa.String(255), nullable=True),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("month", sa.Integer, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
    )
    op.create_index("ix_jornada_records_employee_id", "jornada_records", ["employee_id"])
    op.create_index(
        "ix_jornada_records_year_month", "jornada_records", ["employee_id", "year", "month"]
    )


def downgrade() -> None:
    op.drop_index("ix_settlements_employee_id", table_name="settlements")
    op.drop_index("ix_settlements_tenant_id", table_name="settlements")
    op.drop_table("settlements")

    for col in [
        "cuotas_empresa_json",
        "anticipos",
        "pct_irpf",
        "pct_mei",
        "pct_fp",
        "pct_desempleo",
        "pct_cc",
        "base_irpf",
        "base_cotizacion_cc",
        "devengos_json",
        "gross_salary",
    ]:
        op.drop_column("payrolls", col)

    op.drop_index("ix_jornada_records_year_month", table_name="jornada_records")
    op.drop_index("ix_jornada_records_employee_id", table_name="jornada_records")
    op.drop_table("jornada_records")

    for col in [
        "bonificacion_tipo",
        "periodo_prueba_dias",
        "jornada_horas_semana",
        "jornada_tipo",
        "categoria_profesional",
        "convenio_colectivo",
        "tipo_contrato",
        "grupo_cotizacion",
        "numero_afiliacion_ss",
        "birth_date",
        "phone",
    ]:
        op.drop_column("employees", col)
