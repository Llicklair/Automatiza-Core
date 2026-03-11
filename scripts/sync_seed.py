import urllib.request
import urllib.parse
import json
import time

def q(url, data):
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as response:
            print("OK:", url)
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print("ERR:", url, getattr(e, 'read', lambda: b'()')().decode('utf-8'))

print("1. Registering user...")
q("http://127.0.0.1:8080/api/v1/auth/register", {
    "email": "demo@automatizapyme.com",
    "password": "Demo1234!",
    "full_name": "Demo Admin",
    "tenant": {"name": "Demo Corp", "nif": "B12345678"}
})

print("2. Getting Token...")
res = q("http://127.0.0.1:8080/api/v1/auth/login", {
    "email": "demo@automatizapyme.com",
    "password": "Demo1234!"
})

if res and "access_token" in res:
    token = res["access_token"]
    
    def post_task(domain, intent):
        req = urllib.request.Request("http://127.0.0.1:8080/api/v1/tasks/", data=json.dumps({"domain": domain, "user_intent": intent}).encode('utf-8'), headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'})
        try:
            with urllib.request.urlopen(req) as response:
                print("Task created:", domain)
        except Exception as e:
            print("Task error:", getattr(e, 'read', lambda: b'()')().decode('utf-8'))
    
    tasks_to_create = [
        ("billing", "Necesito facturar 5500 euros a la empresa cliente 'Tech Solutions SL' con NIF B60249562 por los servicios de consultoría informática del mes de octubre. El impuesto será del 21%."),
        ("banking", "Por favor, dame un resumen de los últimos movimientos bancarios de la cuenta principal."),
        ("compliance", "¿Podrías indicarme cuándo es el próximo plazo para presentar el modelo 303 de hacienda y si hay alguna novedad reciente en el BOE que afecte a autónomos?")
    ]
    
    for t in tasks_to_create:
        post_task(t[0], t[1])
        
    print("All tasks submitted!")
