"""
Redis pub/sub → WebSocket relay.

When Celery workers run in separate processes they cannot access the
in-process WebSocket ConnectionManager. Instead, they publish events to
Redis channel ``ap:ws:{tenant_id}``. This service subscribes to those
channels and forwards messages to the WebSocket clients.

Only started when REDIS_URL is configured.
"""

from __future__ import annotations

import asyncio
import json
import logging

_log = logging.getLogger(__name__)
_relay_task: asyncio.Task | None = None


async def start_ws_relay() -> None:
    from app.core.config import settings

    if not settings.REDIS_URL:
        return

    global _relay_task
    _relay_task = asyncio.create_task(_run(settings.REDIS_URL), name="ws_redis_relay")
    _log.info("WebSocket Redis relay iniciado (canal: ap:ws:*)")


async def stop_ws_relay() -> None:
    global _relay_task
    if _relay_task and not _relay_task.done():
        _relay_task.cancel()
        try:
            await _relay_task
        except asyncio.CancelledError:
            pass
    _relay_task = None


async def _run(redis_url: str) -> None:
    try:
        import redis.asyncio as aioredis
    except ImportError:
        _log.warning("redis-py no instalado — relay WebSocket desactivado")
        return

    from app.api.ws.notifications import manager as ws_manager

    r = aioredis.from_url(redis_url, decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.psubscribe("ap:ws:*")

    try:
        async for raw in pubsub.listen():
            if raw.get("type") != "pmessage":
                continue
            channel: str = raw.get("channel", "")
            tenant_id = channel.removeprefix("ap:ws:")
            if not tenant_id:
                continue
            try:
                data = json.loads(raw["data"])
                await ws_manager.broadcast_to_tenant(tenant_id, data)
            except Exception:
                _log.debug("Error procesando mensaje Redis relay", exc_info=True)
    except asyncio.CancelledError:
        pass
    except Exception:
        _log.exception("Error en ws_relay._run — relay detenido")
    finally:
        await pubsub.punsubscribe("ap:ws:*")
        await r.aclose()
