from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from db.config import settings

_engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession]


async def init_engine() -> None:
    global _engine, async_session_factory
    _engine = create_async_engine(
        settings.database_url,
        pool_size=10,
        max_overflow=5,
        pool_pre_ping=True,
        echo=False,
    )
    async_session_factory = async_sessionmaker(
        _engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


async def dispose_engine() -> None:
    if _engine is not None:
        await _engine.dispose()


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("DB engine not initialised — call init_engine() first")
    return _engine
