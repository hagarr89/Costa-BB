"""
Tests for project context middleware.

Tests cover ProjectContextMiddleware and create_project_context_middleware
from app/middleware/project_context.py.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import Request, HTTPException
from starlette.responses import Response

from app.middleware.project_context import (
    ProjectContextMiddleware,
    create_project_context_middleware,
)
from app.deps.context import ProjectContext


class TestProjectContextMiddleware:
    """Tests for ProjectContextMiddleware."""

    @pytest.mark.asyncio
    async def test_extracts_project_id_from_header(self):
        """Should extract project_id from X-Project-ID header."""
        project_id = uuid.uuid4()
        
        request = MagicMock(spec=Request)
        request.headers = {"X-Project-ID": str(project_id)}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        # Create a real state object
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        assert hasattr(request.state, "project_context")
        assert isinstance(request.state.project_context, ProjectContext)
        assert request.state.project_context.project_id == project_id
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_extracts_project_id_from_query_parameter(self):
        """Should extract project_id from query parameter when header missing."""
        project_id = uuid.uuid4()
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=str(project_id))
        request.path_params = {}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        assert request.state.project_context.project_id == project_id
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_extracts_project_id_from_path_parameter(self):
        """Should extract project_id from path parameter when header and query missing."""
        project_id = uuid.uuid4()
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {"project_id": str(project_id)}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        assert request.state.project_context.project_id == project_id
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_prefers_header_over_query_and_path(self):
        """Should prefer header over query parameter and path parameter."""
        header_id = uuid.uuid4()
        query_id = uuid.uuid4()
        path_id = uuid.uuid4()
        
        request = MagicMock(spec=Request)
        request.headers = {"X-Project-ID": str(header_id)}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=str(query_id))
        request.path_params = {"project_id": str(path_id)}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        assert request.state.project_context.project_id == header_id

    @pytest.mark.asyncio
    async def test_prefers_query_over_path(self):
        """Should prefer query parameter over path parameter."""
        query_id = uuid.uuid4()
        path_id = uuid.uuid4()
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=str(query_id))
        request.path_params = {"project_id": str(path_id)}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        assert request.state.project_context.project_id == query_id

    @pytest.mark.asyncio
    async def test_raises_400_on_invalid_uuid_in_header(self):
        """Should raise HTTPException 400 for invalid UUID in header."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Project-ID": "invalid-uuid"}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        call_next = AsyncMock()
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)
        
        assert exc_info.value.status_code == 400
        assert "Invalid project ID format in header" in exc_info.value.detail
        call_next.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_400_on_invalid_uuid_in_query(self):
        """Should raise HTTPException 400 for invalid UUID in query."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value="invalid-uuid")
        request.path_params = {}
        
        call_next = AsyncMock()
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)
        
        assert exc_info.value.status_code == 400
        assert "Invalid project ID format in query" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_raises_400_on_invalid_uuid_in_path(self):
        """Should raise HTTPException 400 for invalid UUID in path."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = {}
        request.path_params = {"project_id": "invalid-uuid"}
        
        call_next = AsyncMock()
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)
        
        assert exc_info.value.status_code == 400
        assert "Invalid project ID format in path" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_leaves_project_context_unset_when_no_project_id(self):
        """Should leave project_context unset when no project_id found."""
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        # Should not have project_context set
        assert not hasattr(request.state, "project_context")
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_empty_header_gracefully(self):
        """Should handle empty header string gracefully."""
        request = MagicMock(spec=Request)
        request.headers = {"X-Project-ID": ""}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = ProjectContextMiddleware(app=MagicMock())
        # Should not raise, but also not set context
        response = await middleware.dispatch(request, call_next)
        
        assert not hasattr(request.state, "project_context")


class TestCreateProjectContextMiddleware:
    """Tests for create_project_context_middleware factory."""

    @pytest.mark.asyncio
    async def test_require_project_id_raises_400_when_missing(self):
        """Should raise 400 when require_project_id=True and project_id missing."""
        middleware_class = create_project_context_middleware(require_project_id=True)
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        call_next = AsyncMock()
        
        middleware = middleware_class(app=MagicMock())
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)
        
        assert exc_info.value.status_code == 400
        assert "Project ID is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_project_id_false_allows_missing(self):
        """Should allow missing project_id when require_project_id=False."""
        middleware_class = create_project_context_middleware(require_project_id=False)
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = middleware_class(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        # Should not raise and not set context
        assert not hasattr(request.state, "project_context")
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_default_project_id_when_provided(self):
        """Should use default_project_id when project_id missing and default provided."""
        default_id = uuid.uuid4()
        middleware_class = create_project_context_middleware(
            require_project_id=False,
            default_project_id=default_id
        )
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = middleware_class(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        assert request.state.project_context.project_id == default_id

    @pytest.mark.asyncio
    async def test_prefers_extracted_over_default_project_id(self):
        """Should prefer extracted project_id over default."""
        extracted_id = uuid.uuid4()
        default_id = uuid.uuid4()
        
        middleware_class = create_project_context_middleware(
            require_project_id=False,
            default_project_id=default_id
        )
        
        request = MagicMock(spec=Request)
        request.headers = {"X-Project-ID": str(extracted_id)}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        from types import SimpleNamespace
        request.state = SimpleNamespace()
        
        call_next = AsyncMock(return_value=Response())
        
        middleware = middleware_class(app=MagicMock())
        response = await middleware.dispatch(request, call_next)
        
        assert request.state.project_context.project_id == extracted_id

    @pytest.mark.asyncio
    async def test_require_project_id_overrides_default(self):
        """Should require project_id even if default is provided."""
        default_id = uuid.uuid4()
        middleware_class = create_project_context_middleware(
            require_project_id=True,
            default_project_id=default_id
        )
        
        request = MagicMock(spec=Request)
        request.headers = {}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        call_next = AsyncMock()
        
        middleware = middleware_class(app=MagicMock())
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)
        
        assert exc_info.value.status_code == 400
        # Should not use default when require_project_id=True

    @pytest.mark.asyncio
    async def test_still_validates_uuid_format(self):
        """Should still validate UUID format even with default provided."""
        default_id = uuid.uuid4()
        middleware_class = create_project_context_middleware(
            require_project_id=False,
            default_project_id=default_id
        )
        
        request = MagicMock(spec=Request)
        request.headers = {"X-Project-ID": "invalid-uuid"}
        request.query_params = MagicMock()
        request.query_params.get = MagicMock(return_value=None)
        request.path_params = {}
        
        call_next = AsyncMock()
        
        middleware = middleware_class(app=MagicMock())
        
        with pytest.raises(HTTPException) as exc_info:
            await middleware.dispatch(request, call_next)
        
        assert exc_info.value.status_code == 400
        assert "Invalid project ID format" in exc_info.value.detail
