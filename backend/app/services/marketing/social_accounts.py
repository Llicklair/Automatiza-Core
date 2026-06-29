"""Cuentas sociales de marketing (Zernio): orquestación de desconexión.

Recibe `db` inyectado. La ruta solo mapea a HTTP (404 si no existe; 502 si Zernio
falla con un error != 404, que se propaga como ZernioError).
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import SocialAccount
from app.services.marketing.provider_config import client_for_account
from app.services.marketing.zernio_client import ZernioError


async def list_accounts(tenant_id, db: AsyncSession) -> list[SocialAccount]:
    """Lista las cuentas sociales activas del tenant."""
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.tenant_id == tenant_id,
            SocialAccount.is_active.is_(True),
        )
    )
    return list(result.scalars().all())


async def upsert_from_callback(
    tenant_id,
    config_id,
    account_id_str: str,
    username: Optional[str],
    platform: str,
    db: AsyncSession,
) -> SocialAccount:
    """Upsert de una cuenta social a partir del callback OAuth de Zernio."""
    existing = await db.execute(
        select(SocialAccount).where(
            SocialAccount.tenant_id == tenant_id,
            SocialAccount.account_id == account_id_str,
        )
    )
    account = existing.scalar_one_or_none()
    if account:
        account.platform = platform
        account.account_name = username or account.account_name
        account.provider_config_id = config_id
        account.is_active = True
    else:
        account = SocialAccount(
            tenant_id=tenant_id,
            platform=platform,
            account_id=account_id_str,
            account_name=username,
            provider_config_id=config_id,
            is_active=True,
        )
        db.add(account)
    await db.commit()
    return account


async def disconnect_account(account_id: UUID, tenant_id, db: AsyncSession) -> bool:
    """Desconecta una cuenta social: libera el hueco en Zernio (best-effort) y la
    marca inactiva localmente.

    Devuelve False si la cuenta no existe (la ruta → 404). Propaga `ZernioError`
    si Zernio falla con un estado != 404 (la ruta → 502).
    """
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.tenant_id == tenant_id,
        )
    )
    account = result.scalar_one_or_none()
    if account is None:
        return False

    # Libera el hueco en Zernio (plan gratis: 2 redes/email) para poder conectar otra.
    try:
        client = await client_for_account(db, account)
    except ZernioError:
        client = None
    if client is not None:
        try:
            await client.disconnect_account(account.account_id)
        except ZernioError as e:
            if e.status != 404:  # 404 = ya no existe en Zernio; continuamos
                raise

    account.is_active = False
    await db.commit()
    return True
