"""Integridad RAG — FK document_embeddings.document_id -> tenant_documents(id) CASCADE.

`document_embeddings.document_id` era un `String` SIN foreign key: al borrar un
`TenantDocument` (service.delete_document, snapshot, _contracts, rutas…) sus
embeddings quedaban HUÉRFANOS y el retrieval semántico (que filtra solo por
`tenant_id`) seguía sirviendo chunks de documentos ya borrados.

`document_id` siempre contiene un `tenant_documents.id` (el indexado carga el
documento por ese id antes de generar embeddings), así que se puede:
  1. Limpiar filas rotas (no-UUID u huérfanas) — son exactamente los embeddings
     que servían contenido fantasma.
  2. Convertir la columna a `uuid`.
  3. Añadir el FK con `ON DELETE CASCADE` → el borrado se propaga en la BD, en
     cualquier vía, sin depender de que cada call-site recuerde limpiar.

Idempotente y Postgres-only (en SQLite el modelo ya crea el FK vía create_all).

Revision ID: 0061_document_embeddings_fk
Revises: 0060_app_role_rls
"""

from alembic import op

revision = "0061_document_embeddings_fk"
down_revision = "0060_app_role_rls"
branch_labels = None
depends_on = None

_FK = "fk_document_embeddings_document"
_UUID_RE = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # 1. Eliminar embeddings con document_id no-UUID o huérfano (impedirían la
    #    conversión de tipo / la creación del FK; además son los huérfanos a purgar).
    op.execute(f"DELETE FROM document_embeddings WHERE document_id !~ '{_UUID_RE}'")
    op.execute(
        """
        DELETE FROM document_embeddings de
        WHERE NOT EXISTS (
            SELECT 1 FROM tenant_documents td WHERE td.id::text = de.document_id
        )
        """
    )

    # 2. Convertir el tipo de la columna a uuid.
    op.execute("ALTER TABLE document_embeddings " "ALTER COLUMN document_id TYPE uuid USING document_id::uuid")

    # 3. Añadir el FK con ON DELETE CASCADE (idempotente).
    op.execute(
        f"""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{_FK}') THEN
            ALTER TABLE document_embeddings
              ADD CONSTRAINT {_FK}
              FOREIGN KEY (document_id) REFERENCES tenant_documents(id) ON DELETE CASCADE;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(f"ALTER TABLE document_embeddings DROP CONSTRAINT IF EXISTS {_FK}")
    op.execute("ALTER TABLE document_embeddings " "ALTER COLUMN document_id TYPE varchar USING document_id::text")
