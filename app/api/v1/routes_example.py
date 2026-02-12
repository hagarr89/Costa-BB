from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps.db import get_db_session


router = APIRouter()


@router.get("/health", summary="Health check")
async def health_check(db: AsyncSession = Depends(get_db_session)) -> dict:
    # Optionally, perform a very cheap DB check here in the future.
    return {"status": "ok"}

