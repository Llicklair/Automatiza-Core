"""Healthcheck de precondiciones legales para facturación (CONT.KILL).

Si alguna precondición falla, las rutas que crean facturas devuelven 503
para evitar emitir documentos no defendibles ante AEAT/inspección.

Precondiciones verificadas:
* **FAC.NUM**: la tabla `invoice_series` existe — numeración correlativa
  por serie/año está disponible.
* **SEC.APR**: la tabla `fiscal_approval_log` existe — aprobación fiscal
  humana puede registrarse cuando proceda.
"""

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import AsyncSession

REQUIRED_TABLES = ("invoice_series", "fiscal_approval_log")


async def check_invoice_preconditions(db: AsyncSession) -> dict:
    """Verifica que las tablas críticas para facturación existen.

    Devuelve `{ok: bool, details: {table: bool}, missing: [str]}`.
    Usado por el endpoint `/api/v1/system/preconditions` y por el dependency
    `require_invoice_preconditions` que protege los endpoints de creación.
    """

    def _check_tables(sync_conn) -> dict[str, bool]:
        inspector = inspect(sync_conn)
        existing = set(inspector.get_table_names())
        return {tbl: tbl in existing for tbl in REQUIRED_TABLES}

    conn = await db.connection()
    table_status = await conn.run_sync(_check_tables)
    missing = [t for t, present in table_status.items() if not present]
    return {
        "ok": len(missing) == 0,
        "details": table_status,
        "missing": missing,
    }
