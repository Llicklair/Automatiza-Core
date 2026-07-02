"""Cuentas del proveedor de marketing social por tenant (BYO Zernio, multi-cuenta).

Cada `MarketingProviderConfig` = una cuenta de Zernio (un email / una API key). Un
tenant puede tener varias (el free tier da 2 cuentas sociales por email). Las keys
se guardan cifradas con TENANT_ENCRYPTION_KEY.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import MarketingProviderConfig, SocialAccount
from app.services.encryption import decrypt_str, encrypt_str
from app.services.marketing.zernio_client import ZernioClient, ZernioError


@dataclass
class ZernioConfigInfo:
    id: object
    label: Optional[str]
    default_profile_id: Optional[str]
    num_accounts: int


async def list_configs_with_counts(db: AsyncSession, tenant_id) -> list[ZernioConfigInfo]:
    """Lista cuentas de Zernio del tenant con el recuento de cuentas sociales activas."""
    configs = await list_provider_configs(db, tenant_id)
    out: list[ZernioConfigInfo] = []
    for c in configs:
        n = await db.scalar(
            select(func.count())
            .select_from(SocialAccount)
            .where(
                SocialAccount.provider_config_id == c.id,
                SocialAccount.is_active.is_(True),
            )
        )
        out.append(
            ZernioConfigInfo(
                id=c.id,
                label=c.label,
                default_profile_id=c.default_profile_id,
                num_accounts=n or 0,
            )
        )
    return out


async def add_zernio_config(
    db: AsyncSession,
    tenant_id,
    api_key: str,
    label: Optional[str] = None,
) -> ZernioConfigInfo:
    """Valida la API key de Zernio contra su API y persiste la nueva cuenta.

    Raises ZernioError si la key no es válida.
    """
    client = ZernioClient(api_key)
    profiles = await client.list_profiles()
    default_pid = str(profiles[0].get("_id") or profiles[0].get("id")) if profiles else None
    cfg = await add_provider_config(
        db,
        tenant_id,
        api_key,
        label=label,
        default_profile_id=default_pid,
    )
    await db.commit()
    return ZernioConfigInfo(
        id=cfg.id,
        label=cfg.label,
        default_profile_id=cfg.default_profile_id,
        num_accounts=0,
    )


async def list_provider_configs(db: AsyncSession, tenant_id) -> list[MarketingProviderConfig]:
    res = await db.execute(
        select(MarketingProviderConfig)
        .where(MarketingProviderConfig.tenant_id == tenant_id)
        .order_by(MarketingProviderConfig.created_at)
    )
    return list(res.scalars().all())


async def get_config(db: AsyncSession, config_id, tenant_id) -> MarketingProviderConfig | None:
    res = await db.execute(
        select(MarketingProviderConfig).where(
            MarketingProviderConfig.id == config_id,
            MarketingProviderConfig.tenant_id == tenant_id,
        )
    )
    return res.scalar_one_or_none()


def decrypted_api_key(cfg: MarketingProviderConfig | None) -> str | None:
    if not cfg or not cfg.api_key:
        return None
    return decrypt_str(cfg.api_key)


def client_for_config(cfg: MarketingProviderConfig | None) -> ZernioClient:
    """Construye el `ZernioClient` de una cuenta de Zernio concreta."""
    key = decrypted_api_key(cfg)
    if not key:
        raise ZernioError("Esta cuenta de Zernio no tiene API key configurada.")
    return ZernioClient(key)


async def add_provider_config(
    db: AsyncSession,
    tenant_id,
    api_key: str,
    label: str | None = None,
    default_profile_id: str | None = None,
) -> MarketingProviderConfig:
    """Añade una nueva cuenta de Zernio al tenant (varias permitidas)."""
    cfg = MarketingProviderConfig(
        tenant_id=tenant_id,
        provider="zernio",
        label=label,
        api_key=encrypt_str(api_key) if api_key else None,
        default_profile_id=default_profile_id,
    )
    db.add(cfg)
    await db.flush()
    return cfg


async def set_default_profile_id(db: AsyncSession, cfg: MarketingProviderConfig, profile_id: str) -> None:
    cfg.default_profile_id = profile_id
    await db.flush()


async def delete_provider_config(db: AsyncSession, config_id, tenant_id) -> bool:
    cfg = await get_config(db, config_id, tenant_id)
    if cfg is None:
        return False
    await db.delete(cfg)
    await db.flush()
    return True


async def client_for_account(db: AsyncSession, account: SocialAccount) -> ZernioClient:
    """Resuelve el `ZernioClient` de la cuenta social, por su `provider_config_id`."""
    if not account.provider_config_id:
        raise ZernioError("La cuenta no está vinculada a ninguna cuenta de Zernio; reconéctala.")
    res = await db.execute(
        select(MarketingProviderConfig).where(
            MarketingProviderConfig.id == account.provider_config_id,
            MarketingProviderConfig.tenant_id == account.tenant_id,
        )
    )
    cfg = res.scalar_one_or_none()
    return client_for_config(cfg)
