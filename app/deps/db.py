"""
Database session dependency injection utilities.

Provides production-ready async database session management with proper
lifespan handling and error management.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def _get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session with proper error handling.
    
    Ensures session is properly closed even if exceptions occur.
    
    Yields:
        AsyncSession: Database session
        
    Raises:
        HTTPException: If database connection fails
    """
    session = None
    try:
        async with AsyncSessionLocal() as session:
            yield session
            # Commit if no exception occurred
            await session.commit()
    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}", exc_info=True)
        if session:
            await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database operation failed. Please try again later.",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error in database session: {str(e)}", exc_info=True)
        if session:
            await session.rollback()
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again later.",
        ) from e
    finally:
        # Ensure session is closed
        if session:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing session: {str(e)}", exc_info=True)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database session.
    
    Provides a database session with:
    - Automatic transaction management (commit on success, rollback on error)
    - Proper session cleanup
    - Production-ready error handling
    - Connection pooling via AsyncSessionLocal
    
    Usage:
        ```python
        from fastapi import Depends
        from app.deps.db import get_db_session
        
        @router.get("/items")
        async def list_items(
            session: AsyncSession = Depends(get_db_session)
        ):
            # Use session for database operations
            result = await session.execute(select(Item))
            return result.scalars().all()
        ```
    
    Yields:
        AsyncSession: Database session ready for use
        
    Raises:
        HTTPException: If database connection fails (500 status)
    """
    async with _get_db_session_context() as session:
        yield session

