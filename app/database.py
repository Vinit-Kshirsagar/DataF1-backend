from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os
from dotenv import load_dotenv

load_dotenv()


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory = None


def _get_engine():
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL", "")
        # Force asyncpg driver regardless of what's in the URL
        url = url.replace("postgresql://", "postgresql+asyncpg://")
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
        _engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db():  # type: ignore
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
