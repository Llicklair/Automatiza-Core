import asyncio

import httpx

BASE_URL = "http://localhost:8080/api/v1"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # 1) Login como demo (creado previamente por smoke_demo / create_user)
        print("== Login demo para pruebas de tareas/automatizaciones ==")
        r = await client.post(
            "/auth/login",
            json={"email": "demo@automatizapyme.com", "password": "Demo1234!"},
        )
        print("login status:", r.status_code)
        if r.status_code != 200:
            print("login response:", r.text)
            return

        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2) Crear tarea de billing (creación de factura IA)
        print("\n== Crear tarea de billing (factura IA) ==")
        billing_intent = (
            "Crea una factura de 2400 euros a la empresa 'Consultoría SEO S.A.' "
            "con NIF B11223344 por consultoría web de Noviembre 2023, IVA 21%."
        )
        r = await client.post(
            "/tasks",
            json={"domain": "billing", "user_intent": billing_intent},
            headers=headers,
        )
        print("create billing task status:", r.status_code)
        if r.status_code not in (200, 201):
            print("create billing task response:", r.text)
            return
        billing_task = r.json()
        billing_task_id = billing_task["id"]
        print("billing task id:", billing_task_id)

        # 3) Crear tarea de HR (agente RRHH)
        print("\n== Crear tarea de HR (RRHH) ==")
        hr_intent = "Genera un resumen de vacaciones pendientes y coste salarial estimado para este mes."
        r = await client.post(
            "/tasks",
            json={"domain": "hr", "user_intent": hr_intent},
            headers=headers,
        )
        print("create hr task status:", r.status_code)
        if r.status_code not in (200, 201):
            print("create hr task response:", r.text)
            return
        hr_task = r.json()
        hr_task_id = hr_task["id"]
        print("hr task id:", hr_task_id)

        # 4) Polling simple del estado de ambas tareas
        print("\n== Polling de estado de tareas (billing + hr) ==")
        for i in range(10):
            for tid, label in [(billing_task_id, "billing"), (hr_task_id, "hr")]:
                tr = await client.get(f"/tasks/{tid}", headers=headers)
                if tr.status_code == 200:
                    data = tr.json()
                    print(f"  [{label}] intento {i+1}/10 -> status={data['status']}")
                else:
                    print(f"  [{label}] intento {i+1}/10 -> error {tr.status_code}")
            await asyncio.sleep(2)

        # 5) Listar aprobaciones pendientes (si el billing agent ha pedido approval)
        print("\n== Listar aprobaciones pendientes ==")
        r = await client.get("/approvals", headers=headers)
        print("approvals status:", r.status_code)
        if r.status_code == 200:
            approvals = r.json()
            print("num approvals:", len(approvals))
            for a in approvals:
                print("-", a.get("id"), "|", a.get("risk_level"), "|", a.get("action_description"))
        else:
            print("approvals response:", r.text)

        # 6) Crear y ejecutar un workflow sencillo (automatización manual)
        print("\n== Crear workflow manual de prueba ==")
        wf_payload = {
            "name": "Aviso facturas altas",
            "description": "Cuando se cree una factura de más de 5000€, genera un informe IA.",
            "is_active": True,
            "trigger_type": "event_based",
            "trigger_config": {"events": ["invoice_created"]},
            "action_type": "ai_task",
            "action_config": {
                "instruction": (
                    "Analiza la factura recién creada y genera un breve informe de riesgo "
                    "y recomendaciones para el director financiero."
                ),
                "domain": "billing",
            },
        }
        r = await client.post("/workflows/", json=wf_payload, headers=headers)
        print("create workflow status:", r.status_code)
        if r.status_code not in (200, 201):
            print("create workflow response:", r.text)
            return
        workflow = r.json()
        workflow_id = workflow["id"]
        print("workflow id:", workflow_id)

        # 7) Lanzar el workflow manualmente
        print("\n== Ejecutar workflow manualmente ==")
        r = await client.post(f"/workflows/{workflow_id}/run", headers=headers)
        print("run workflow status:", r.status_code)
        if r.status_code not in (200, 201):
            print("run workflow response:", r.text)
            return
        exec_data = r.json()
        exec_id = exec_data["id"]
        linked_task_id = exec_data.get("task_id")
        print("workflow execution id:", exec_id, "task_id:", linked_task_id)

        # 8) Polling de la tarea enlazada al workflow
        if linked_task_id:
            print("\n== Polling tarea del workflow ==")
            for i in range(10):
                tr = await client.get(f"/tasks/{linked_task_id}", headers=headers)
                if tr.status_code == 200:
                    data = tr.json()
                    print(f"  [workflow task] intento {i+1}/10 -> status={data['status']}")
                    if data["status"] in ("done", "failed"):
                        break
                else:
                    print("  [workflow task] error", tr.status_code)
                await asyncio.sleep(2)

        # 9) Listar workflows y sus últimas ejecuciones
        print("\n== Listar workflows del tenant ==")
        r = await client.get("/workflows/", headers=headers)
        print("workflows status:", r.status_code)
        if r.status_code == 200:
            workflows = r.json()
            print("num workflows:", len(workflows))
            for wf in workflows:
                print("-", wf.get("id"), "|", wf.get("name"), "| active:", wf.get("is_active"))
        else:
            print("workflows response:", r.text)


if __name__ == "__main__":
    asyncio.run(main())

