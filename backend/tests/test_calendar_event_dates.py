"""
Regresión: los schemas de entrada de eventos/reservas del CRM deben rechazar
end_time < start_time (ambos presentes) con 422. Si falta uno, se permite.
El validator vive SOLO en los schemas de ENTRADA (EventCreate/EventUpdate,
ReservationCreate/ReservationUpdate); NO en EventBase/ReservationBase, porque
EventResponse/ReservationResponse heredan de Base y se serializan al leer
registros legacy con end<start.
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient


class TestEventDateRange:
    @pytest.mark.asyncio
    async def test_create_event_end_before_start_422(self, auth_client: AsyncClient):
        payload = {
            "title": "Evento invertido",
            "start_time": "2026-06-27T10:00:00Z",
            "end_time": "2026-06-26T09:00:00Z",
            "type": "meeting",
        }
        resp = await auth_client.post("/api/v1/crm/events", json=payload)
        assert resp.status_code == 422, resp.text

    @pytest.mark.asyncio
    async def test_create_event_valid_range_not_422(self, auth_client: AsyncClient):
        # Control no-tautológico: mismo POST con end >= start NO debe ser 422.
        payload = {
            "title": "Evento valido",
            "start_time": "2026-06-26T10:00:00Z",
            "end_time": "2026-06-27T11:00:00Z",
            "type": "meeting",
        }
        resp = await auth_client.post("/api/v1/crm/events", json=payload)
        assert resp.status_code != 422, resp.text
        assert resp.status_code == 201, resp.text

    @pytest.mark.asyncio
    async def test_create_reservation_end_before_start_422(self, auth_client: AsyncClient):
        # ReservationCreate requiere client_id (UUID). El validator de rango
        # corre al deserializar el body, antes del servicio, así que un UUID
        # cualquiera basta para provocar el 422 por fechas invertidas.
        payload = {
            "client_id": str(uuid4()),
            "start_time": "2026-06-27T10:00:00Z",
            "end_time": "2026-06-26T09:00:00Z",
            "status": "pending",
        }
        resp = await auth_client.post("/api/v1/crm/reservations", json=payload)
        assert resp.status_code == 422, resp.text
