"""Tests de validación de rango de fechas en schemas de Projects.

Verifica que due_date < start_date (ambos presentes) devuelve 422 en el camino
de ENTRADA (Create/Update) y que el caso válido NO se rechaza. La serialización
de Response (registros legacy) no debe verse afectada porque el validator vive
solo en Create/Update, no en Base.
"""
import pytest


@pytest.mark.asyncio
async def test_create_project_inverted_dates_returns_422(auth_client):
    resp = await auth_client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto fechas invertidas",
            "start_date": "2026-06-10T00:00:00",
            "due_date": "2026-06-01T00:00:00",
        },
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_create_project_valid_dates_not_422(auth_client):
    resp = await auth_client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto fechas válidas",
            "start_date": "2026-06-01T00:00:00",
            "due_date": "2026-06-10T00:00:00",
        },
    )
    # Control no-tautológico: el caso correcto debe crear (201), no 422.
    assert resp.status_code == 201, resp.text
    assert resp.status_code != 422


@pytest.mark.asyncio
async def test_create_project_only_one_date_is_allowed(auth_client):
    # Falta una de las dos fechas → no se valida el rango → no 422 por fechas.
    resp = await auth_client.post(
        "/api/v1/projects",
        json={
            "name": "Proyecto solo start",
            "start_date": "2026-06-10T00:00:00",
        },
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_create_task_inverted_dates_returns_422(auth_client):
    resp = await auth_client.post(
        "/api/v1/projects/tasks",
        json={
            "title": "Tarea fechas invertidas",
            "start_date": "2026-06-10T00:00:00",
            "due_date": "2026-06-01T00:00:00",
        },
    )
    assert resp.status_code == 422, resp.text
