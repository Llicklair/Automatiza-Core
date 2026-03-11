import asyncio

from app.db.base import engine
from app.db.models.models import Base


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tablas sincronizadas satisfactoriamente.")

if __name__ == "__main__":
    asyncio.run(init_models())
