# Dependency Injection Utilities

Production-ready FastAPI dependency injection utilities for async database sessions, project context, and repository factories.

## Overview

This module provides three main utilities:

1. **Async DB Session Provider** - Manages database sessions with proper lifecycle and error handling
2. **Project Context Provider** - Extracts and validates project context from `request.state`
3. **Repository Factory** - Automatically injects `project_id` into repository instances

## 1. Database Session Provider

### Basic Usage

```python
from fastapi import Depends, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.db import get_db_session

router = APIRouter()

@router.get("/items")
async def list_items(
    session: AsyncSession = Depends(get_db_session)
):
    # Session is automatically committed on success, rolled back on error
    result = await session.execute(select(Item))
    return result.scalars().all()
```

### Features

- ✅ Automatic transaction management (commit on success, rollback on error)
- ✅ Proper session cleanup (always closed)
- ✅ Production-ready error handling
- ✅ Connection pooling via `AsyncSessionLocal`
- ✅ Logging for debugging

### Error Handling

The session provider handles:
- `SQLAlchemyError` - Database-specific errors (500 with generic message)
- Unexpected exceptions - Logged and returned as 500 errors
- Session cleanup - Always ensures session is closed

## 2. Project Context Provider

### Setup Middleware

First, add the middleware to extract project context:

```python
from fastapi import FastAPI
from app.middleware.project_context import ProjectContextMiddleware

app = FastAPI()
app.add_middleware(ProjectContextMiddleware)
```

The middleware extracts `project_id` from:
1. `X-Project-ID` header (preferred)
2. `project_id` query parameter
3. `project_id` path parameter

### Basic Usage

```python
from fastapi import Depends
from app.deps.context import get_project_context, get_project_id, ProjectContext

# Get full context
@router.get("/items")
async def list_items(
    context: ProjectContext = Depends(get_project_context)
):
    project_id = context.project_id
    user_id = context.user_id  # Optional, if set by middleware
    # Use project_id...
    
# Or just get project_id
@router.get("/items")
async def list_items(
    project_id: uuid.UUID = Depends(get_project_id)
):
    # Use project_id...
```

### ProjectContext Structure

```python
@dataclass
class ProjectContext:
    project_id: uuid.UUID  # Required
    user_id: Optional[uuid.UUID] = None  # Optional
    organization_id: Optional[uuid.UUID] = None  # Optional
```

### Error Handling

- Missing context: Returns 500 error (middleware not configured)
- Invalid context: Returns 500 error (invalid configuration)
- Missing project_id: Returns 400 error (required field)

## 3. Repository Factory

### Basic Usage

```python
from fastapi import Depends
from app.repositories.rfq import RFQRepository
from app.deps.repository import get_repository_factory

# Create factory function
get_rfq_repository = get_repository_factory(RFQRepository)

@router.get("/rfqs")
async def list_rfqs(
    repo: RFQRepository = Depends(get_rfq_repository)
):
    # Repository already has project_id injected!
    return await repo.list()
```

### Alternative: Direct Dependency Creation

```python
from app.deps.repository import create_repository_dependency

get_rfq_repository = create_repository_dependency(RFQRepository)

@router.get("/rfqs")
async def list_rfqs(
    rfq_repo: RFQRepository = Depends(get_rfq_repository)
):
    return await rfq_repo.list()
```

### For Background Jobs / Services

```python
from app.deps.repository import get_repository
from app.repositories.rfq import RFQRepository

async def background_task(session: AsyncSession, project_id: uuid.UUID):
    # Create repository directly (outside FastAPI dependency system)
    repo = get_repository(RFQRepository, session, project_id)
    rfqs = await repo.list()
```

## Complete Example

Here's a complete example combining all three utilities:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.db import get_db_session
from app.deps.context import get_project_id
from app.deps.repository import get_repository_factory
from app.repositories.rfq import RFQRepository

router = APIRouter()

# Create repository factory
get_rfq_repository = get_repository_factory(RFQRepository)

@router.get("/rfqs")
async def list_rfqs(
    repo: RFQRepository = Depends(get_rfq_repository)
):
    """
    List RFQs for the current project.
    
    The repository automatically filters by project_id from request context.
    """
    return await repo.list(status="published")

@router.post("/rfqs")
async def create_rfq(
    data: RFQCreateSchema,
    repo: RFQRepository = Depends(get_rfq_repository)
):
    """
    Create a new RFQ.
    
    The repository automatically injects project_id from request context.
    """
    return await repo.create(**data.dict())

# Alternative: Manual approach (if you need more control)
@router.get("/rfqs/manual")
async def list_rfqs_manual(
    session: AsyncSession = Depends(get_db_session),
    project_id: uuid.UUID = Depends(get_project_id)
):
    """
    Manual approach - create repository yourself.
    
    Use this if you need to pass additional parameters or have custom logic.
    """
    repo = RFQRepository(session, project_id)
    return await repo.list()
```

## Setup in main.py

```python
from fastapi import FastAPI
from app.middleware.project_context import ProjectContextMiddleware
from app.api.v1 import api_router

app = FastAPI()

# Add project context middleware
app.add_middleware(ProjectContextMiddleware)

# Include routers
app.include_router(api_router, prefix="/api/v1")
```

## Error Handling Best Practices

All utilities include production-ready error handling:

1. **Database Errors**: Logged with full context, user gets generic message
2. **Missing Context**: Clear error messages for configuration issues
3. **Invalid Data**: Validation errors with specific details
4. **Unexpected Errors**: Logged with stack traces, user gets safe message

## Testing

For testing, you can override dependencies:

```python
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app

def override_get_db_session():
    # Return mock session
    return AsyncMock()

def override_get_project_context():
    from app.deps.context import ProjectContext
    return ProjectContext(project_id=uuid.UUID("..."))

app.dependency_overrides[get_db_session] = override_get_db_session
app.dependency_overrides[get_project_context] = override_get_project_context

client = TestClient(app)
```

## Architecture Notes

- **Session Management**: Uses `AsyncSessionLocal` with proper context managers
- **Transaction Safety**: Automatic commit/rollback based on exceptions
- **Multi-Tenancy**: Strict project_id enforcement via repository layer
- **Type Safety**: Full type hints for IDE support and runtime validation
- **Production Ready**: Comprehensive error handling and logging
