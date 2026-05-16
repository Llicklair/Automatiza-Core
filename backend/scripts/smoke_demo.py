import asyncio
from datetime import datetime, timedelta

import httpx

BASE_URL = "http://localhost:8080/api/v1"


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1) Registro tenant + usuario admin demo (idempotente)
        print("== Registro demo@automatizapyme.com ==")
        register_payload = {
            "email": "demo@automatizapyme.com",
            "password": "Demo1234!",
            "full_name": "Demo Admin",
            "tenant": {"name": "Demo Corp", "nif": "B12345678"},
        }
        r = await client.post("/auth/register", json=register_payload)
        print("register status:", r.status_code)
        if r.status_code not in (201, 400):
            print("register response:", r.text)

        # 2) Login
        print("\n== Login ==")
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

        # 3) Crear cliente
        print("\n== Crear cliente ==")
        client_payload = {
            "nif": "B60249562",
            "name": "Tech Solutions SL",
            "email": "facturacion@techsolutions.test",
            "address": "Calle Tecnología 123, Barcelona",
            "city": "Barcelona",
            "postal_code": "08001",
            "client_type": "customer",
        }
        r = await client.post("/clients", json=client_payload, headers=headers)
        print("create client status:", r.status_code)
        if r.status_code != 201:
            print("create client response:", r.text)
            return
        created_client = r.json()
        client_id = created_client["id"]
        print("client id:", client_id)

        # 4) Crear producto
        print("\n== Crear producto ==")
        product_payload = {
            "item_type": "service",
            "sku": "CONSULT-SEO",
            "name": "Consultoría SEO mensual",
            "description": "Servicio de consultoría SEO para PYMEs",
            "price": 2000.0,
            "tax_percentage": 21.0,
        }
        r = await client.post("/products", json=product_payload, headers=headers)
        print("create product status:", r.status_code)
        if r.status_code != 201:
            print("create product response:", r.text)
            return
        product_id = r.json()["id"]
        print("product id:", product_id)

        # 5) Crear factura con una línea
        print("\n== Crear factura ==")
        today = datetime.utcnow()
        invoice_payload = {
            "invoice_number": None,
            "date": today.isoformat(),
            "due_date": (today + timedelta(days=30)).isoformat(),
            "status": "draft",
            "invoice_type": "issued",
            "notes": "Factura de prueba creada por smoke_demo.py",
            "terms": "Pago a 30 días",
            "lines": [
                {
                    "product_id": product_id,
                    "description": "Consultoría SEO noviembre 2023",
                    "quantity": 1,
                    "unit_price": 2400.0,
                    "discount_percentage": 0.0,
                    "tax_percentage": 21.0,
                }
            ],
        }
        r = await client.post(
            f"/clients/{client_id}/invoices", json=invoice_payload, headers=headers
        )
        print("create invoice status:", r.status_code)
        if r.status_code not in (200, 201):
            print("create invoice response:", r.text)
            return
        invoice = r.json()
        invoice_id = invoice["id"]
        print("invoice id:", invoice_id, "total:", invoice["amount_total"])

        # 6) Descargar PDF de factura
        print("\n== Descargar PDF de factura ==")
        r = await client.get(f"/invoices/{invoice_id}/pdf", headers=headers)
        print("invoice pdf status:", r.status_code, "bytes:", len(r.content))

        # 7) Crear empleado
        print("\n== Crear empleado ==")
        employee_payload = {
            "nif": "12345678A",
            "name": "Juan Pérez",
            "department": "Operaciones",
            "role": "Consultor",
            "base_salary": 2500.0,
            "status": "active",
        }
        r = await client.post("/hr/employees", json=employee_payload, headers=headers)
        print("create employee status:", r.status_code)
        if r.status_code != 201:
            print("create employee response:", r.text)
            return
        employee_id = r.json()["id"]
        print("employee id:", employee_id)

        # 8) Crear nómina en estado draft
        print("\n== Crear nómina draft ==")
        payroll_payload = {
            "employee_id": employee_id,
            "period_start": datetime(today.year, today.month, 1).isoformat(),
            "period_end": datetime(today.year, today.month, 28).isoformat(),
            "issue_date": today.isoformat(),
            "base_salary": 2500.0,
            "deductions": 0.0,
            "net_salary": 2000.0,
            "status": "draft",
        }
        r = await client.post("/hr/payrolls", json=payroll_payload, headers=headers)
        print("create payroll status:", r.status_code)
        if r.status_code != 201:
            print("create payroll response:", r.text)
            return
        payroll = r.json()
        payroll_id = payroll["id"]
        print("payroll id:", payroll_id, "status:", payroll["status"])

        # 9) Aprobar nómina (genera PDF y TenantDocument en background)
        print("\n== Aprobar nómina y generar PDF en TenantDocument ==")
        r = await client.post(f"/hr/payrolls/{payroll_id}/approve", headers=headers)
        print("approve payroll status:", r.status_code)
        if r.status_code != 200:
            print("approve payroll response:", r.text)

        # 10) Descargar PDF directo de nómina
        print("\n== Descargar PDF de nómina ==")
        r = await client.get(f"/hr/payrolls/{payroll_id}/pdf", headers=headers)
        print("payroll pdf status:", r.status_code, "bytes:", len(r.content))

        # 11) Listar documentos del tenant (incluye PDFs guardados en disco)
        print("\n== Listar documentos (TenantDocument) ==")
        r = await client.get("/documents", headers=headers)
        print("documents status:", r.status_code)
        if r.status_code == 200:
            docs = r.json()
            print("num documentos:", len(docs))
            for d in docs:
                print("-", d.get("category"), ":", d.get("file_name"))
        else:
            print("documents response:", r.text)


if __name__ == "__main__":
    asyncio.run(main())

