"""Tests del servicio de notificaciones persistentes (UI.NOT)."""
from uuid import uuid4

import pytest
from app.services import notifications as svc


@pytest.mark.asyncio
class TestNotifications:
    async def test_create_y_list(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user.id,
            title="Factura creada", body="F2026-0001 por 121€", kind="success",
        )
        await db.commit()

        items = await svc.list_notifications(db, tenant_id=tenant.id, user_id=user.id)
        assert len(items) == 1
        assert items[0].title == "Factura creada"
        assert items[0].kind == "success"
        assert items[0].read_at is None

    async def test_count_unread(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        for i in range(3):
            await svc.create_notification(
                db, tenant_id=tenant.id, user_id=user.id, title=f"N{i}",
            )
        await db.commit()

        unread = await svc.count_unread(db, tenant_id=tenant.id, user_id=user.id)
        assert unread == 3

    async def test_mark_read(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        n = await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user.id, title="Hola",
        )
        await db.commit()

        changed = await svc.mark_read(db, tenant_id=tenant.id, notification_id=n.id)
        await db.commit()
        assert changed is True

        unread = await svc.count_unread(db, tenant_id=tenant.id, user_id=user.id)
        assert unread == 0

    async def test_mark_read_idempotente(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        n = await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user.id, title="Hola",
        )
        await db.commit()

        c1 = await svc.mark_read(db, tenant_id=tenant.id, notification_id=n.id)
        await db.commit()
        c2 = await svc.mark_read(db, tenant_id=tenant.id, notification_id=n.id)
        await db.commit()

        assert c1 is True
        assert c2 is False  # ya estaba leída

    async def test_mark_all_read(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        for i in range(4):
            await svc.create_notification(
                db, tenant_id=tenant.id, user_id=user.id, title=f"N{i}",
            )
        await db.commit()

        marked = await svc.mark_all_read(db, tenant_id=tenant.id, user_id=user.id)
        await db.commit()
        assert marked == 4

        unread = await svc.count_unread(db, tenant_id=tenant.id, user_id=user.id)
        assert unread == 0

    async def test_aislamiento_entre_tenants(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user
        other = uuid4()

        await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user.id, title="Mía",
        )
        await svc.create_notification(
            db, tenant_id=other, title="Ajena",
        )
        await db.commit()

        items = await svc.list_notifications(db, tenant_id=tenant.id, user_id=user.id)
        titles = [n.title for n in items]
        assert "Mía" in titles
        assert "Ajena" not in titles

    async def test_broadcast_tenant_wide_visible_a_todos(
        self, db, seed_tenant_and_user
    ):
        """user_id=None significa notificación tenant-wide (broadcast)."""
        tenant, user, _t = seed_tenant_and_user

        await svc.create_notification(
            db, tenant_id=tenant.id, user_id=None, title="Comunicado",
        )
        await db.commit()

        items = await svc.list_notifications(db, tenant_id=tenant.id, user_id=user.id)
        titles = [n.title for n in items]
        assert "Comunicado" in titles

    async def test_only_unread_filtra(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        n1 = await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user.id, title="Sin leer",
        )
        n2 = await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user.id, title="Leída",
        )
        await db.commit()

        await svc.mark_read(db, tenant_id=tenant.id, notification_id=n2.id)
        await db.commit()

        items = await svc.list_notifications(
            db, tenant_id=tenant.id, user_id=user.id, only_unread=True,
        )
        ids = [n.id for n in items]
        assert n1.id in ids
        assert n2.id not in ids

    async def test_payload_se_persiste(self, db, seed_tenant_and_user):
        tenant, user, _t = seed_tenant_and_user

        await svc.create_notification(
            db, tenant_id=tenant.id, user_id=user.id,
            title="Con payload",
            payload={"link": "/ventas/facturas/123", "invoice_id": "abc"},
        )
        await db.commit()

        items = await svc.list_notifications(db, tenant_id=tenant.id, user_id=user.id)
        assert items[0].payload == {"link": "/ventas/facturas/123", "invoice_id": "abc"}
