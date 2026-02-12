from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# Import all models here so Alembic (or other tooling) can discover them.
from app.models.user import User  # noqa: F401

