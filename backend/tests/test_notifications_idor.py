"""
Regresión IDOR intra-tenant en notificaciones (authz por-usuario).

Las notificaciones son por-usuario: `Notification.user_id` nullable, donde
NULL = broadcast tenant-wide. Antes del fix, `mark_read` filtraba el WHERE solo
por `tenant_id` (no por `user_id`), así que un usuarioA del MISMO tenant podía
marcar leída la notificación PRIVADA de usuarioB:
    PATCH /api/v1/notifications/<id_de_B>/read  → 200 (debía ser 404).

Tras el fix, `mark_read` recibe `user_id` y el WHERE exige
`(user_id == actual) | (user_id IS NULL)`, igual que list/count/mark_all_read.

Estos tests demuestran:
  - userA NO puede marcar leída la notif privada de userB → 404.
  - Control no-tautológico: userB SÍ puede marcar la suya → 200.
  - list/unread-count de userA NO exponen la privada de B pero SÍ los broadcasts
    (ya filtraban bien; aquí se verifica que el endpoint sigue correcto).
"""
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, get_password_hash
from app.db.models.models import Tenant, User
from app.main import app
from app.services import notifications as svc


@pytest.fixture
async def two_users_same_tenant(db):
    """Crea UN tenant con DOS usuarios (A y B) y devuelve tenant + ambos users."""
    tenant = Tenant(
        id=uuid4(),
        name="Tenant Compartido S.L.",
        nif="B22222222",
        plan="starter",
    )
    db.add(tenant)
    await db.flush()

    user_a = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="user_a@empresa.com",
        hashed_password=get_password_hash("UserAPass123!"),
        full_name="Usuario A",
        role="user",
    )
    user_b = User(
        id=uuid4(),
        tenant_id=tenant.id,
        email="user_b@empresa.com",
        hashed_password=get_password_hash("UserBPass123!"),
        full_name="Usuario B",
        role="user",
    )
    db.add(user_a)
    db.add(user_b)
    await db.commit()

    token_a = create_access_token({
        "sub": str(user_a.id),
        "tenant_id": str(tenant.id),
        "role": "user",
    })
    token_b = create_access_token({
        "sub": str(user_b.id),
        "tenant_id": str(tenant.id),
        "role": "user",
    })
    return tenant, user_a, user_b, token_a, token_b


def _client(token: str) -> AsyncClient:
    transport = ASGITransport(app=app)
    ac = AsyncClient(transport=transport, base_url="http://test")
    ac.headers["Authorization"] = f"Bearer {token}"
    return ac


@pytest.mark.asyncio
class TestNotificationsIDOR:

    async def test_user_a_cannot_mark_read_private_notif_of_b(
        self, db, two_users_same_tenant
    ):
        """
        CASO ORO: notif PRIVADA de B (user_id=B). A intenta marcarla leída.
        Debe obtener 404 (no-op → rowcount=0). Antes del fix devolvía 200.
        """
        tenant, user_a, user_b, token_a, _token_b = two_users_same_tenant

        notif_b = await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user_b.id, title="Privada de B",
        )
        await db.commit()

        async with _client(token_a) as ca:
            resp = await ca.patch(f"/api/v1/notifications/{notif_b.id}/read")

        assert resp.status_code == 404, (
            f"IDOR activo: userA obtuvo {resp.status_code} al marcar leída la "
            f"notif privada de userB. Respuesta: {resp.text}"
        )

        # Y la notif de B sigue SIN leer en BD.
        await db.refresh(notif_b)
        assert notif_b.read_at is None, (
            "userA marcó leída la notif privada de userB pese al 404"
        )

    async def test_user_b_can_mark_read_own_notif(
        self, db, two_users_same_tenant
    ):
        """
        CONTROL no-tautológico: B marca SU PROPIA notif → 200.
        Verifica que el gate es selectivo, no que rechaza todo.
        """
        tenant, _user_a, user_b, _token_a, token_b = two_users_same_tenant

        notif_b = await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user_b.id, title="Propia de B",
        )
        await db.commit()

        async with _client(token_b) as cb:
            resp = await cb.patch(f"/api/v1/notifications/{notif_b.id}/read")

        assert resp.status_code == 200, (
            f"userB no pudo marcar leída su propia notif: {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )

    async def test_user_can_mark_read_broadcast(
        self, db, two_users_same_tenant
    ):
        """Broadcast (user_id IS NULL) → cualquier usuario del tenant puede marcarlo."""
        tenant, user_a, _user_b, token_a, _token_b = two_users_same_tenant

        bcast = await svc.create_notification(
            db, tenant_id=tenant.id, user_id=None, title="Comunicado tenant",
        )
        await db.commit()

        async with _client(token_a) as ca:
            resp = await ca.patch(f"/api/v1/notifications/{bcast.id}/read")

        assert resp.status_code == 200, (
            f"userA no pudo marcar leído un broadcast: {resp.status_code}. "
            f"Respuesta: {resp.text}"
        )

    async def test_list_and_unread_count_hide_private_of_others(
        self, db, two_users_same_tenant
    ):
        """
        LECTURA: list/unread-count de A NO exponen la privada de B,
        pero SÍ incluyen/cuentan los broadcasts y lo propio de A.
        (list_notifications/count_unread ya filtraban; verificamos el endpoint.)
        """
        tenant, user_a, user_b, token_a, _token_b = two_users_same_tenant

        await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user_b.id, title="Privada de B",
        )
        await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user_a.id, title="Privada de A",
        )
        await svc.create_notification(
            db, tenant_id=tenant.id, user_id=None, title="Comunicado tenant",
        )
        await db.commit()

        async with _client(token_a) as ca:
            resp = await ca.get("/api/v1/notifications")

        assert resp.status_code == 200, resp.text
        data = resp.json()
        titles = {item["title"] for item in data["items"]}

        assert "Privada de B" not in titles, (
            "IDOR de lectura: userA ve la notif privada de userB"
        )
        assert "Privada de A" in titles
        assert "Comunicado tenant" in titles
        # unread_count cuenta lo propio (1) + broadcast (1) = 2, nunca la de B.
        assert data["unread_count"] == 2, (
            f"unread_count incorrecto: {data['unread_count']} "
            f"(no debe contar la privada de B). Respuesta: {data}"
        )
