import httpx
import asyncio

async def test():
    async with httpx.AsyncClient() as client:
        res = await client.post("http://127.0.0.1:8080/api/v1/auth/register", json={
            "email": "demo@automatizapyme.com",
            "password": "Demo1234!",
            "full_name": "Demo Admin",
            "tenant": {
                "name": "Demo Corp",
                "nif": "B12345678"
            }
        })
        print(res.status_code, res.text)

asyncio.run(test())
