from fastapi import APIRouter

from app.api.v1.ruleset import router as ruleset_router

api_router = APIRouter()
api_router.include_router(ruleset_router)
