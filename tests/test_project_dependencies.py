"""
Tests for project ID extraction dependencies.

Tests cover:
- Header-based extraction (X-Project-ID)
- Query parameter extraction
- Path parameter extraction
- Error handling for missing/invalid UUIDs
"""

import uuid

import pytest
from fastapi import APIRouter, Depends, FastAPI
from httpx import AsyncClient, ASGITransport


from app.deps.project import (
    get_project_id_from_header,
    get_project_id_from_path,
    get_project_id_from_query,
)


@pytest.fixture
def test_app() -> FastAPI:
    """Create a test FastAPI app with test routes."""
    app = FastAPI()
    router = APIRouter()

    @router.get("/header")
    async def test_header(project_id: uuid.UUID = Depends(get_project_id_from_header)):
        return {"project_id": str(project_id)}

    @router.get("/query")
    async def test_query(project_id: uuid.UUID = Depends(get_project_id_from_query)):
        return {"project_id": str(project_id)}

    @router.get("/path/{project_id}")
    async def test_path(project_id: uuid.UUID = Depends(get_project_id_from_path)):
        return {"project_id": str(project_id)}

    app.include_router(router)
    return app


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=test_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client



class TestProjectIDFromHeader:
    """Tests for get_project_id_from_header dependency."""

    async def test_extract_valid_project_id_from_header(self, client: AsyncClient):
        """Should extract valid UUID from X-Project-ID header."""
        project_id = uuid.uuid4()
        response = await client.get(
            "/header",
            headers={"X-Project-ID": str(project_id)},
        )

        assert response.status_code == 200
        assert response.json() == {"project_id": str(project_id)}

    async def test_missing_header_returns_400(self, client: AsyncClient):
        """Should return 400 when X-Project-ID header is missing."""
        response = await client.get("/header")

        assert response.status_code == 400
        assert "X-Project-ID header is required" in response.json()["detail"]

    async def test_invalid_uuid_format_returns_400(self, client: AsyncClient):
        """Should return 400 when header contains invalid UUID format."""
        response = await client.get(
            "/header",
            headers={"X-Project-ID": "not-a-valid-uuid"},
        )

        assert response.status_code == 400
        assert "Invalid project ID format" in response.json()["detail"]
        assert "not-a-valid-uuid" in response.json()["detail"]

    async def test_empty_header_returns_400(self, client: AsyncClient):
        """Should return 400 when header is empty string."""
        response = await client.get(
            "/header",
            headers={"X-Project-ID": ""},
        )

        assert response.status_code == 400
        assert "X-Project-ID header is required" in response.json()["detail"]

    async def test_malformed_uuid_returns_400(self, client: AsyncClient):
        """Should return 400 for malformed UUID strings."""
        test_cases = [
            "12345",  # Too short
            "00000000-0000-0000-0000-000000000000-extra",  # Too long
            "gggggggg-gggg-gggg-gggg-gggggggggggg",  # Invalid hex
            "12345678-1234-1234-1234-1234567890123",  # Wrong length
        ]

        for invalid_uuid in test_cases:
            response = await client.get(
                "/header",
                headers={"X-Project-ID": invalid_uuid},
            )
            assert response.status_code == 400
            assert "Invalid project ID format" in response.json()["detail"]


class TestProjectIDFromQuery:
    """Tests for get_project_id_from_query dependency."""

    async def test_extract_valid_project_id_from_query(self, client: AsyncClient):
        """Should extract valid UUID from query parameter."""
        project_id = uuid.uuid4()
        response = await client.get("/query", params={"project_id": str(project_id)})

        assert response.status_code == 200
        assert response.json() == {"project_id": str(project_id)}

    async def test_missing_query_param_returns_400(self, client: AsyncClient):
        """Should return 400 when project_id query parameter is missing."""
        response = await client.get("/query")

        assert response.status_code == 400
        assert "project_id query parameter is required" in response.json()["detail"]

    async def test_invalid_uuid_format_returns_400(self, client: AsyncClient):
        """Should return 400 when query param contains invalid UUID format."""
        response = await client.get("/query", params={"project_id": "invalid-uuid"})

        assert response.status_code == 400
        assert "Invalid project ID format" in response.json()["detail"]
        assert "invalid-uuid" in response.json()["detail"]

    async def test_empty_query_param_returns_400(self, client: AsyncClient):
        """Should return 400 when query parameter is empty."""
        response = await client.get("/query", params={"project_id": ""})

        assert response.status_code == 400
        assert "project_id query parameter is required" in response.json()["detail"]

    async def test_multiple_query_params_uses_first(self, client: AsyncClient):
        """Should handle multiple project_id parameters (uses first)."""
        project_id = uuid.uuid4()
        # FastAPI will use the first value
        response = await client.get(
            "/query",
            params=[("project_id", str(project_id)), ("project_id", "invalid")],
        )

        assert response.status_code == 200
        assert response.json() == {"project_id": str(project_id)}


class TestProjectIDFromPath:
    """Tests for get_project_id_from_path dependency."""

    async def test_extract_valid_project_id_from_path(self, client: AsyncClient):
        """Should extract valid UUID from path parameter."""
        project_id = uuid.uuid4()
        response = await client.get(f"/path/{project_id}")

        assert response.status_code == 200
        assert response.json() == {"project_id": str(project_id)}

    async def test_invalid_uuid_format_returns_400(self, client: AsyncClient):
        """Should return 400 when path contains invalid UUID format."""
        response = await client.get("/path/not-a-valid-uuid")

        assert response.status_code == 400
        assert "Invalid project ID format" in response.json()["detail"]
        assert "not-a-valid-uuid" in response.json()["detail"]

    async def test_malformed_uuid_in_path_returns_400(self, client: AsyncClient):
        """Should return 400 for malformed UUID in path."""
        test_cases = [
            "12345",
            "00000000-0000-0000-0000-000000000000-extra",
            "gggggggg-gggg-gggg-gggg-gggggggggggg",
        ]

        for invalid_uuid in test_cases:
            response = await client.get(f"/path/{invalid_uuid}")
            assert response.status_code == 400
            assert "Invalid project ID format" in response.json()["detail"]

    async def test_uppercase_uuid_works(self, client: AsyncClient):
        """Should accept uppercase UUID format."""
        project_id = uuid.uuid4()
        uppercase_uuid = str(project_id).upper()
        response = await client.get(f"/path/{uppercase_uuid}")

        assert response.status_code == 200
        assert response.json() == {"project_id": str(project_id).lower()}
