"""
Dependencies for project-scoped operations.

These dependencies help extract and validate project_id from requests
for use with multi-tenant repositories.
"""

import uuid
from typing import Annotated
from fastapi import Request

from fastapi import Header, HTTPException, Query


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
    """
    Extract project_id from query parameter.

    Alternative to header-based approach, useful for GET requests
    where project context is passed as query parameter.

    Args:
        project_id: Project ID from query parameter

    Returns:
        UUID of the project

    Raises:
        HTTPException: If parameter is missing or invalid

    Example:
        ```python
        @router.get("/rfqs")
        async def list_rfqs(
            project_id: uuid.UUID = Depends(get_project_id_from_query)
        ):
            # Use project_id with repository
        ```
    """
    if not project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id query parameter is required",
        )

    try:
        return uuid.UUID(project_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid project ID format: {project_id}",
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
