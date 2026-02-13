"""
Project context dependency injection utilities.

Provides project context extraction from request.state with proper
validation and error handling.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """
    Project context extracted from request state.
    
    This context is typically set by middleware or earlier dependencies
    and provides project-scoped information for multi-tenant operations.
    
    Attributes:
        project_id: UUID of the current project (tenant boundary)
        user_id: Optional UUID of the current user
        organization_id: Optional UUID of the current organization
    """
    
    project_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    
    def __post_init__(self):
        """Validate project_id is not None."""
        if self.project_id is None:
            raise ValueError("project_id cannot be None")


async def get_project_context(request: Request) -> ProjectContext:
    """
    Extract project context from request.state.
    
    This dependency expects that project context has been set in request.state
    by middleware or an earlier dependency. The context should be stored as
    request.state.project_context.
    
    Usage:
        ```python
        from fastapi import Depends, Request
        from app.deps.context import get_project_context
        
        @router.get("/items")
        async def list_items(
            context: ProjectContext = Depends(get_project_context)
        ):
            # Use context.project_id for repository operations
            repo = ItemRepository(session, context.project_id)
            return await repo.list()
        ```
    
    Args:
        request: FastAPI request object
        
    Returns:
        ProjectContext: Project context with project_id and optional metadata
        
    Raises:
        HTTPException: If project context is missing or invalid (400/500 status)
    """
    try:
        # Check if project_context exists in request.state
        if not hasattr(request.state, "project_context"):
            logger.warning(
                "Project context not found in request.state. "
                "Ensure middleware sets request.state.project_context"
            )
            raise HTTPException(
                status_code=500,
                detail="Project context not available. Please ensure middleware is configured.",
            )
        
        context = request.state.project_context
        
        # Validate context is ProjectContext instance
        if not isinstance(context, ProjectContext):
            logger.error(
                f"Invalid project context type: {type(context)}. "
                "Expected ProjectContext instance."
            )
            raise HTTPException(
                status_code=500,
                detail="Invalid project context configuration.",
            )
        
        # Validate project_id is present
        if context.project_id is None:
            logger.error("Project context has None project_id")
            raise HTTPException(
                status_code=400,
                detail="Project ID is required but was not provided.",
            )
        
        return context
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error extracting project context: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to extract project context.",
        ) from e


async def get_project_id(request: Request) -> uuid.UUID:
    """
    Extract project_id from request.state (convenience function).
    
    This is a convenience wrapper around get_project_context that only
    returns the project_id UUID.
    
    Usage:
        ```python
        from fastapi import Depends
        from app.deps.context import get_project_id
        
        @router.get("/items")
        async def list_items(
            project_id: uuid.UUID = Depends(get_project_id)
        ):
            repo = ItemRepository(session, project_id)
            return await repo.list()
        ```
    
    Args:
        request: FastAPI request object
        
    Returns:
        uuid.UUID: Project ID
        
    Raises:
        HTTPException: If project context is missing or invalid
    """
    context = await get_project_context(request)
    return context.project_id
