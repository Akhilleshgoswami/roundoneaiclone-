"""Async SQLAlchemy engine and request-scoped database sessions."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from voiceai.core.config import get_settings

settings = get_settings()
# NullPool avoids asyncpg connections sticking to a closed pytest event loop.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    poolclass=NullPool,
)
SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped database session."""

    async with SessionFactory() as session:
        yield session


# Keep the misspelled alias so existing route imports continue to work.
get_db_sassion = get_db_session
