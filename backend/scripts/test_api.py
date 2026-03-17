import urllib.request
import urllib.parse
import json
import time

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

print("1. Login...")
status, user = request("http://127.0.0.1:8080/api/v1/auth/login", "POST", {
    "email": "demo@automatizapyme.com",
    "password": "Demo1234!"
})
if status != 200 or not user:
    print("Login failed")
    exit(1)
    
token = user["access_token"]
print("2. Creando tarea de facturación...")
status, task = request("http://127.0.0.1:8080/api/v1/tasks", "POST", {
    "domain": "billing",
    "user_intent": "Facturar 2400 euros a la empresa 'Consultoría SEO S.A.' con NIF B11223344 por consultoria web de Noviembre 2023. Impuesto 21%."
}, token)

if status not in (200, 201):
    print("Failed to create task")
    exit(1)

task_id = task["id"]
print(f"Task created: {task_id}. Polling...")

while True:
    status, updated_task = request(f"http://127.0.0.1:8080/api/v1/tasks/{task_id}", "GET", token=token)
    if status != 200:
        print("Failed to get task")
        break
    
    t_status = updated_task.get("status")
    print(f"Status: {t_status}")
    if t_status in ["done", "failed"]:
        print("Final task payload:", json.dumps(updated_task, indent=2))
        break
    time.sleep(2)
