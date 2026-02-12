"""FastAPI dependencies for database and project context."""

from app.deps.db import get_db_session
from app.deps.project import (
    get_project_id_from_header,
    get_project_id_from_path,
    get_project_id_from_query,
)

__all__ = [
    "get_db_session",
    "get_project_id_from_header",
    "get_project_id_from_query",
    "get_project_id_from_path",
]

