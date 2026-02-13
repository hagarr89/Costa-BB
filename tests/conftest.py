import uuid
import pytest
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String, Boolean, DateTime

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from httpx import AsyncClient, ASGITransport

from app.db.base import Base
from app.main import app
from app.models.base_project import (
    BaseProjectModel,
    BaseProjectModelWithSoftDelete,
)

DATABASE_URL = "postgresql+asyncpg://costa_user:supersecretpassword@localhost:5433/costadb_test"


# ---------- ENGINE ----------

@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        DATABASE_URL,
        poolclass=NullPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ---------- DB SESSION ----------

@pytest.fixture
async def db_session(engine):
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        tx = await session.begin()
        yield session
        await tx.rollback()


# ---------- HTTP CLIENT ----------

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client


# ---------- TEST MODELS ----------

class TestProject(Base):
    __tablename__ = "test_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String)


class TestProjectModel(BaseProjectModel):
    __tablename__ = "test_project_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        index=True,
    )


class TestProjectModelWithSoftDelete(BaseProjectModelWithSoftDelete):
    __tablename__ = "test_project_models_soft"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        index=True,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )

    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
