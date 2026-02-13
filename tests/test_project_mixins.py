import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, declarative_mixin

from app.db.base import Base


# -------------------------
# UUID Base
# -------------------------

class BaseUUIDModel(Base):
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


# -------------------------
# Project Scoped
# -------------------------

@declarative_mixin
class ProjectScopedMixin:

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_projects.id"),
        nullable=False,
        index=True,
    )


# -------------------------
# Soft Delete
# -------------------------

@declarative_mixin
class SoftDeleteMixin:

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )


# -------------------------
# Combined Models
# -------------------------

class BaseProjectModel(ProjectScopedMixin, BaseUUIDModel):
    __abstract__ = True


class BaseProjectModelWithSoftDelete(
    ProjectScopedMixin,
    SoftDeleteMixin,
    BaseUUIDModel,
):
    __abstract__ = True
