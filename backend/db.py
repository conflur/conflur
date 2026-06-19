from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager

from config import settings

# La app usa el rol sin BYPASSRLS (conflur_app). Solo las migraciones usan el owner.
# Si APP_DATABASE_URL no está seteado, cae al owner (aceptable solo en local).
RUNTIME_DATABASE_URL = settings.APP_DATABASE_URL or settings.DATABASE_URL

engine = create_async_engine(
    RUNTIME_DATABASE_URL,
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


async def set_tenant(session: AsyncSession, tenant_id: str, user_id: str | None = None) -> None:
    """
    Establece el contexto de seguridad de la request en la sesión:

    - ``app.tenant_id`` → consultorio activo. El RLS lo usa para aislar entre
      consultorios (última línea de defensa).
    - ``app.user_id``   → usuario autenticado. Disponible para la capa de
      autorización dentro del consultorio (visibilidad clínica vía
      patient_access) y para futuras políticas RLS más finas.

    Se setea con SET LOCAL, así que aplica solo a la transacción/sesión actual.
    """
    from sqlalchemy import text

    # set_config(setting, value, is_local=true) — equivale a SET LOCAL pero acepta
    # parámetros bind (SET LOCAL no los acepta). is_local=true ⇒ alcance transacción.
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
    if user_id is not None:
        await session.execute(
            text("SELECT set_config('app.user_id', :uid, true)"),
            {"uid": str(user_id)},
        )
