# Repository Layer

This directory contains the repository layer for data access operations in the COSTA multi-tenant SaaS system.

## Architecture

The repository layer follows clean architecture principles:

```
Controller → Service → Repository → Database
```

### Key Principles

1. **Strict Multi-Tenancy**: All repositories enforce project-level isolation
2. **No Business Logic**: Repositories only handle data access
3. **Automatic Tenant Filtering**: All queries are automatically scoped to `project_id`
4. **Type Safety**: Uses generic typing for compile-time safety

## BaseRepository

The `BaseRepository` class provides a foundation for all project-scoped repositories.

### Features

- ✅ Automatic `project_id` filtering on all read queries
- ✅ Automatic `project_id` injection on create operations
- ✅ Prevention of tenant filtering bypass
- ✅ Soft delete support (if model has `deleted_at` field)
- ✅ Generic typing for type safety
- ✅ Production-ready error handling

### Core Methods

- `get_by_id(id, include_deleted=False)` - Get single record by ID
- `list(skip=0, limit=100, include_deleted=False, order_by=None, **filters)` - List records with pagination
- `create(**data)` - Create new record (project_id auto-injected)
- `update(id, **data)` - Update record (project_id cannot be changed)
- `soft_delete(id)` - Soft delete record (if model supports it)
- `delete(id)` - Hard delete record
- `count(include_deleted=False, **filters)` - Count records
- `exists(id, include_deleted=False)` - Check if record exists

## Usage

### 1. Create a Model

First, create a model that inherits from `BaseProjectModel`:

```python
from app.models.base_project import BaseProjectModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

class RFQ(BaseProjectModel):
    __tablename__ = "rfqs"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(50), default="draft")
```

### 2. Create a Repository

Create a repository class that extends `BaseRepository`:

```python
from app.repositories.base import BaseRepository
from app.models.rfq import RFQ
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

class RFQRepository(BaseRepository[RFQ]):
    def __init__(self, session: AsyncSession, project_id: uuid.UUID):
        super().__init__(session, project_id, RFQ)
    
    # Add entity-specific methods if needed
    async def get_published(self):
        return await self.list(status="published")
```

### 3. Use in FastAPI Endpoints

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps.db import get_db_session
from app.deps.project import get_project_id_from_header
from app.repositories.rfq import RFQRepository
import uuid

router = APIRouter()

@router.get("/rfqs")
async def list_rfqs(
    session: AsyncSession = Depends(get_db_session),
    project_id: uuid.UUID = Depends(get_project_id_from_header),
):
    repo = RFQRepository(session, project_id)
    rfqs = await repo.list(status="published", limit=50)
    return rfqs

@router.post("/rfqs")
async def create_rfq(
    data: RFQCreateSchema,
    session: AsyncSession = Depends(get_db_session),
    project_id: uuid.UUID = Depends(get_project_id_from_header),
):
    repo = RFQRepository(session, project_id)
    rfq = await repo.create(**data.dict())
    return rfq
```

## Security Guarantees

The `BaseRepository` enforces several security guarantees:

1. **Mandatory Project Filtering**: All queries automatically include `WHERE project_id = :project_id`
2. **Project ID Injection**: `project_id` is automatically set on create operations
3. **Project ID Immutability**: `project_id` cannot be changed via `update()` method
4. **Bypass Prevention**: Attempting to set a different `project_id` raises `ValueError`

## Soft Delete Support

If your model includes a `deleted_at` field, the repository automatically:

- Filters out soft-deleted records from queries (unless `include_deleted=True`)
- Provides `soft_delete()` method
- Prevents updating soft-deleted records

To enable soft delete, inherit from `BaseProjectModelWithSoftDelete`:

```python
from app.models.base_project import BaseProjectModelWithSoftDelete

class RFQ(BaseProjectModelWithSoftDelete):
    __tablename__ = "rfqs"
    # ... fields
```

## Best Practices

1. **Always use repositories**: Never access models directly from services or controllers
2. **One repository per entity**: Create a dedicated repository for each project-scoped entity
3. **Keep repositories thin**: Add business logic in services, not repositories
4. **Use type hints**: Leverage generic typing for better IDE support
5. **Validate project_id**: Always validate project_id in dependencies before creating repositories

## Error Handling

The repository raises appropriate exceptions:

- `ValueError`: Invalid `project_id` or attempt to bypass tenant filtering
- `AttributeError`: Attempting soft delete on model without `deleted_at`
- SQLAlchemy exceptions: Database-level errors (handled by FastAPI)

## Testing

When testing repositories, always provide a valid `project_id`:

```python
import pytest
from app.repositories.rfq import RFQRepository
from app.db.session import AsyncSessionLocal

@pytest.mark.asyncio
async def test_list_rfqs():
    async with AsyncSessionLocal() as session:
        project_id = uuid.uuid4()
        repo = RFQRepository(session, project_id)
        rfqs = await repo.list()
        assert isinstance(rfqs, list)
```
