from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager

from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=NullPool,  # Neon.tech serverless — sin pool persistente
    echo=settings.APP_ENV == "development",
    connect_args={"ssl": "require"},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@asynccontextmanager
async def get_db_context():
    async with AsyncSessionLocal() as session:
        yield session


async def set_tenant(session: AsyncSession, tenant_id: str) -> None:
    """Establece el tenant activo para RLS en la sesión."""
    await session.execute(
        __import__("sqlalchemy").text("SET LOCAL app.tenant_id = :tid"),
        {"tid": str(tenant_id)},
    )
