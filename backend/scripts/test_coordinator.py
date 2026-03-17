import urllib.request
import urllib.parse
import json
import time
import sys

def request(url, method="GET", json_data=None, token=None):
    headers = {}
    if json_data:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(json_data).encode('utf-8')
    else:
        data = None
    if token:
        headers['Authorization'] = f'Bearer {token}'
        
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code} for {url} - {e.read().decode('utf-8')}")
        return e.code, None
    except Exception as e:
        print(f"Error {url} - {e}")
        return 500, None

def run_test():
    print("1. Login...")
    status, user = request("http://127.0.0.1:8080/api/v1/auth/login", "POST", {
        "email": "demo@automatizapyme.com",
        "password": "Demo1234!"
    })
    
    if status != 200 or not user:
        print("Login failed")
        sys.exit(1)
        
    token = user["access_token"]
    
    print("\n2. Creando tarea compleja (Coordinador)...")
    
    # Prompt complejo que involucra varios agentes (ej. HR para sacar NIF, Billing para facturar, Email para enviar)
    complex_intent = "Busca el NIF del empleado Carlos, luego crea una factura por 500 euros concepto 'Bono rendimiento' a ese NIF y finalmente enviale un correo avisando que ya está la factura."
    
    print(f"Intent: '{complex_intent}'")
    
    status, task = request("http://127.0.0.1:8080/api/v1/tasks", "POST", {
        "domain": "coordinator",
        "user_intent": complex_intent
    }, token)

    if status not in (200, 201):
        print(f"Failed to create task (Status: {status})")
        sys.exit(1)

    task_id = task["id"]
    print(f"\nTask created: {task_id}. Polling status...")

    already_approved = False
    
    while True:
        status, updated_task = request(f"http://127.0.0.1:8080/api/v1/tasks/{task_id}", "GET", token=token)
        if status != 200:
            print(f"Failed to get task (Status: {status})")
            break

        t_status = updated_task.get("status")
        print(f"Status: {t_status}")
        
        if t_status == "awaiting_approval" and not already_approved:
            print("\nTask is awaiting approval. Approving now...")
            approval_id = updated_task["agent_results"][-1]["output"]["approval_id"]
            
            # Aprobar la tarea
            auth_headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = json.dumps({"approved": True}).encode("utf-8")
            approve_req = urllib.request.Request(
                f"http://127.0.0.1:8080/api/v1/approvals/{approval_id}/decide",
                data=payload,
                method="POST",
                headers=auth_headers
            )
            try:
                urllib.request.urlopen(approve_req)
                print("Approval successful!")
                already_approved = True
            except Exception as e:
                print(f"Approval failed: {e}")
                break
                
            continue # Seguir esperando a que termine
            
        if t_status in ["done", "failed"]:
            print("\nFinal task payload:")
            print(json.dumps(updated_task, indent=2))
            break
            
        time.sleep(2)

if __name__ == "__main__":
    run_test()
