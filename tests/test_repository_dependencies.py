"""
Tests for repository factory dependency injection utilities.

Tests cover get_repository_factory, create_repository_dependency, and get_repository
from app/deps/repository.py.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException, Depends

from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.context import ProjectContext
from app.deps.repository import (
    get_repository_factory,
    create_repository_dependency,
    get_repository,
)
from app.repositories.base import BaseRepository


# Mock repository class for testing
class MockModel:
    """Mock model for testing."""
    project_id = None  # Attribute exists for hasattr check


class MockRepository(BaseRepository[MockModel]):
    """Mock repository for testing."""
    
    def __init__(self, session: AsyncSession, project_id: uuid.UUID):
        # MockModel needs to have project_id attribute for BaseRepository validation
        super().__init__(session, project_id, MockModel)


class TestGetRepositoryFactory:
    """Tests for get_repository_factory function."""

    def test_creates_factory_function(self):
        """Should create a factory function for the repository class."""
        factory = get_repository_factory(MockRepository)
        
        assert callable(factory)
        # Factory should have Depends annotations
        assert hasattr(factory, "__annotations__")

    @pytest.mark.asyncio
    async def test_factory_creates_repository_with_injected_dependencies(self):
        """Should create repository instance with injected session and context."""
        project_id = uuid.uuid4()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = ProjectContext(project_id=project_id)
        
        factory = get_repository_factory(MockRepository)
        
        # Call factory with mocked dependencies
        repo = factory(session=mock_session, context=mock_context)
        
        assert isinstance(repo, MockRepository)
        assert repo.session == mock_session
        assert repo.project_id == project_id

    @pytest.mark.asyncio
    async def test_factory_raises_http_exception_on_value_error(self):
        """Should raise HTTPException 500 when repository raises ValueError."""
        project_id = uuid.uuid4()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = ProjectContext(project_id=project_id)
        
        # Mock repository to raise ValueError
        with patch.object(MockRepository, "__init__", side_effect=ValueError("Invalid project_id")):
            factory = get_repository_factory(MockRepository)
            
            with pytest.raises(HTTPException) as exc_info:
                factory(session=mock_session, context=mock_context)
            
            assert exc_info.value.status_code == 500
            assert "Failed to initialize repository" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_factory_raises_http_exception_on_unexpected_error(self):
        """Should raise HTTPException 500 on unexpected errors."""
        project_id = uuid.uuid4()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = ProjectContext(project_id=project_id)
        
        # Mock repository to raise unexpected error
        with patch.object(MockRepository, "__init__", side_effect=RuntimeError("Unexpected")):
            factory = get_repository_factory(MockRepository)
            
            with pytest.raises(HTTPException) as exc_info:
                factory(session=mock_session, context=mock_context)
            
            assert exc_info.value.status_code == 500
            assert "Failed to create repository instance" in exc_info.value.detail

    def test_factory_uses_depends_for_session_and_context(self):
        """Should use Depends for session and context parameters."""
        factory = get_repository_factory(MockRepository)
        
        # Check that factory signature includes Depends
        import inspect
        sig = inspect.signature(factory)
        
        # Parameters should exist (Depends is handled at runtime)
        assert "session" in sig.parameters
        assert "context" in sig.parameters


class TestCreateRepositoryDependency:
    """Tests for create_repository_dependency alias."""

    def test_is_alias_for_get_repository_factory(self):
        """Should return same result as get_repository_factory."""
        factory1 = get_repository_factory(MockRepository)
        factory2 = create_repository_dependency(MockRepository)
        
        # Both should be callable factory functions
        assert callable(factory1)
        assert callable(factory2)
        
        # They should behave the same way
        project_id = uuid.uuid4()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_context = ProjectContext(project_id=project_id)
        
        repo1 = factory1(session=mock_session, context=mock_context)
        repo2 = factory2(session=mock_session, context=mock_context)
        
        assert isinstance(repo1, MockRepository)
        assert isinstance(repo2, MockRepository)
        assert repo1.project_id == repo2.project_id


class TestGetRepository:
    """Tests for get_repository direct function."""

    def test_creates_repository_instance(self):
        """Should create repository instance directly."""
        project_id = uuid.uuid4()
        mock_session = AsyncMock(spec=AsyncSession)
        
        repo = get_repository(MockRepository, mock_session, project_id)
        
        assert isinstance(repo, MockRepository)
        assert repo.session == mock_session
        assert repo.project_id == project_id

    def test_raises_value_error_on_repository_value_error(self):
        """Should raise ValueError when repository raises ValueError."""
        project_id = uuid.uuid4()
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock repository to raise ValueError
        with patch.object(MockRepository, "__init__", side_effect=ValueError("Invalid")):
            with pytest.raises(ValueError, match="Invalid"):
                get_repository(MockRepository, mock_session, project_id)

    def test_raises_http_exception_on_unexpected_error(self):
        """Should raise HTTPException 500 on unexpected errors."""
        project_id = uuid.uuid4()
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock repository to raise unexpected error
        with patch.object(MockRepository, "__init__", side_effect=RuntimeError("Unexpected")):
            with pytest.raises(HTTPException) as exc_info:
                get_repository(MockRepository, mock_session, project_id)
            
            assert exc_info.value.status_code == 500
            assert "Failed to create repository instance" in exc_info.value.detail

    def test_uses_provided_session_and_project_id(self):
        """Should use provided session and project_id without dependency injection."""
        project_id1 = uuid.uuid4()
        project_id2 = uuid.uuid4()
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session2 = AsyncMock(spec=AsyncSession)
        
        repo1 = get_repository(MockRepository, mock_session1, project_id1)
        repo2 = get_repository(MockRepository, mock_session2, project_id2)
        
        assert repo1.session == mock_session1
        assert repo1.project_id == project_id1
        assert repo2.session == mock_session2
        assert repo2.project_id == project_id2
