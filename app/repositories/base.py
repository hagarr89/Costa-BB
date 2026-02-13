"""
BaseRepository for multi-tenant SaaS system.

This repository enforces strict project-level isolation by:
- Automatically filtering all queries by project_id
- Automatically injecting project_id on create operations
- Preventing bypassing of tenant filtering
- Supporting soft delete for models with deleted_at field
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Generic, Optional, Type, TypeVar

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.db.base import Base

# Type variable for SQLAlchemy models
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Base repository for multi-tenant data access.

    This repository enforces strict project-level isolation. All operations
    are automatically scoped to the provided project_id.

    Attributes:
        session: Async database session
        project_id: UUID of the project (tenant boundary)
        model: SQLAlchemy model class

    Example:
        ```python
        class RFQRepository(BaseRepository[RFQ]):
            def __init__(self, session: AsyncSession, project_id: uuid.UUID):
                super().__init__(session, project_id, RFQ)
        ```
    """

    def __init__(
        self,
        session: AsyncSession,
        project_id: uuid.UUID,
        model: Type[ModelType],
    ):
        """
        Initialize repository with session and project context.

        Args:
            session: Async database session
            project_id: UUID of the project (tenant boundary)
            model: SQLAlchemy model class

        Raises:
            ValueError: If project_id is None or model doesn't have project_id attribute
        """
        if project_id is None:
            raise ValueError("project_id is required and cannot be None")

        if not hasattr(model, "project_id"):
            raise ValueError(
                f"Model {model.__name__} must have a 'project_id' attribute "
                "for multi-tenant isolation"
            )

        self.session = session
        self.project_id = project_id
        self.model = model
        self._has_soft_delete = hasattr(model, "deleted_at")

    def _enforce_project_filter(self, query: Any) -> Any:
        """
        Enforce project_id filtering on a query.

        This method ensures that all queries are scoped to the current project.
        It's called internally to prevent accidental cross-project data access.

        Args:
            query: SQLAlchemy select/update/delete statement

        Returns:
            Query with project_id filter applied
        """
        return query.where(self.model.project_id == self.project_id)

    def _check_project_id(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Ensure project_id is present and matches repository's project_id.

        This prevents bypassing tenant filtering by explicitly setting
        a different project_id in create/update operations.

        Args:
            data: Dictionary of model attributes

        Returns:
            Dictionary with project_id enforced

        Raises:
            ValueError: If project_id is provided and doesn't match repository's project_id
        """
        if "project_id" in data:
            if data["project_id"] != self.project_id:
                raise ValueError(
                    f"Cannot set project_id to {data['project_id']}. "
                    f"This repository is scoped to project {self.project_id}"
                )
        else:
            data["project_id"] = self.project_id

        return data

    def _apply_soft_delete_filter(self, query: Any) -> Any:
        """
        Apply soft delete filter if model supports it.

        Args:
            query: SQLAlchemy query

        Returns:
            Query with soft delete filter applied (if applicable)
        """
        if self._has_soft_delete:
            return query.where(self.model.deleted_at.is_(None))
        return query

    async def get_by_id(
        self,
        id: uuid.UUID,
        include_deleted: bool = False,
    ) -> Optional[ModelType]:
        """
        Get a single record by ID within the current project.

        Args:
            id: UUID of the record
            include_deleted: If True, include soft-deleted records (only if model supports it)

        Returns:
            Model instance or None if not found

        Example:
            ```python
            rfq = await repository.get_by_id(rfq_id)
            ```
        """
        query = select(self.model).where(self.model.id == id)

        # Enforce project filtering
        query = self._enforce_project_filter(query)

        # Apply soft delete filter unless explicitly including deleted
        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
        order_by: Optional[Any] = None,
        **filters: Any,
    ) -> list[ModelType]:
        """
        List records within the current project with optional filtering.

        Args:
            skip: Number of records to skip (for pagination)
            limit: Maximum number of records to return
            include_deleted: If True, include soft-deleted records (only if model supports it)
            order_by: Column(s) to order by (defaults to created_at DESC)
            **filters: Additional filters to apply (e.g., status='active')

        Returns:
            List of model instances

        Example:
            ```python
            # Get active RFQs
            rfqs = await repository.list(status='published', limit=50)

            # Get with custom ordering
            rfqs = await repository.list(order_by=RFQ.created_at.desc())
            ```
        """
        query = select(self.model)

        # Enforce project filtering (mandatory)
        query = self._enforce_project_filter(query)

        # Apply additional filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        # Apply soft delete filter unless explicitly including deleted
        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        # Apply ordering
        if order_by is not None:
            query = query.order_by(order_by)
        elif hasattr(self.model, "created_at"):
            query = query.order_by(self.model.created_at.desc())

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, **data: Any) -> ModelType:
        """
        Create a new record within the current project.

        The project_id is automatically injected and cannot be overridden.

        Args:
            **data: Model attributes (project_id will be automatically set)

        Returns:
            Created model instance

        Raises:
            ValueError: If project_id is provided and doesn't match repository's project_id

        Example:
            ```python
            rfq = await repository.create(
                title="New RFQ",
                description="Description",
                created_by_user_id=user_id
            )
            ```
        """
        # Enforce project_id
        data = self._check_project_id(data)

        # Create instance
        instance = self.model(**data)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)

        return instance

    async def update(
        self,
        id: uuid.UUID,
        **data: Any,
    ) -> Optional[ModelType]:
        """
        Update a record by ID within the current project.

        The project_id cannot be changed via this method.

        Args:
            id: UUID of the record to update
            **data: Attributes to update (project_id will be ignored/validated)

        Returns:
            Updated model instance or None if not found

        Raises:
            ValueError: If project_id is provided and doesn't match repository's project_id

        Example:
            ```python
            updated = await repository.update(
                rfq_id,
                status='published',
                published_at=datetime.utcnow()
            )
            ```
        """
        # Prevent project_id changes
        if "project_id" in data:
            if data["project_id"] != self.project_id:
                raise ValueError(
                    f"Cannot change project_id. Record belongs to project {self.project_id}"
                )
            # Remove project_id from update data as it shouldn't change
            del data["project_id"]

        # Build update query with project enforcement
        query = (
            update(self.model)
            .where(and_(self.model.id == id, self.model.project_id == self.project_id))
            .values(**data)
            .returning(self.model)
        )

        # Apply soft delete filter to prevent updating deleted records
        if self._has_soft_delete:
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.session.execute(query)
        instance = result.scalar_one_or_none()

        if instance:
            await self.session.refresh(instance)

        return instance

    async def soft_delete(self, id: uuid.UUID) -> Optional[ModelType]:
        """
        Soft delete a record by ID within the current project.

        This method only works if the model has a `deleted_at` field.
        For models without soft delete support, use `delete` instead.

        Args:
            id: UUID of the record to soft delete

        Returns:
            Soft-deleted model instance or None if not found

        Raises:
            AttributeError: If model doesn't support soft delete (no deleted_at field)

        Example:
            ```python
            deleted = await repository.soft_delete(rfq_id)
            ```
        """
        if not self._has_soft_delete:
            raise AttributeError(
                f"Model {self.model.__name__} does not support soft delete. "
                "Use delete() instead."
            )

        return await self.update(id, deleted_at=datetime.now(timezone.utc))

    async def delete(self, id: uuid.UUID) -> bool:
        """
        Hard delete a record by ID within the current project.

        This permanently removes the record from the database.
        Use with caution.

        Args:
            id: UUID of the record to delete

        Returns:
            True if deleted, False if not found

        Example:
            ```python
            deleted = await repository.delete(rfq_id)
            ```
        """
        query = select(self.model).where(
            and_(self.model.id == id, self.model.project_id == self.project_id)
        )

        result = await self.session.execute(query)
        instance = result.scalar_one_or_none()

        if instance:
            await self.session.delete(instance)
            await self.session.flush()
            return True

        return False

    async def count(self, include_deleted: bool = False, **filters: Any) -> int:
        """
        Count records within the current project.

        Args:
            include_deleted: If True, include soft-deleted records in count
            **filters: Additional filters to apply

        Returns:
            Number of records matching the criteria

        Example:
            ```python
            total = await repository.count(status='published')
            ```
        """
        from sqlalchemy import func

        query = select(func.count()).select_from(self.model)

        # Enforce project filtering
        query = self._enforce_project_filter(query)

        # Apply additional filters
        for key, value in filters.items():
            if hasattr(self.model, key):
                query = query.where(getattr(self.model, key) == value)

        # Apply soft delete filter
        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def exists(self, id: uuid.UUID, include_deleted: bool = False) -> bool:
        """
        Check if a record exists by ID within the current project.

        Args:
            id: UUID of the record
            include_deleted: If True, include soft-deleted records

        Returns:
            True if record exists, False otherwise

        Example:
            ```python
            if await repository.exists(rfq_id):
                # do something
            ```
        """
        query = select(self.model.id).where(self.model.id == id)

        # Enforce project filtering
        query = self._enforce_project_filter(query)

        # Apply soft delete filter
        if not include_deleted:
            query = self._apply_soft_delete_filter(query)

        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None
