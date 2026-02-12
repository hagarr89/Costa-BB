from fastapi import APIRouter

from app.api.v1.routes_example import router as example_router


api_router = APIRouter()
api_router.include_router(example_router, tags=["health"])

