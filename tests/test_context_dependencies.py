"""
Tests for project context dependency injection utilities.

Tests cover ProjectContext, get_project_context, and get_project_id
from app/deps/context.py.
"""

import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, Request

from app.deps.context import ProjectContext, get_project_context, get_project_id


class TestProjectContext:
    """Tests for ProjectContext dataclass."""

    def test_create_with_project_id_only(self):
        """Should create ProjectContext with only project_id."""
        project_id = uuid.uuid4()
        context = ProjectContext(project_id=project_id)
        
        assert context.project_id == project_id
        assert context.user_id is None
        assert context.organization_id is None

    def test_create_with_all_fields(self):
        """Should create ProjectContext with all fields."""
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()
        organization_id = uuid.uuid4()
        
        context = ProjectContext(
            project_id=project_id,
            user_id=user_id,
            organization_id=organization_id
        )
        
        assert context.project_id == project_id
        assert context.user_id == user_id
        assert context.organization_id == organization_id

    def test_raises_value_error_on_none_project_id(self):
        """Should raise ValueError when project_id is None."""
        with pytest.raises(ValueError, match="project_id cannot be None"):
            ProjectContext(project_id=None)


class TestGetProjectContext:
    """Tests for get_project_context dependency."""

    @pytest.mark.asyncio
    async def test_extracts_valid_project_context(self):
        """Should extract ProjectContext from request.state."""
        project_id = uuid.uuid4()
        context = ProjectContext(project_id=project_id)
        
        request = MagicMock(spec=Request)
        request.state.project_context = context
        
        result = await get_project_context(request)
        
        assert result == context
        assert result.project_id == project_id

    @pytest.mark.asyncio
    async def test_raises_500_when_project_context_missing(self):
        """Should raise HTTPException 500 when project_context not in request.state."""
        request = MagicMock(spec=Request)
        # Create a state object without project_context attribute
        request.state = MagicMock()
        # Make hasattr return False for project_context
        type(request.state).project_context = None
        # Override hasattr to return False
        with patch("builtins.hasattr", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await get_project_context(request)
        
        assert exc_info.value.status_code == 500
        assert "Project context not available" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_500_when_project_context_not_instance(self):
        """Should raise HTTPException 500 when project_context is not ProjectContext instance."""
        request = MagicMock(spec=Request)
        request.state.project_context = {"project_id": str(uuid.uuid4())}  # Dict instead
        
        with pytest.raises(HTTPException) as exc_info:
            await get_project_context(request)
        
        assert exc_info.value.status_code == 500
        assert "Invalid project context configuration" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_400_when_project_id_is_none(self):
        """Should raise HTTPException 400 when project_id is None."""
        # Create a context with None project_id (bypassing __post_init__)
        context = ProjectContext.__new__(ProjectContext)
        context.project_id = None
        context.user_id = None
        context.organization_id = None
        
        request = MagicMock(spec=Request)
        request.state.project_context = context
        
        with pytest.raises(HTTPException) as exc_info:
            await get_project_context(request)
        
        assert exc_info.value.status_code == 400
        assert "Project ID is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_500_on_unexpected_error(self):
        """Should raise HTTPException 500 on unexpected errors."""
        request = MagicMock(spec=Request)
        # Make accessing request.state raise an exception
        request.state = MagicMock()
        # Make hasattr raise an exception
        def mock_hasattr(obj, name):
            if name == "project_context":
                raise RuntimeError("Unexpected error accessing state")
            return False
        
        with patch("builtins.hasattr", side_effect=mock_hasattr):
            with pytest.raises(HTTPException) as exc_info:
                await get_project_context(request)
            
            assert exc_info.value.status_code == 500
            assert "Failed to extract project context" in exc_info.value.detail


class TestGetProjectId:
    """Tests for get_project_id convenience function."""

    @pytest.mark.asyncio
    async def test_returns_project_id_from_context(self):
        """Should return project_id from ProjectContext."""
        project_id = uuid.uuid4()
        context = ProjectContext(project_id=project_id)
        
        request = MagicMock(spec=Request)
        request.state.project_context = context
        
        with patch("app.deps.context.get_project_context", return_value=context):
            result = await get_project_id(request)
        
        assert result == project_id

    @pytest.mark.asyncio
    async def test_propagates_http_exception_from_get_project_context(self):
        """Should propagate HTTPException from get_project_context."""
        request = MagicMock(spec=Request)
        http_exception = HTTPException(status_code=500, detail="Context error")
        
        with patch("app.deps.context.get_project_context", side_effect=http_exception):
            with pytest.raises(HTTPException) as exc_info:
                await get_project_id(request)
            
            assert exc_info.value.status_code == 500
            assert exc_info.value.detail == "Context error"
