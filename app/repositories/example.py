"""
Example repository implementation.

This file demonstrates how to create a repository for a project-scoped entity.
It's provided as a reference and can be deleted once you create your own repositories.
"""

import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped

from app.repositories.base import BaseRepository


# Example: RFQ Repository
# Replace this with your actual model once you have it defined
class ExampleModel:
    """Placeholder for actual model - replace with your model class."""

    id: Mapped[uuid.UUID]
    project_id: Mapped[uuid.UUID]
    title: Mapped[str]
    status: Mapped[str]
    created_at: Mapped


class RFQRepository(BaseRepository[ExampleModel]):
    """
    Example repository for RFQ entities.

    This demonstrates how to extend BaseRepository for a specific entity.
    You can add entity-specific methods here.

    Usage:
        ```python
        from app.deps.db import get_db_session
        from app.deps.project import get_current_project_id

        async def some_endpoint(
            session: AsyncSession = Depends(get_db_session),
            project_id: uuid.UUID = Depends(get_current_project_id)
        ):
            repo = RFQRepository(session, project_id)
            rfqs = await repo.list(status='published')
        ```
    """

    def __init__(self, session: AsyncSession, project_id: uuid.UUID):
        super().__init__(session, project_id, ExampleModel)

    # Example: Add entity-specific query methods
    async def get_by_status(self, status: str) -> list[ExampleModel]:
        """
        Get all RFQs with a specific status.

        Args:
            status: RFQ status to filter by

        Returns:
            List of RFQs with the specified status
        """
        return await self.list(status=status)

    async def get_published(self) -> list[ExampleModel]:
        """Get all published RFQs."""
        return await self.get_by_status("published")

    async def get_draft(self) -> list[ExampleModel]:
        """Get all draft RFQs."""
        return await self.get_by_status("draft")
