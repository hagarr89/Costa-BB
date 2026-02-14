# Test Suite

Comprehensive pytest test suite for COSTA backend multi-tenant functionality.

## Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and test models
├── test_project_dependencies.py  # Tests for project ID extraction
├── test_project_mixins.py        # Tests for model mixins
└── README.md                      # This file
```

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Files

```bash
# Test project dependencies
pytest tests/test_project_dependencies.py

# Test model mixins
pytest tests/test_project_mixins.py
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

## Test Coverage

### 1. Project ID Dependencies (`test_project_dependencies.py`)

Tests for FastAPI dependencies that extract `project_id` from:
- HTTP headers (`X-Project-ID`)
- Query parameters (`?project_id=...`)
- Path parameters (`/projects/{project_id}/...`)

**Coverage:**
- ✅ Valid UUID extraction
- ✅ Missing parameter handling (400 error)
- ✅ Invalid UUID format handling (400 error)
- ✅ Edge cases (empty strings, malformed UUIDs)

### 2. Model Mixins (`test_project_mixins.py`)

Tests for SQLAlchemy model mixins:
- `ProjectScopedMixin` - Adds `project_id` field
- `SoftDeleteMixin` - Adds `deleted_at` field
- `BaseProjectModel` - Combined base model
- `BaseProjectModelWithSoftDelete` - Full feature set

**Coverage:**
- ✅ `project_id` requirement and storage
- ✅ Foreign key constraints
- ✅ Index creation
- ✅ `deleted_at` default behavior
- ✅ Soft delete workflow
- ✅ Multi-tenant isolation

## Test Database

Tests use PostgreSQL for full compatibility with production models (UUID, CITEXT, JSONB, etc.).

### Setup Test Database

#### Option 1: Using Docker Compose (Recommended)

```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest

# Stop test database
docker-compose -f docker-compose.test.yml down
```

#### Option 2: Manual PostgreSQL Setup

1. Create test database:
```sql
CREATE DATABASE costadb_test;
CREATE USER costa_user WITH PASSWORD 'supersecretpassword';
GRANT ALL PRIVILEGES ON DATABASE costadb_test TO costa_user;
```

2. Set environment variable (optional, uses default if not set):
```bash
export COSTA_DATABASE_URL_TEST="postgresql+asyncpg://costa_user:supersecretpassword@localhost:5433/costadb_test"
pytest
```

### Database Configuration

The test database URL is configured in `app/core/config.py`:
- Default: `postgresql+asyncpg://costa_user:supersecretpassword@localhost:5433/costadb_test`
- Override: Set `COSTA_DATABASE_URL_TEST` environment variable

## Fixtures

### Database Fixtures

- `test_engine` - Async database engine (function scope)
- `test_session` - Async database session with auto-rollback (function scope)
- `test_project_id` - Generated UUID for test project
- `test_project_id_2` - Second UUID for isolation tests
- `test_project` - Test project record in database
- `test_project_2` - Second test project record

### HTTP Client Fixtures

- `test_app` - FastAPI test application
- `test_client` - Async HTTP client for API tests

## Example Test Models

The test suite includes example models that demonstrate proper usage:

- `TestProjectModel` - Uses `BaseProjectModel` (project-scoped, no soft delete)
- `TestProjectModelWithSoftDelete` - Uses `BaseProjectModelWithSoftDelete` (full features)
- `TestProject` - Reference table for foreign key constraints

## Best Practices

1. **Use fixtures** - Leverage shared fixtures for database sessions and test data
2. **Isolation** - Each test runs in its own transaction (auto-rollback)
3. **Async first** - All tests use async/await patterns
4. **Clear names** - Test names describe what they're testing
5. **One assertion per concept** - Keep tests focused

## Continuous Integration

Tests are designed to run in CI environments:
- PostgreSQL database required (use docker-compose.test.yml)
- Full production model compatibility
- Deterministic results with transaction rollback
- Parallel execution support
- Session-scoped engine for performance