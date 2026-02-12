from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session to be used as a FastAPI dependency."""
    async with AsyncSessionLocal() as session:
        yield session

