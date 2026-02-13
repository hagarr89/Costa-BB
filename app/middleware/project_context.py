"""
Middleware for setting project context in request.state.

This middleware extracts project_id from headers/query/path and sets
it in request.state.project_context for use by dependencies.
"""

import logging
import uuid
from typing import Callable

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.deps.context import ProjectContext

logger = logging.getLogger(__name__)


class ProjectContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts project context and sets it in request.state.
    
    This middleware looks for project_id in the following order:
    1. X-Project-ID header
    2. project_id query parameter
    3. project_id path parameter (if route includes it)
    
    The extracted project_id is stored in request.state.project_context
    as a ProjectContext instance.
    
    Usage:
        ```python
        from app.middleware.project_context import ProjectContextMiddleware
        
        app.add_middleware(ProjectContextMiddleware)
        ```
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and set project context.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from next handler
            
        Raises:
            HTTPException: If project_id is required but missing
        """
        project_id = None
        
        # Try to extract project_id from various sources
        # 1. Check X-Project-ID header
        x_project_id = request.headers.get("X-Project-ID")
        if x_project_id:
            try:
                project_id = uuid.UUID(x_project_id)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid project ID format in header: {x_project_id}",
                )
        
        # 2. Check query parameter
        if not project_id:
            query_project_id = request.query_params.get("project_id")
            if query_project_id:
                try:
                    project_id = uuid.UUID(query_project_id)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid project ID format in query: {query_project_id}",
                    )
        
        # 3. Check path parameter (if available)
        if not project_id and "project_id" in request.path_params:
            path_project_id = request.path_params.get("project_id")
            if path_project_id:
                try:
                    project_id = uuid.UUID(path_project_id)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid project ID format in path: {path_project_id}",
                    )
        
        # Set project context in request.state
        if project_id:
            request.state.project_context = ProjectContext(project_id=project_id)
        else:
            # If project_id is not found, you can either:
            # 1. Set a default (not recommended for multi-tenant)
            # 2. Leave it unset and let dependencies handle the error
            # 3. Only set for specific routes (recommended)
            # For now, we'll leave it unset and let dependencies handle it
            pass
        
        response = await call_next(request)
        return response


def create_project_context_middleware(
    require_project_id: bool = True,
    default_project_id: uuid.UUID | None = None,
) -> type[BaseHTTPMiddleware]:
    """
    Create a project context middleware with custom configuration.
    
    Args:
        require_project_id: If True, raise 400 error when project_id is missing
        default_project_id: Optional default project_id to use if not found
        
    Returns:
        Middleware class configured with the specified options
        
    Example:
        ```python
        # Require project_id (strict multi-tenant)
        middleware = create_project_context_middleware(require_project_id=True)
        app.add_middleware(middleware)
        
        # Allow optional project_id with default
        middleware = create_project_context_middleware(
            require_project_id=False,
            default_project_id=uuid.UUID("00000000-0000-0000-0000-000000000000")
        )
        app.add_middleware(middleware)
        ```
    """
    class ConfiguredProjectContextMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Callable) -> Response:
            project_id = None
            
            # Try to extract project_id from various sources
            x_project_id = request.headers.get("X-Project-ID")
            if x_project_id:
                try:
                    project_id = uuid.UUID(x_project_id)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid project ID format in header: {x_project_id}",
                    )
            
            if not project_id:
                query_project_id = request.query_params.get("project_id")
                if query_project_id:
                    try:
                        project_id = uuid.UUID(query_project_id)
                    except ValueError:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid project ID format in query: {query_project_id}",
                        )
            
            if not project_id and "project_id" in request.path_params:
                path_project_id = request.path_params.get("project_id")
                if path_project_id:
                    try:
                        project_id = uuid.UUID(path_project_id)
                    except ValueError:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Invalid project ID format in path: {path_project_id}",
                        )
            
            # Handle missing project_id
            if not project_id:
                if require_project_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Project ID is required. Provide it via X-Project-ID header, "
                               "project_id query parameter, or project_id path parameter.",
                    )
                elif default_project_id:
                    project_id = default_project_id
            
            # Set project context
            if project_id:
                request.state.project_context = ProjectContext(project_id=project_id)
            
            response = await call_next(request)
            return response
    
    return ConfiguredProjectContextMiddleware
