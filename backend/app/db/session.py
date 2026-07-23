"""Async SQLAlchemy engine and session helpers."""

import ssl
from collections.abc import AsyncGenerator

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import Settings, get_settings

# Stable constraint names for Alembic autogenerate diffs.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def connect_args(settings: Settings) -> dict[str, object]:
    """Connect args for asyncpg (statement timeout + optional SSL).

    ``DB_SSL_REQUIRE`` matches libpq ``sslmode=require``: encrypt the connection
    without verifying the server certificate. Managed providers such as Railway
    Postgres use a self-signed chain that fails default verification.
    """
    args: dict[str, object] = {
        "server_settings": {
            "statement_timeout": str(settings.db_statement_timeout_ms),
        }
    }
    if settings.db_ssl_require:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        args["ssl"] = context
    return args


def create_engine(settings: Settings | None = None) -> AsyncEngine:
    resolved = settings or get_settings()
    return create_async_engine(
        resolved.database_url,
        pool_pre_ping=True,
        pool_size=resolved.db_pool_size,
        max_overflow=resolved.db_max_overflow,
        pool_timeout=resolved.db_pool_timeout_seconds,
        pool_recycle=resolved.db_pool_recycle_seconds,
        connect_args=connect_args(resolved),
    )


engine: AsyncEngine = create_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
