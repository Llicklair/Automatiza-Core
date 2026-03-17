import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_tenant_me_and_update(client: AsyncClient):
    # 1. Registrar un usuario y tenant para obtener token
    email = "tenant@test.com"
    password = "Password123!"
    reg_payload = {
        "email": email,
        "password": password,
        "full_name": "Tenant Admin",
        "tenant": {
            "name": "Empresa Test Original",
            "nif": "T12345678",
        },
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # 2. Login para obtener access_token
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password,
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. GET /me (verificar campos iniciales)
    me_resp = await client.get("/api/v1/tenant/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["name"] == "Empresa Test Original"
    assert me_data["nif"] == "T12345678"
    assert me_data["address"] is None
    assert me_data["phone"] is None
    assert me_data["contact_email"] is None

    # 4. PATCH /me (actualizar metadatos nuevos)
    update_payload = {
        "name": "Empresa Test Modificada",
        "address": "Calle Falsa 123",
        "phone": "+34 912 345 678",
        "contact_email": "contacto@empresatest.com"
    }
    patch_resp = await client.patch("/api/v1/tenant/me", json=update_payload, headers=headers)
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["name"] == "Empresa Test Modificada"
    assert patch_data["address"] == "Calle Falsa 123"
    assert patch_data["phone"] == "+34 912 345 678"
    assert patch_data["contact_email"] == "contacto@empresatest.com"

    # 5. Volver a llamar a GET para asegurar persistencia
    me_resp_2 = await client.get("/api/v1/tenant/me", headers=headers)
    me_data_2 = me_resp_2.json()
    assert me_data_2["address"] == "Calle Falsa 123"
    assert me_data_2["phone"] == "+34 912 345 678"
    assert me_data_2["contact_email"] == "contacto@empresatest.com"
