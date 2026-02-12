"""
Base model mixins for project-scoped entities.

These mixins provide project_id and optional soft delete support
for multi-tenant entities.
"""

import uuid
from datetime import datetime
from typing import Annotated, Optional

from sqlalchemy import ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_uuid import BaseUUIDModel


class ProjectScopedMixin(Base):
    """
    Mixin that adds project_id to a model.

    All project-scoped entities must include this mixin to ensure
    multi-tenant isolation.

    Example:
        ```python
        class RFQ(BaseUUIDModel, ProjectScopedMixin):
            __tablename__ = "rfqs"
            # ... other fields
        ```
    """

    __abstract__ = True

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Project (tenant) identifier for multi-tenant isolation",
    )


class SoftDeleteMixin(Base):
    """
    Mixin that adds soft delete support via deleted_at timestamp.

    Models using this mixin will be filtered out of queries by default
    unless include_deleted=True is explicitly passed.

    Example:
        ```python
        class RFQ(BaseUUIDModel, ProjectScopedMixin, SoftDeleteMixin):
            __tablename__ = "rfqs"
            # ... other fields
        ```
    """

    __abstract__ = True

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        default=None,
        nullable=True,
        index=True,
        comment="Timestamp when record was soft deleted (NULL if active)",
    )


class BaseProjectModel(BaseUUIDModel, ProjectScopedMixin):
    """
    Base model for project-scoped entities.

    Combines UUID primary key with project_id for multi-tenant isolation.
    Use this as a base class for all project-scoped entities.

    Example:
        ```python
        class RFQ(BaseProjectModel):
            __tablename__ = "rfqs"
            title: Mapped[str]
            # ... other fields
        ```
    """

    __abstract__ = True


class BaseProjectModelWithSoftDelete(BaseProjectModel, SoftDeleteMixin):
    """
    Base model for project-scoped entities with soft delete support.

    Combines UUID primary key, project_id, and soft delete capability.
    Use this for entities that should support soft deletion.

    Example:
        ```python
        class RFQ(BaseProjectModelWithSoftDelete):
            __tablename__ = "rfqs"
            title: Mapped[str]
            # ... other fields
        ```
    """

    __abstract__ = True
