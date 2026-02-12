# costa-backend

Production-grade FastAPI backend skeleton.

All generated code MUST follow docs/02_architecture.md strictly.
Business logic must comply with docs/01_requirements.md.
Database changes must align with docs/03_database_schema.md.

## Features

- Async FastAPI app with structured project layout.
- Environment-based configuration using Pydantic Settings.
- Async SQLAlchemy setup for PostgreSQL (via `asyncpg`).
- UUID-based primary keys for models.
- Dependency-injected async DB sessions.

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root, for example:

   ```bash
   COSTA_ENV=dev
   COSTA_DEBUG=true
   COSTA_PROJECT_NAME="costa-backend"
   COSTA_API_V1_STR="/api/v1"

   COSTA_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/costa
   COSTA_BACKEND_CORS_ORIGINS=["http://localhost:3000"]
   COSTA_SECRET_KEY="change_me_in_prod"
   COSTA_LOG_LEVEL="INFO"
   ```

4. Run the app:

   ```bash
   uvicorn app.main:app --reload
   ```

