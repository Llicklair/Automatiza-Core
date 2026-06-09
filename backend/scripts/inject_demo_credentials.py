import asyncio

# Necesitamos path lib para importar la app 
import os
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantIntegration, User
from app.services.encryption import encrypt_credentials


async def inject_demo_credentials():
    print("Inyectando credenciales DEMO a nivel de base de datos...")
    async with AsyncSessionLocal() as db:
        # 1. Encontrar el usuario demo y su tenant
        result = await db.execute(select(User).where(User.email == "demo@automatizacore.com"))
        user = result.scalar_one_or_none()
        if not user:
            print("❌ Usuario demo@automatizacore.com no encontrado.")
            return

        tenant_id = user.tenant_id

        # 2. Add PSD2 / Nordigen Mock
        encrypted_psd2 = encrypt_credentials({"secret_id": "DEMO_PSD2_ID", "secret_key": "dummy"})
        result = await db.execute(select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == "psd2"
        ))
        existing_psd2 = result.scalar_one_or_none()
        if existing_psd2:
            existing_psd2.encrypted_credentials = encrypted_psd2
            existing_psd2.is_active = True
        else:
            db.add(TenantIntegration(
                tenant_id=tenant_id,
                integration_type="psd2",
                encrypted_credentials=encrypted_psd2,
                is_active=True,
            ))

        await db.commit()
        print("✅ Credenciales de integración DEMO inyectadas exitosamente en la BD.")

if __name__ == "__main__":
    asyncio.run(inject_demo_credentials())
