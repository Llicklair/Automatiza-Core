"""Initial squashed migration - replaces all 44 original migrations

Revision ID: 0001_initial_squash
Revises: (none)
Create Date: 2026-04-23

This migration squashes all 44 original Alembic migrations into a single
initial migration for a clean baseline.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_squash"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- 6106ea8b058e_initial_schema ---
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("nif", sa.String(length=9), nullable=False),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenants_nif"), "tenants", ["nif"], unique=True)
    op.create_table(
        "tenant_integrations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("integration_type", sa.String(length=50), nullable=False),
        sa.Column("encrypted_credentials", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_integrations_tenant_id"), "tenant_integrations", ["tenant_id"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"], unique=False)
    op.create_table(
        "tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=False),
        sa.Column("user_intent", sa.Text(), nullable=True),
        sa.Column("plan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("current_step", sa.BigInteger(), nullable=True),
        sa.Column("agent_results", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("requires_human_approval", sa.Boolean(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasks_created_at"), "tasks", ["created_at"], unique=False)
    op.create_index(op.f("ix_tasks_domain"), "tasks", ["domain"], unique=False)
    op.create_index(op.f("ix_tasks_status"), "tasks", ["status"], unique=False)
    op.create_index(op.f("ix_tasks_tenant_id"), "tasks", ["tenant_id"], unique=False)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("input_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("output_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("llm_prompt", sa.Text(), nullable=True),
        sa.Column("llm_response", sa.Text(), nullable=True),
        sa.Column("validation_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_log_executed_at"), "audit_log", ["executed_at"], unique=False)
    op.create_index(op.f("ix_audit_log_task_id"), "audit_log", ["task_id"], unique=False)
    op.create_index(op.f("ix_audit_log_tenant_id"), "audit_log", ["tenant_id"], unique=False)
    op.create_table(
        "pending_approvals",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=False),
        sa.Column("action_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.UUID(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.Column("execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_pending_approvals_status"), "pending_approvals", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_pending_approvals_task_id"), "pending_approvals", ["task_id"], unique=False
    )
    op.create_index(
        op.f("ix_pending_approvals_tenant_id"), "pending_approvals", ["tenant_id"], unique=False
    )

    # --- 480048dde7b6_add_tenant_documents_table ---
    op.create_table(
        "tenant_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("uploaded_by", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("file_type", sa.String(length=100), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("parsed_content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
        ),
        sa.Column("locked_by", sa.UUID(), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tenant_documents_created_at"), "tenant_documents", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_tenant_documents_status"), "tenant_documents", ["status"], unique=False
    )
    op.create_index(
        op.f("ix_tenant_documents_task_id"), "tenant_documents", ["task_id"], unique=False
    )
    op.create_index(
        op.f("ix_tenant_documents_tenant_id"), "tenant_documents", ["tenant_id"], unique=False
    )

    # --- 856702bb2ab8_add_erp_models ---
    op.create_table(
        "clients",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("nif", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(length=255), nullable=True),
        sa.Column("postal_code", sa.String(length=50), nullable=True),
        sa.Column("client_type", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_clients_nif"), "clients", ["nif"], unique=False)
    op.create_index(op.f("ix_clients_tenant_id"), "clients", ["tenant_id"], unique=False)
    op.create_table(
        "employees",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("nif", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("base_salary", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("join_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contract_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("birth_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("numero_afiliacion_ss", sa.String(20), nullable=True),
        sa.Column("grupo_cotizacion", sa.String(2), nullable=True),
        sa.Column("tipo_contrato", sa.String(10), nullable=True),
        sa.Column("convenio_colectivo", sa.String(255), nullable=True),
        sa.Column("categoria_profesional", sa.String(100), nullable=True),
        sa.Column("jornada_tipo", sa.String(20), server_default="completa", nullable=True),
        sa.Column("jornada_horas_semana", sa.Numeric(4, 1), nullable=True),
        sa.Column("periodo_prueba_dias", sa.Integer(), nullable=True),
        sa.Column("bonificacion_tipo", sa.String(50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employees_nif"), "employees", ["nif"], unique=False)
    op.create_index(op.f("ix_employees_tenant_id"), "employees", ["tenant_id"], unique=False)
    op.create_table(
        "invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("invoice_number", sa.String(length=100), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount_base", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("amount_total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("invoice_type", sa.String(length=50), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_client_id"), "invoices", ["client_id"], unique=False)
    op.create_index(
        op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"], unique=False
    )
    op.create_index(op.f("ix_invoices_tenant_id"), "invoices", ["tenant_id"], unique=False)

    # --- 0406749c1f9a_add_workflows_tables ---
    op.create_table(
        "workflows",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("trigger_type", sa.String(length=50), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("action_type", sa.String(length=50), nullable=False),
        sa.Column("action_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.Column("ui_nodes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ui_edges", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "execution_mode",
            sa.String(length=20),
            nullable=False,
            server_default="reasoning",
        ),
        sa.Column(
            "compiled_steps",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflows_tenant_id"), "workflows", ["tenant_id"], unique=False)
    op.create_table(
        "workflow_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("trigger_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("result_log", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["task_id"],
            ["tasks.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
        ),
        sa.Column("node_states", postgresql.JSONB(), nullable=True, server_default="{}"),
        sa.Column("current_node_id", sa.String(100), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workflow_executions_tenant_id"), "workflow_executions", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_workflow_executions_workflow_id"),
        "workflow_executions",
        ["workflow_id"],
        unique=False,
    )

    # --- cf7da4c31523_add_quote_models ---
    op.create_table(
        "quotes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("quote_number", sa.String(length=100), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_base", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("amount_total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column("opportunity_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quotes_client_id"), "quotes", ["client_id"], unique=False)
    op.create_index(op.f("ix_quotes_quote_number"), "quotes", ["quote_number"], unique=False)
    op.create_index(op.f("ix_quotes_tenant_id"), "quotes", ["tenant_id"], unique=False)
    op.create_table(
        "quote_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("quote_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("tax_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("total_line", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- 363b80e64875_add_crm_expansion_models ---
    op.create_table(
        "events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=True),
        sa.Column("location_or_link", sa.String(length=255), nullable=True),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_events_tenant_id"), "events", ["tenant_id"], unique=False)
    op.create_table(
        "reservations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reservations_tenant_id"), "reservations", ["tenant_id"], unique=False)
    op.create_table(
        "activities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("opportunity_id", sa.UUID(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"],
            ["opportunities.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activities_client_id"), "activities", ["client_id"], unique=False)
    op.create_index(
        op.f("ix_activities_opportunity_id"), "activities", ["opportunity_id"], unique=False
    )
    op.create_index(op.f("ix_activities_tenant_id"), "activities", ["tenant_id"], unique=False)

    # --- bb642129ec99_add_start_date_to_projects_and_ ---
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("budget", sa.Numeric(10, 2), server_default="0"),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
    )
    op.create_index("ix_projects_tenant_id", "projects", ["tenant_id"])
    op.create_table(
        "project_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("project_id", sa.UUID(), nullable=True),
        sa.Column("assignee_id", sa.UUID(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), server_default="todo"),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["assignee_id"], ["users.id"]),
    )
    op.create_index("ix_project_tasks_tenant_id", "project_tasks", ["tenant_id"])
    op.create_index("ix_project_tasks_project_id", "project_tasks", ["project_id"])

    # --- ad8cd22d678b_add_domain_events_table ---
    op.create_table(
        "domain_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("event_name", sa.String(length=100), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_domain_events_created_at"), "domain_events", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_domain_events_event_name"), "domain_events", ["event_name"], unique=False
    )
    op.create_index(
        op.f("ix_domain_events_tenant_id"), "domain_events", ["tenant_id"], unique=False
    )
    op.create_table(
        "bank_transactions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("balance", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("invoice_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_bank_transactions_tenant_id"), "bank_transactions", ["tenant_id"], unique=False
    )

    # --- a79b087a3db7_add_tenant_knowledge_table ---
    op.create_table(
        "tenant_knowledge",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tenant_knowledge_key"), "tenant_knowledge", ["key"], unique=False)
    op.create_index(
        op.f("ix_tenant_knowledge_tenant_id"), "tenant_knowledge", ["tenant_id"], unique=False
    )

    # --- a3f7c9e2d1b4_add_node_engine_fields ---
    op.create_index("ix_pending_approvals_execution_id", "pending_approvals", ["execution_id"])

    # --- b1e3f8a2c9d0_add_fixed_assets_table ---
    op.create_table(
        "fixed_assets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("purchase_date", sa.Date(), nullable=False),
        sa.Column("purchase_value", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column(
            "useful_life_years",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="5",
        ),
        sa.Column(
            "residual_value", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0"
        ),
        sa.Column(
            "depreciation_method", sa.String(length=50), nullable=False, server_default="linear"
        ),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("account_code", sa.String(length=50), nullable=True),
        sa.Column("reference_invoice", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fixed_assets_tenant_id"), "fixed_assets", ["tenant_id"], unique=False)

    # --- journal_entries & journal_lines (accounting) ---
    op.create_table(
        "journal_entries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("reference_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_journal_entries_tenant_id"), "journal_entries", ["tenant_id"], unique=False
    )
    op.create_table(
        "journal_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("entry_id", sa.UUID(), nullable=False),
        sa.Column("account_code", sa.String(length=50), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=True),
        sa.Column("debit", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("credit", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["entry_id"], ["journal_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_journal_lines_tenant_id"), "journal_lines", ["tenant_id"], unique=False
    )
    op.create_index(op.f("ix_journal_lines_entry_id"), "journal_lines", ["entry_id"], unique=False)
    op.create_index(
        op.f("ix_journal_lines_account_code"), "journal_lines", ["account_code"], unique=False
    )

    # --- c2d4f6e8a0b2_add_stock_and_sales_orders ---
    op.create_table(
        "stock_movements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("movement_type", sa.String(50), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("stock_after", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reference", sa.String(255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_movements_tenant_id", "stock_movements", ["tenant_id"])
    op.create_index("ix_stock_movements_product_id", "stock_movements", ["product_id"])
    op.create_table(
        "sales_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_number", sa.String(100), nullable=True),
        sa.Column(
            "date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("expected_delivery", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("amount_base", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=True, server_default="0"),
        sa.Column("amount_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_orders_tenant_id", "sales_orders", ["tenant_id"])
    op.create_index("ix_sales_orders_client_id", "sales_orders", ["client_id"])
    op.create_index("ix_sales_orders_order_number", "sales_orders", ["order_number"])
    op.create_table(
        "sales_order_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("discount_percentage", sa.Numeric(5, 2), nullable=True, server_default="0"),
        sa.Column("tax_percentage", sa.Numeric(5, 2), nullable=True, server_default="21"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["order_id"], ["sales_orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_order_lines_order_id", "sales_order_lines", ["order_id"])

    # --- d4e6f8a2c0b4_add_purchase_orders_and_recurring_invoices ---
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_number", sa.String(100), nullable=True),
        sa.Column(
            "date", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column("expected_delivery", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("amount_base", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=True, server_default="0"),
        sa.Column("amount_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["supplier_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_orders_tenant_id", "purchase_orders", ["tenant_id"])
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_order_number", "purchase_orders", ["order_number"])
    op.create_table(
        "purchase_order_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tax_percentage", sa.Numeric(5, 2), nullable=True, server_default="21"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["order_id"], ["purchase_orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_purchase_order_lines_order_id", "purchase_order_lines", ["order_id"])
    op.create_table(
        "recurring_invoices",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("interval_type", sa.String(50), nullable=False, server_default="monthly"),
        sa.Column("next_run_date", sa.Date(), nullable=False),
        sa.Column("last_run_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("lines_json", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("terms", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recurring_invoices_tenant_id", "recurring_invoices", ["tenant_id"])
    op.create_index("ix_recurring_invoices_next_run_date", "recurring_invoices", ["next_run_date"])

    # --- f1a2b3c4d5e6_add_missing_indexes ---
    op.create_index(
        "ix_invoice_lines_product_id", "invoice_lines", ["product_id"], if_not_exists=True
    )
    op.create_index("ix_activities_client_id", "activities", ["client_id"], if_not_exists=True)
    op.create_index(
        "ix_activities_opportunity_id", "activities", ["opportunity_id"], if_not_exists=True
    )
    op.create_index(
        "ix_invoices_tenant_created", "invoices", ["tenant_id", "created_at"], if_not_exists=True
    )
    op.create_index(
        "ix_tasks_tenant_created", "tasks", ["tenant_id", "created_at"], if_not_exists=True
    )

    # --- e2f3a4b5c6d7_add_invoice_series_table ---
    op.create_table(
        "invoice_series",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("serie", sa.String(10), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prefix", sa.String(20), nullable=False, server_default="F"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "serie", "year", name="uq_invoice_series_tenant_serie_year"
        ),
    )
    op.create_index("ix_invoice_series_tenant_id", "invoice_series", ["tenant_id"])

    # --- f3a4b5c6d7e8_add_document_templates ---
    op.create_table(
        "document_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("template_type", sa.String(20), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("layout_style", sa.String(20), nullable=False, server_default="modern"),
        sa.Column("accent_color", sa.String(7), nullable=False, server_default="#6366f1"),
        sa.Column("font_family", sa.String(20), nullable=False, server_default="helvetica"),
        sa.Column("logo_position", sa.String(10), nullable=False, server_default="left"),
        sa.Column("header_style", sa.String(20), nullable=False, server_default="color_band"),
        sa.Column("table_style", sa.String(20), nullable=False, server_default="striped"),
        sa.Column("footer_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_templates_tenant_id", "document_templates", ["tenant_id"])
    op.create_index(
        "ix_document_templates_type", "document_templates", ["tenant_id", "template_type"]
    )

    # --- a1b2c3d4e5f6_add_albaranes ---
    op.create_table(
        "delivery_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("albaran_number", sa.String(50), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("amount_base", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("amount_total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_delivery_notes_tenant_id", "delivery_notes", ["tenant_id"])
    op.create_table(
        "delivery_note_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("albaran_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 3), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("tax_percentage", sa.Numeric(5, 2), nullable=False, server_default="21"),
        sa.Column("total", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["albaran_id"], ["delivery_notes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- 4ce2419ccd96_add_products_and_invoice_lines ---
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("item_type", sa.String(length=50), nullable=True),
        sa.Column("sku", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("tax_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.Column("stock_quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stock_min_alert", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_sku"), "products", ["sku"], unique=False)
    op.create_index(op.f("ix_products_tenant_id"), "products", ["tenant_id"], unique=False)
    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("invoice_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("discount_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("tax_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_invoice_lines_invoice_id"), "invoice_lines", ["invoice_id"], unique=False
    )

    # --- a0b1c2d3e4f5_add_opportunities_table ---
    op.create_table(
        "opportunities",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "expected_value", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0"
        ),
        sa.Column("stage", sa.String(length=50), nullable=False, server_default="new"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["clients.id"],
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_opportunities_tenant_id"), "opportunities", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_opportunities_client_id"), "opportunities", ["client_id"], unique=False
    )

    # --- c1d2e3f4a5b6_add_tenant_llm_config ---
    op.create_table(
        "tenant_llm_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("active_llm_provider", sa.String(50), nullable=False, server_default="gemini"),
        sa.Column(
            "active_embeddings_provider", sa.String(50), nullable=False, server_default="local"
        ),
        sa.Column("encrypted_keys", sa.Text()),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tenant_llm_configs_tenant_id", "tenant_llm_configs", ["tenant_id"])

    # --- a2b3c4d5e6f7_add_password_reset_tokens ---
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])

    # --- a6bf183c8e0c_add_category_to_tenantdocument ---
    op.create_index(
        op.f("ix_tenant_documents_category"), "tenant_documents", ["category"], unique=False
    )

    # --- e9f0a1b2c3d4_add_ai_employees_activity_feed ---
    op.create_table(
        "ai_employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(100), nullable=False),
        sa.Column("domain", sa.String(50), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("budget_limit_usd", sa.Numeric(10, 2), nullable=True, server_default="10.00"),
        sa.Column("status", sa.String(20), nullable=False, server_default="idle"),
        sa.Column("is_builtin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.Column("doc_folder", sa.String(200), nullable=True),
        sa.Column("icon", sa.String(10), nullable=True),
        sa.Column("avatar_color", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_employees_tenant_id", "ai_employees", ["tenant_id"])
    op.create_table(
        "agent_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tool_module", sa.String(255), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["ai_employees.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_skills_employee_id", "agent_skills", ["employee_id"])
    op.create_table(
        "token_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["ai_employees.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_token_ledger_tenant_id", "token_ledger", ["tenant_id"])
    op.create_index("ix_token_ledger_employee_id", "token_ledger", ["employee_id"])
    op.create_index("ix_token_ledger_created_at", "token_ledger", ["created_at"])
    op.create_table(
        "activity_feed",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("icon", sa.String(10), nullable=False, server_default="📋"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["ai_employees.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_feed_tenant_id", "activity_feed", ["tenant_id"])
    op.create_index("ix_activity_feed_employee_id", "activity_feed", ["employee_id"])
    op.create_index("ix_activity_feed_created_at", "activity_feed", ["created_at"])

    # --- f2a3b4c5d6e7_add_recruitment_tables ---
    op.create_table(
        "recruitment_positions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("department", sa.String(100)),
        sa.Column("description", sa.Text()),
        sa.Column("required_skills", postgresql.JSONB, server_default="[]"),
        sa.Column("experience_min_years", sa.Numeric(4, 1), server_default="0"),
        sa.Column("salary_range_min", sa.Numeric(10, 2)),
        sa.Column("salary_range_max", sa.Numeric(10, 2)),
        sa.Column("status", sa.String(50), server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "candidates",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "position_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recruitment_positions.id"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("phone", sa.String(50)),
        sa.Column("skills", postgresql.JSONB, server_default="[]"),
        sa.Column("experience_years", sa.Numeric(4, 1)),
        sa.Column("languages", postgresql.JSONB, server_default="[]"),
        sa.Column("education", sa.Text()),
        sa.Column("summary", sa.Text()),
        sa.Column("raw_cv_text", sa.Text()),
        sa.Column("cv_file_path", sa.String(500)),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("score_breakdown", postgresql.JSONB),
        sa.Column("status", sa.String(50), server_default="new"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- g1e2n3e4r5a6_add_generated_uis_table ---
    op.create_table(
        "generated_uis",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("metadata_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_generated_uis_tenant_id", "generated_uis", ["tenant_id"])

    # --- c4d5e6f7a8b9_create_hr_documents ---
    op.create_table(
        "hr_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True)),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("employee_name", sa.String(200), nullable=True),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # --- d1e2f3a4b5c6_add_hr_ss_fields_and_settlements ---
    op.create_table(
        "settlements",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("otros_conceptos_json", postgresql.JSONB(), nullable=True),
        sa.Column("total_percepciones", sa.Numeric(10, 2), nullable=False),
        sa.Column("deduccion_ss", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("deduccion_irpf", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("total_deducciones", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("total_liquido", sa.Numeric(10, 2), nullable=False),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_settlements_tenant_id", "settlements", ["tenant_id"])
    op.create_index("ix_settlements_employee_id", "settlements", ["employee_id"])
    op.create_table(
        "jornada_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fecha", sa.Date, nullable=False),
        sa.Column("hora_entrada", sa.String(5), nullable=True),
        sa.Column("hora_salida", sa.String(5), nullable=True),
        sa.Column("horas_ordinarias", sa.Numeric(4, 2), server_default="0", nullable=True),
        sa.Column("horas_extra", sa.Numeric(4, 2), server_default="0", nullable=True),
        sa.Column("horas_extra_voluntarias", sa.Numeric(4, 2), server_default="0", nullable=True),
        sa.Column("notas", sa.String(255), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jornada_records_employee_id", "jornada_records", ["employee_id"])
    op.create_index(
        "ix_jornada_records_year_month", "jornada_records", ["employee_id", "year", "month"]
    )

    # --- document_embeddings (TEXT fallback for embedding, pgvector not required) ---
    op.create_table(
        "document_embeddings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("chunk_index", sa.String(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("element_type", sa.String(), nullable=True),
        sa.Column("bounding_box", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_document_embeddings_document_id"),
        "document_embeddings",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_embeddings_tenant_id"), "document_embeddings", ["tenant_id"], unique=False
    )

    # --- payrolls (from model, not in original migrations) ---
    op.create_table(
        "payrolls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("employee_id", sa.UUID(), nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("issue_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("base_salary", sa.Numeric(10, 2), nullable=False),
        sa.Column("gross_salary", sa.Numeric(10, 2), nullable=True),
        sa.Column("devengos_json", postgresql.JSONB(), nullable=True),
        sa.Column("base_cotizacion_cc", sa.Numeric(10, 2), nullable=True),
        sa.Column("base_irpf", sa.Numeric(10, 2), nullable=True),
        sa.Column("pct_cc", sa.Numeric(5, 2), server_default="4.70", nullable=True),
        sa.Column("pct_desempleo", sa.Numeric(5, 2), server_default="1.55", nullable=True),
        sa.Column("pct_fp", sa.Numeric(5, 2), server_default="0.10", nullable=True),
        sa.Column("pct_mei", sa.Numeric(5, 2), server_default="0.10", nullable=True),
        sa.Column("ss_contingencias_comunes", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("ss_desempleo", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("ss_formacion_profesional", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("ss_mei", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("irpf", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("pct_irpf", sa.Numeric(5, 2), server_default="15.00", nullable=True),
        sa.Column("anticipos", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("other_deductions", sa.Numeric(10, 2), server_default="0", nullable=True),
        sa.Column("deductions", sa.Numeric(10, 2), nullable=True),
        sa.Column("cuotas_empresa_json", postgresql.JSONB(), nullable=True),
        sa.Column("net_salary", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(50), server_default="draft", nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payrolls_tenant_id"), "payrolls", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_payrolls_employee_id"), "payrolls", ["employee_id"], unique=False)


def downgrade() -> None:
    op.drop_table("payrolls")
    op.drop_table("document_embeddings")
    op.drop_table("jornada_records")
    op.drop_table("settlements")
    op.drop_table("hr_documents")
    op.drop_table("generated_uis")
    op.drop_table("candidates")
    op.drop_table("recruitment_positions")
    op.drop_table("activity_feed")
    op.drop_table("token_ledger")
    op.drop_table("agent_skills")
    op.drop_table("ai_employees")
    op.drop_table("password_reset_tokens")
    op.drop_table("tenant_llm_configs")
    op.drop_table("opportunities")
    op.drop_table("invoice_lines")
    op.drop_table("products")
    op.drop_table("delivery_note_lines")
    op.drop_table("delivery_notes")
    op.drop_table("document_templates")
    op.drop_table("invoice_series")
    op.drop_table("recurring_invoices")
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
    op.drop_table("sales_order_lines")
    op.drop_table("sales_orders")
    op.drop_table("stock_movements")
    op.drop_table("fixed_assets")
    op.drop_table("journal_lines")
    op.drop_table("journal_entries")
    op.drop_table("tenant_knowledge")
    op.drop_table("bank_transactions")
    op.drop_table("domain_events")
    op.drop_table("project_tasks")
    op.drop_table("projects")
    op.drop_table("activities")
    op.drop_table("reservations")
    op.drop_table("events")
    op.drop_table("quote_lines")
    op.drop_table("quotes")
    op.drop_table("workflow_executions")
    op.drop_table("workflows")
    op.drop_table("invoices")
    op.drop_table("employees")
    op.drop_table("clients")
    op.drop_table("tenant_documents")
    op.drop_table("pending_approvals")
    op.drop_table("audit_log")
    op.drop_table("tasks")
    op.drop_table("users")
    op.drop_table("tenant_integrations")
    op.drop_table("tenants")
