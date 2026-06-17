"""Marketing BYO: retira las columnas de token OAuth de social_accounts.

En el modelo BYO (Zernio) las cuentas sociales no guardan tokens OAuth — la
publicación usa la API key del tenant (`marketing_provider_config`). Estas
columnas quedaron inertes tras la migración a Zernio; se retiran.

Revision ID: 0063_drop_social_account_tokens
Revises: 0062_marketing_provider_config
"""

from alembic import op

revision = "0063_drop_social_account_tokens"
down_revision = "0062_marketing_provider_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE social_accounts DROP COLUMN IF EXISTS access_token")
    op.execute("ALTER TABLE social_accounts DROP COLUMN IF EXISTS refresh_token")
    op.execute("ALTER TABLE social_accounts DROP COLUMN IF EXISTS token_expires_at")


def downgrade() -> None:
    op.execute("ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS access_token TEXT")
    op.execute("ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS refresh_token TEXT")
    op.execute("ALTER TABLE social_accounts ADD COLUMN IF NOT EXISTS token_expires_at TIMESTAMPTZ")
