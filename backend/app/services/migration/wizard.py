"""Wizard de importación (MIG.3) — orquesta preview → confirm → persist con rollback.

Flujo:
1. **Upload + Preview**: el cliente sube CSV (MIG.1) o configura API Holded (MIG.2).
   El sistema devuelve `ImportPreview` con las primeras 10 filas mapeadas y los
   campos detectados/no detectados.
2. **Confirm**: el cliente revisa, ajusta mapping si procede, y confirma.
3. **Persist**: el wizard hace dry-run dentro de una transacción. Si dry-run
   detecta errores fatales (>N% filas con errores), aborta. Si no, hace commit.
4. **Rollback automático** si algo falla a mitad — usamos transacción única
   con savepoint por fila opcional.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.crm import Client
from app.services.migration.csv_importer import ImportPreview, ImportRow


@dataclass
class ImportResult:
    """Resultado de un import confirmado."""

    inserted: int
    updated: int
    skipped: int
    failed: int
    errors: list[str]


# Umbral de errores fatales: si más del 20% de las filas tienen errores,
# el wizard aborta en dry-run.
ERROR_RATIO_THRESHOLD = 0.20


def _validate_preview_for_commit(preview: ImportPreview, total_in_set: int) -> str | None:
    """Devuelve `None` si el preview puede commitearse; mensaje de error si no."""
    if total_in_set == 0:
        return "El archivo no contiene filas válidas."
    if not preview.header_mapping:
        return "No se ha podido mapear ninguna columna a campos canónicos."
    error_ratio = preview.errors_count / total_in_set if total_in_set > 0 else 1.0
    if error_ratio > ERROR_RATIO_THRESHOLD:
        return (
            f"Más del {int(ERROR_RATIO_THRESHOLD * 100)}% de las filas tienen errores "
            f"({preview.errors_count}/{total_in_set}). Revisa el archivo y reintenta."
        )
    return None


async def import_clients(
    db: AsyncSession,
    tenant_id: UUID,
    rows: list[ImportRow],
    *,
    dry_run: bool = False,
) -> ImportResult:
    """Persiste clientes desde rows canónicas.

    Estrategia upsert por (tenant_id, nif): si existe → update name/email/etc.,
    si no → insert. Filas con errores se skipean (registradas en `errors`).

    Si `dry_run=True`, se ejecutan las operaciones pero NO se hace commit
    (el caller debe gestionar la transacción). Útil para el wizard preview.
    """
    inserted = updated = skipped = failed = 0
    errors: list[str] = []

    for row in rows:
        if row.errors:
            skipped += 1
            continue
        nif = row.canonical.get("nif")
        name = row.canonical.get("name")
        if not nif and not name:
            skipped += 1
            continue

        try:
            existing = None
            if nif:
                result = await db.execute(
                    select(Client).where(
                        Client.tenant_id == tenant_id,
                        Client.nif == str(nif),
                    )
                )
                existing = result.scalar_one_or_none()

            if existing:
                if name:
                    existing.name = str(name)
                email = row.canonical.get("email")
                if email:
                    existing.email = str(email)
                phone = row.canonical.get("phone")
                if phone:
                    existing.phone = str(phone)
                updated += 1
            else:
                client = Client(
                    tenant_id=tenant_id,
                    nif=str(nif) if nif else None,
                    name=str(name) if name else "Cliente importado",
                )
                # Optional fields
                for opt in ("email", "phone", "address"):
                    value = row.canonical.get(opt)
                    if value and hasattr(client, opt):
                        setattr(client, opt, str(value))
                db.add(client)
                inserted += 1
        except Exception as e:
            failed += 1
            errors.append(f"NIF {nif!r}: {type(e).__name__}: {e}")

    if dry_run:
        await db.rollback()
    else:
        await db.flush()

    return ImportResult(
        inserted=inserted,
        updated=updated,
        skipped=skipped,
        failed=failed,
        errors=errors,
    )
