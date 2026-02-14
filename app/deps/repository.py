"""
Repository factory dependency injection utilities.

Provides factory functions for creating repositories with automatic
project_id injection from request context.
"""

import logging
import uuid
from typing import Callable, Generic, Type, TypeVar

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.project import ProjectContext, get_project_context
from app.deps.db import get_db_session
from app.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# Type variable for repository types
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


def get_repository_factory(
    repository_class: Type[RepositoryType],
) -> Callable[[AsyncSession, ProjectContext], RepositoryType]:
    """
    Create a repository factory function for a specific repository class.
    
    This factory automatically injects project_id from the project context,
    reducing boilerplate in route handlers.
    
    Args:
        repository_class: Repository class that extends BaseRepository
        
    Returns:
        Factory function that creates repository instances
        
    Example:
        ```python
        from app.repositories.rfq import RFQRepository
        from app.deps.repository import get_repository_factory
        
        get_rfq_repository = get_repository_factory(RFQRepository)
        
        @router.get("/rfqs")
        async def list_rfqs(
            repo: RFQRepository = Depends(get_rfq_repository)
        ):
            return await repo.list()
        ```
    """
    def factory(
        session: AsyncSession = Depends(get_db_session),
        context: ProjectContext = Depends(get_project_context),
    ) -> RepositoryType:
        """
        Factory function that creates a repository instance.
        
        Args:
            session: Database session (injected)
            context: Project context (injected)
            
        Returns:
            Repository instance with project_id automatically set
        """
        try:
            return repository_class(session, context.project_id)
        except ValueError as e:
            logger.error(f"Failed to create repository {repository_class.__name__}: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize repository: {str(e)}",
            ) from e
        except Exception as e:
            logger.error(
                f"Unexpected error creating repository {repository_class.__name__}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to create repository instance.",
            ) from e
    
    return factory


def create_repository_dependency(
    repository_class: Type[RepositoryType],
) -> Callable[[AsyncSession, ProjectContext], RepositoryType]:
    """
    Create a FastAPI dependency for a repository class.
    
    This is an alias for get_repository_factory that provides a more
    descriptive name for dependency creation.
    
    Args:
        repository_class: Repository class that extends BaseRepository
        
    Returns:
        Dependency function for FastAPI
        
    Example:
        ```python
        from app.repositories.rfq import RFQRepository
        from app.deps.repository import create_repository_dependency
        
        get_rfq_repository = create_repository_dependency(RFQRepository)
        
        @router.get("/rfqs")
        async def list_rfqs(
            rfq_repo: RFQRepository = Depends(get_rfq_repository)
        ):
            return await rfq_repo.list()
        ```
    """
    return get_repository_factory(repository_class)


# Convenience function for common pattern
def get_repository(
    repository_class: Type[RepositoryType],
    session: AsyncSession,
    project_id: uuid.UUID,
) -> RepositoryType:
    """
    Create a repository instance directly (for use outside FastAPI dependencies).
    
    This function is useful for:
    - Background jobs
    - Service layer code
    - Testing
    
    Args:
        repository_class: Repository class that extends BaseRepository
        session: Database session
        project_id: Project ID for tenant isolation
        
    Returns:
        Repository instance
        
    Raises:
        ValueError: If repository cannot be created
        HTTPException: If unexpected error occurs
        
    Example:
        ```python
        from app.repositories.rfq import RFQRepository
        from app.deps.repository import get_repository
        
        async def background_task(session: AsyncSession, project_id: uuid.UUID):
            repo = get_repository(RFQRepository, session, project_id)
            rfqs = await repo.list()
        ```
    """
    try:
        return repository_class(session, project_id)
    except ValueError as e:
        logger.error(f"Failed to create repository {repository_class.__name__}: {str(e)}")
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error creating repository {repository_class.__name__}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to create repository instance.",
        ) from e
