"""upload_bulk: las entradas de un ZIP con extensión no permitida se rechazan.

Regresión de seguridad: un ZIP con una entrada `.php`/`.exe` no debe escribir
ficheros de tipo arbitrario en UPLOAD_DIR ni crear un TenantDocument. La entrada
válida (`.pdf`) sí se procesa; la inválida se omite (skip + log).
"""

import io
import zipfile
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import TenantDocument
from app.services.documents.service import upload_bulk


def _build_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_bulk_skips_disallowed_extension(
    db: AsyncSession, seed_tenant_and_user
):
    tenant, user, _ = seed_tenant_and_user
    contents = _build_zip(
        {
            "factura.pdf": b"%PDF-1.4 ok",
            "shell.php": b"<?php system($_GET['c']); ?>",
        }
    )

    with patch(
        "app.services.workflow.task_dispatch.dispatch_orchestrator",
        new=AsyncMock(return_value=None),
    ):
        docs = await upload_bulk(contents, tenant.id, user.id, db)

    # Solo la entrada válida produce documento.
    assert len(docs) == 1
    assert docs[0].file_name == "factura.pdf"

    result = await db.execute(
        select(TenantDocument).where(TenantDocument.tenant_id == tenant.id)
    )
    names = {d.file_name for d in result.scalars().all()}
    assert "factura.pdf" in names
    assert "shell.php" not in names
