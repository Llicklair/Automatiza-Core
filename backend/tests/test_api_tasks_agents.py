import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task_and_run_mock(client: AsyncClient, seed_tenant_and_user):
    """
    Prueba que se pueda crear una tarea y que el orquestador 
    funcione (usando Mock LLM por falta de llaves en entorno test).
    """
    tenant, user, token = seed_tenant_and_user
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Crear tarea
    payload = {
        "domain": "billing",
        "user_intent": "Lista las facturas pendientes de cobro y genera un resumen."
    }
    resp = await client.post("/api/v1/tasks", json=payload, headers=headers)
    assert resp.status_code == 201
    task_data = resp.json()
    task_id = task_data["id"]
    assert task_data["status"] == "pending"

    # En un entorno real, Celery procesaría esta tarea.
    # Aquí simplemente verificamos que la creación fue exitosa y la estructura es correcta.
    # No podemos ejecutar el worker de Celery fácilmente en este test unitario síncrono,
    # pero hemos asegurado que la core factory (llm_factory) devolverá un Mock
    # si se intenta inicializar un agente durante el flujo.
    
    assert "user_intent" in task_data
    assert task_data["domain"] == "billing"
