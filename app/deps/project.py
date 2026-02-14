"""
Dependencies for project-scoped operations.

Provides project_id extraction from header/query/path and project context
from request.state (set by middleware) for multi-tenant repositories.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Header, HTTPException, Query, Request

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """
    Project context extracted from request state.

    Set by middleware; provides project-scoped information for multi-tenant operations.

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
    Extract project context from request.state (set by middleware).

    Fails with 400 when project_id was not provided; 500 only on invalid server state.

    Raises:
        HTTPException: 400 if project context missing, 500 if invalid configuration.
    """
    try:
        if not hasattr(request.state, "project_context"):
            logger.warning(
                "Project context not found in request.state. "
                "Ensure middleware sets request.state.project_context"
            )
            raise HTTPException(
                status_code=400,
                detail="Project ID is required. Provide it via X-Project-ID header, "
                       "project_id query parameter, or project_id path parameter.",
            )
        context = request.state.project_context
        if not isinstance(context, ProjectContext):
            logger.error(
                "Invalid project context type: %s. Expected ProjectContext instance.",
                type(context).__name__,
            )
            raise HTTPException(
                status_code=500,
                detail="Invalid project context configuration.",
            )
        if context.project_id is None:
            logger.error("Project context has None project_id")
            raise HTTPException(
                status_code=400,
                detail="Project ID is required but was not provided.",
            )
        return context
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error extracting project context: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to extract project context.",
        ) from e


async def get_project_id(request: Request) -> uuid.UUID:
    """
    Extract project_id from request.state (convenience wrapper around get_project_context).
    """
    context = await get_project_context(request)
    return context.project_id


async def get_project_id_from_header(
    x_project_id: Annotated[str | None, Header(alias="X-Project-ID")] = None,
) -> uuid.UUID:
    """
    Extract project_id from X-Project-ID header.

    This is a common pattern for multi-tenant APIs where the project
    context is provided via HTTP header.

    Args:
        x_project_id: Project ID from X-Project-ID header

    Returns:
        UUID of the project

    Raises:
        HTTPException: If header is missing or invalid

    Example:
        ```python
        @router.get("/rfqs")
        async def list_rfqs(
            project_id: uuid.UUID = Depends(get_project_id_from_header)
        ):
            # Use project_id with repository
        ```
    """
    if not x_project_id:
        raise HTTPException(
            status_code=400,
            detail="X-Project-ID header is required",
        )

    try:
        return uuid.UUID(x_project_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid project ID format: {x_project_id}",
        )


async def get_project_id_from_query(request: Request) -> uuid.UUID:
    values = request.query_params.getlist("project_id")

    if not values or not values[0]:
        raise HTTPException(
            status_code=400,
            detail="project_id query parameter is required",
        )

    raw = values[0]

    try:
        return uuid.UUID(raw)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid project ID format: {raw}",
        )


async def get_project_id_from_path(
    project_id: str,
) -> uuid.UUID:
    """
    Extract and validate project_id from path parameter.

    Use this when project_id is part of the URL path.

    Args:
        project_id: Project ID from path parameter

    Returns:
        UUID of the project

    Raises:
        HTTPException: If parameter is invalid

    Example:
        ```python
        @router.get("/projects/{project_id}/rfqs")
        async def list_rfqs(
            project_id: uuid.UUID = Depends(get_project_id_from_path)
        ):
            # Use project_id with repository
        ```
    """
    try:
        return uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid project ID format: {project_id}",
        )
