"""
Tests for database session dependency injection utilities.

Tests cover the new error handling, transaction management, and session lifecycle
introduced in app/deps/db.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db_session, _get_db_session_context


class TestGetDbSessionContext:
    """Tests for _get_db_session_context context manager."""

    @pytest.mark.asyncio
    async def test_successful_session_commit(self):
        """Should commit session when no exceptions occur."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch("app.deps.db.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            async with _get_db_session_context() as session:
                assert session == mock_session
            
            # Verify commit was called
            mock_session.commit.assert_called_once()
            # Verify close was called
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_sqlalchemy_error_rollback_and_raise_http_exception(self):
        """Should rollback and raise HTTPException on SQLAlchemyError."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        db_error = OperationalError("Connection failed", None, None)
        
        with patch("app.deps.db.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.side_effect = db_error
            
            with pytest.raises(HTTPException) as exc_info:
                async with _get_db_session_context() as session:
                    pass
            
            assert exc_info.value.status_code == 500
            assert "Database operation failed" in exc_info.value.detail
            mock_session.rollback.assert_not_called()  # Session not created yet

    @pytest.mark.asyncio
    async def test_sqlalchemy_error_during_execution_rollback(self):
        """Should rollback session when SQLAlchemyError occurs during execution."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("DB error"))
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch("app.deps.db.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                async with _get_db_session_context() as session:
                    pass
            
            assert exc_info.value.status_code == 500
            assert "Database operation failed" in exc_info.value.detail
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_unexpected_exception_rollback_and_raise_http_exception(self):
        """Should rollback and raise HTTPException on unexpected exceptions."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock(side_effect=ValueError("Unexpected error"))
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch("app.deps.db.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                async with _get_db_session_context() as session:
                    pass
            
            assert exc_info.value.status_code == 500
            assert "unexpected error occurred" in exc_info.value.detail.lower()
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_close_error_logged_but_not_raised(self):
        """Should log warning but not raise when closing session fails."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock(side_effect=Exception("Close error"))
        
        with patch("app.deps.db.AsyncSessionLocal") as mock_session_local:
            with patch("app.deps.db.logger") as mock_logger:
                mock_session_local.return_value.__aenter__.return_value = mock_session
                mock_session_local.return_value.__aexit__.return_value = None
                
                async with _get_db_session_context() as session:
                    pass
                
                # Should log warning but not raise
                mock_logger.warning.assert_called_once()
                assert "Error closing session" in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_session_always_closed_in_finally(self):
        """Should always close session even if exception occurs."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock(side_effect=Exception("Test error"))
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch("app.deps.db.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            
            with pytest.raises(HTTPException):
                async with _get_db_session_context() as session:
                    pass
            
            # Verify close was called in finally block
            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancellation_rollback_and_reraise(self):
        """Should rollback and re-raise on BaseException (e.g. CancelledError)."""
        import asyncio
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.commit.side_effect = asyncio.CancelledError()
        with patch("app.deps.db.AsyncSessionLocal") as mock_session_local:
            mock_session_local.return_value.__aenter__.return_value = mock_session
            mock_session_local.return_value.__aexit__.return_value = None
            with pytest.raises(asyncio.CancelledError):
                async with _get_db_session_context() as session:
                    pass
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()


class TestGetDbSession:
    """Tests for get_db_session FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_yields_session_from_context_manager(self):
        """Should yield session from context manager."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.close = AsyncMock()
        
        with patch("app.deps.db._get_db_session_context") as mock_context:
            mock_context.return_value.__aenter__.return_value = mock_session
            mock_context.return_value.__aexit__.return_value = None
            
            async for session in get_db_session():
                assert session == mock_session
                break  # Only test first iteration

    @pytest.mark.asyncio
    async def test_propagates_http_exception_from_context(self):
        """Should propagate HTTPException from context manager."""
        http_exception = HTTPException(status_code=500, detail="DB error")
        
        with patch("app.deps.db._get_db_session_context") as mock_context:
            mock_context.return_value.__aenter__.side_effect = http_exception
            
            with pytest.raises(HTTPException) as exc_info:
                async for session in get_db_session():
                    pass
            
            assert exc_info.value.status_code == 500
