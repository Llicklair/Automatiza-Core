import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        # tenant_id -> set of active WebSockets
        self.active_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = set()
        self.active_connections[tenant_id].add(websocket)

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        if tenant_id in self.active_connections:
            self.active_connections[tenant_id].discard(websocket)
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        # UI.AGT — fan-out al TaskEventHub para suscriptores SSE por task_id.
        # Best-effort: si falla, no debe afectar el broadcast WS.
        task_id = message.get("task_id")
        if task_id:
            try:
                from app.services.workflow.task_event_hub import task_event_hub

                await task_event_hub.publish(str(task_id), message)
                # Si el evento es terminal, cerramos el stream.
                if message.get("type") in ("task_completed", "task_failed") or message.get("step") == message.get(
                    "total_steps"
                ):
                    await task_event_hub.signal_end(str(task_id))
            except Exception as _e:
                logger.debug("task_event_hub fan-out falló (silenciado): %s", _e)

        if tenant_id in self.active_connections:
            connections = list(self.active_connections[tenant_id])
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as _e:
                    logger.warning("WebSocket roto para tenant %s, desconectando: %s", tenant_id, _e)
                    # Clean up broken connections
                    self.disconnect(connection, tenant_id)


manager = ConnectionManager()


async def get_token_tenant(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        tenant_id: str = payload.get("tenant_id")
        if tenant_id is None:
            raise ValueError("Token no contiene tenant_id")
        return tenant_id
    except JWTError as exc:
        raise ValueError("Token inválido") from exc


@router.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    try:
        tenant_id = await get_token_tenant(token)
    except Exception as e:
        await websocket.close(code=1008, reason=str(e))
        return

    await manager.connect(websocket, tenant_id)
    try:
        while True:
            # We don't expect messages from the client in this basic implementation
            # but we need to wait to keep the connection open
            data = await websocket.receive_text()
            # Respond to pings if needed
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
