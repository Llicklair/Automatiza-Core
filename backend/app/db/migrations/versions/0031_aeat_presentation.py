"""Custodia de certificado digital del cliente + registro de presentaciones AEAT.

Habilita la Fase C del roadmap fiscal: presentación electrónica real a la
SEDE AEAT con firma XAdES. El certificado se almacena cifrado (Fernet con
TENANT_ENCRYPTION_KEY) y nunca se devuelve por la API.

Tablas:
  - tenant_certificates: un certificado activo por tenant (puede haber más
    históricos en estado revoked). Solo se usa para firma de modelos AEAT.
  - aeat_presentations: registro auditado de cada intento de presentación
    (modelo, periodo, status, CSV justificante, errores).

Revision ID: 0031_aeat_presentation
Revises: 0030_accounting_periods
"""

from alembic import op

revision = "0031_aeat_presentation"
down_revision = "0030_accounting_periods"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tenant_certificates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            label VARCHAR(120) NOT NULL,
            subject_cn VARCHAR(255),
            issuer_cn VARCHAR(255),
            valid_from TIMESTAMP WITH TIME ZONE,
            valid_until TIMESTAMP WITH TIME ZONE,
            serial_number VARCHAR(80),
            sha256_fingerprint VARCHAR(80),
            encrypted_pfx BYTEA NOT NULL,        -- contenido .pfx/.p12 cifrado con Fernet
            encrypted_password TEXT NOT NULL,    -- contraseña del PFX cifrada
            status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active | revoked
            uploaded_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMP WITH TIME ZONE,
            notes VARCHAR(500)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_tenant_certificates_tenant_id ON tenant_certificates(tenant_id)")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_tenant_certificates_active
        ON tenant_certificates(tenant_id) WHERE status = 'active'
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS aeat_presentations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            model_code VARCHAR(10) NOT NULL,            -- '303' | '130' | '111' | '347' | ...
            year INTEGER NOT NULL,
            period VARCHAR(10) NOT NULL,                 -- '1T' | '2T' | '01' | 'A'
            environment VARCHAR(20) NOT NULL DEFAULT 'preproduccion', -- preproduccion | produccion
            status VARCHAR(30) NOT NULL DEFAULT 'pending',
                -- pending | signed | submitted | accepted | rejected | error
            xml_unsigned TEXT,
            xml_signed TEXT,
            response_raw TEXT,
            csv_justificante VARCHAR(80),
            error_code VARCHAR(40),
            error_message TEXT,
            submitted_at TIMESTAMP WITH TIME ZONE,
            accepted_at TIMESTAMP WITH TIME ZONE,
            created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_aeat_presentations_tenant_id ON aeat_presentations(tenant_id)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_aeat_presentations_lookup
        ON aeat_presentations(tenant_id, model_code, year, period)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS aeat_presentations CASCADE")
    op.execute("DROP TABLE IF EXISTS tenant_certificates CASCADE")
