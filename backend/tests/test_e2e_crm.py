"""E2E CRM — flujo cliente → oportunidad → avance en el embudo → actividad.

Cruza varios endpoints contra la API real (SQLite en memoria, sin LLM):
  - se crea un cliente y una oportunidad vinculada a él,
  - la oportunidad avanza de etapa (new → qualified → won),
  - se registra una actividad ligada al cliente y a la oportunidad,
  - la oportunidad aparece en el embudo con su etapa final y la actividad se filtra por oportunidad.
"""
import pytest
from httpx import AsyncClient


class TestCrmE2E:
    @pytest.mark.asyncio
    async def test_cliente_oportunidad_actividad(self, auth_client: AsyncClient):
        # 1) Cliente (CRM reutiliza el Client de facturación).
        cli = await auth_client.post("/api/v1/clients", json={
            "name": "Cliente CRM S.L.", "nif": "B99999999", "email": "crm@cliente.com",
        })
        assert cli.status_code == 201, cli.text
        client_id = cli.json()["id"]

        # 2) Oportunidad en etapa inicial, vinculada al cliente.
        opp = await auth_client.post("/api/v1/crm/opportunities", json={
            "client_id": client_id,
            "title": "Implantación ERP",
            "expected_value": 15000.0,
            "stage": "new",
        })
        assert opp.status_code == 201, opp.text
        opp_data = opp.json()
        opp_id = opp_data["id"]
        assert opp_data["stage"] == "new"
        assert opp_data["client_id"] == client_id

        # 3) Avanzar la oportunidad en el embudo.
        for nueva_etapa in ("qualified", "won"):
            mv = await auth_client.patch(
                f"/api/v1/crm/opportunities/{opp_id}", json={"stage": nueva_etapa}
            )
            assert mv.status_code == 200, mv.text
            assert mv.json()["stage"] == nueva_etapa

        # 4) Actividad sobre el cliente y la oportunidad.
        act = await auth_client.post("/api/v1/crm/activities", json={
            "type": "call",
            "description": "Llamada de seguimiento; el cliente confirma la compra.",
            "client_id": client_id,
            "opportunity_id": opp_id,
        })
        assert act.status_code == 201, act.text
        act_id = act.json()["id"]

        # 5) La oportunidad aparece en el embudo con su etapa final.
        opps = await auth_client.get("/api/v1/crm/opportunities")
        assert opps.status_code == 200
        match = next(o for o in opps.json() if o["id"] == opp_id)
        assert match["stage"] == "won"

        # 6) La actividad aparece filtrada por su oportunidad.
        acts = await auth_client.get("/api/v1/crm/activities", params={"opportunity_id": opp_id})
        assert acts.status_code == 200
        assert act_id in [a["id"] for a in acts.json()]
