"""Marketing OAuth callback — un fallo de perfil NO debe crear una cuenta 'unknown'.

Bug (auditoría): para twitter/linkedin, si `_fetch_profile` falla, el callback
tragaba la excepción (`account_id_str=""`) y el upsert creaba una cuenta con
`account_id='unknown'` (fantasma); reconectar la duplicaba. Este test reproduce
el fallo y blinda que el callback aborte sin persistir nada.
"""
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.api.v1.routes import marketing as mkt_routes
from app.db.models.marketing import SocialAccount


@pytest.mark.asyncio
async def test_callback_perfil_fallido_no_crea_cuenta_unknown(
    auth_client: AsyncClient, db, seed_tenant_and_user
):
    tenant, _u, _t = seed_tenant_and_user
    state = mkt_routes._encode_state("twitter", str(tenant.id))

    async def fake_exchange(platform, code, state):
        return {"access_token": "tok-123"}

    async def boom_profile(platform, token):
        raise RuntimeError("perfil 500")

    with patch.object(mkt_routes, "_exchange_token", fake_exchange), patch.object(
        mkt_routes, "_fetch_profile", boom_profile
    ):
        resp = await auth_client.get(
            f"/api/v1/marketing/oauth/callback?code=abc&state={state}"
        )

    # El popup siempre responde 200; lo que NO debe pasar es crear una cuenta.
    assert resp.status_code == 200
    accounts = (
        await db.execute(
            select(SocialAccount).where(SocialAccount.tenant_id == tenant.id)
        )
    ).scalars().all()
    assert accounts == [], (
        "un fallo al obtener el perfil no debe persistir una cuenta 'unknown' "
        f"(se crearon {len(accounts)})"
    )
