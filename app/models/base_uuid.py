import uuid
from typing import Annotated

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


UUID_PK = Annotated[
    uuid.UUID,
    mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    ),
]


class BaseUUIDModel(Base):
    """Abstract base model that provides a UUID primary key."""

    __abstract__ = True

    id: Mapped[UUID_PK]

