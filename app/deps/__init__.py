"""FastAPI dependencies for database, project context, and repository factories."""

from app.deps.context import ProjectContext, get_project_context, get_project_id
from app.deps.db import get_db_session
from app.deps.project import (
    get_project_id_from_header,
    get_project_id_from_path,
    get_project_id_from_query,
)
from app.deps.repository import (
    create_repository_dependency,
    get_repository,
    get_repository_factory,
)

__all__ = [
    # Database
    "get_db_session",
    # Project context
    "ProjectContext",
    "get_project_context",
    "get_project_id",
    # Project ID extraction (legacy)
    "get_project_id_from_header",
    "get_project_id_from_query",
    "get_project_id_from_path",
    # Repository factories
    "get_repository_factory",
    "create_repository_dependency",
    "get_repository",
]

