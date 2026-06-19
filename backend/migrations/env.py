import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from models import Base  # noqa: E402
target_metadata = Base.metadata

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL:
    # asyncpg requires postgresql+asyncpg:// scheme
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    # asyncpg does not accept sslmode/channel_binding as query params — strip them
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    parsed = urlparse(DATABASE_URL)
    params = {k: v for k, v in parse_qs(parsed.query).items()
              if k not in ("sslmode", "channel_binding")}
    clean = parsed._replace(query=urlencode({k: v[0] for k, v in params.items()}))
    DATABASE_URL = urlunparse(clean)
    config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args={"ssl": "require"},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
