import asyncio
import sys
import time

import httpx

BASE_URL = "http://127.0.0.1:8080/api/v1"

async def run_demo():
    print("--- Iniciando script de demostración... ---")
    
    async with httpx.AsyncClient() as client:
        # 1. Login
        print("--- Iniciando sesión como demo@automatizapyme.com... ---")
        login_res = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": "demo@automatizapyme.com", "password": "Demo1234!"}
        )
        if login_res.status_code != 200:
            print(f"Error en login: {login_res.text}")
            sys.exit(1)
            
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("--- Login correcto ---")
        
        # 2. Crear tareas de demostración
        tasks_to_create = [
            {
                "domain": "billing",
                "user_intent": "Necesito facturar 5500 euros a la empresa cliente 'Tech Solutions SL' con NIF B60249562 por los servicios de consultoría informática del mes de octubre. El impuesto será del 21%."
            },
            {
                "domain": "banking",
                "user_intent": "Por favor, dame un resumen de los últimos movimientos bancarios de la cuenta principal."
            },
            {
                "domain": "compliance",
                "user_intent": "¿Podrías indicarme cuándo es el próximo plazo para presentar el modelo 303 de hacienda y si hay alguna novedad reciente en el BOE que afecte a autónomos?"
            }
        ]
        
        for t in tasks_to_create:
            print(f"\n--- Creando tarea de dominio '{t['domain']}'... ---")
            res = await client.post(
                f"{BASE_URL}/tasks/",  # Soluciono el 307 agregando el trailing slash
                json=t,
                headers=headers
            )
            if res.status_code == 200 or res.status_code == 201:
                task_data = res.json()
                print(f"--- Tarea creada con ID: {task_data['id']} ---")
            else:
                print(f"--- Error al crear tarea: {res.text} ---")
                
        print("\n--- Esperando 15 segundos para que los agentes (Celery/LangGraph) terminen de procesar... ---")
        for i in range(15):
            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(1)
            
        print("\n\n--- Demostración lista. Revisa el Dashboard en http://localhost:3000 ---")

if __name__ == "__main__":
    asyncio.run(run_demo())
