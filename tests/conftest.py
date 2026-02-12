"""
Pytest configuration and shared fixtures for async testing.

This module provides:
- Async database session fixtures
- Test database setup/teardown
- Example test models
- FastAPI test client fixtures
"""

import asyncio
import uuid
from datetime import datetime
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import String, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base_project import (
    BaseProjectModel,
    BaseProjectModelWithSoftDelete,
)


# Test database URL - use TEST_DATABASE_URL env var or fallback to SQLite
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    Create a test database engine.

    Uses in-memory SQLite for fast tests. For PostgreSQL testing,
    set TEST_DATABASE_URL environment variable.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {},
    )

    # Create all tables (test models are already registered with Base.metadata)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session.

    Automatically rolls back transactions after each test.
    """
    async_session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        # Begin a transaction
        await session.begin()
        yield session
        # Rollback after test
        await session.rollback()


@pytest_asyncio.fixture
async def test_project_id() -> uuid.UUID:
    """Generate a test project ID."""
    return uuid.uuid4()


@pytest_asyncio.fixture
async def test_project_id_2() -> uuid.UUID:
    """Generate a second test project ID for isolation tests."""
    return uuid.uuid4()


# ============================================================================
# Example Test Models
# ============================================================================


class TestProjectModel(BaseProjectModel):
    """Example model using BaseProjectModel (with project_id, no soft delete)."""

    __tablename__ = "test_projects"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))


class TestProjectModelWithSoftDelete(BaseProjectModelWithSoftDelete):
    """Example model using BaseProjectModelWithSoftDelete (with project_id and soft delete)."""

    __tablename__ = "test_projects_soft_delete"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))


class TestProject(Base):
    """Test project table for foreign key references."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        type_=uuid.UUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        nullable=False,
    )


@pytest_asyncio.fixture
async def test_project(test_session: AsyncSession, test_project_id: uuid.UUID) -> dict:
    """Create a test project in the database."""
    project = TestProject(id=test_project_id, name="Test Project")
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)
    return {"id": project.id, "name": project.name}


@pytest_asyncio.fixture
async def test_project_2(
    test_session: AsyncSession, test_project_id_2: uuid.UUID
) -> dict:
    """Create a second test project for isolation tests."""
    project = TestProject(id=test_project_id_2, name="Test Project 2")
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)
    return {"id": project.id, "name": project.name}


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_app() -> FastAPI:
    """Create a test FastAPI app."""
    from fastapi import FastAPI

    app = FastAPI()
    return app


@pytest_asyncio.fixture
async def test_client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create a test HTTP client."""
    async with AsyncClient(app=test_app, base_url="http://test") as client:
        yield client
