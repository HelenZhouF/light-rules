from fastapi import APIRouter

from app.api.v1.ruleset import router as ruleset_router
from app.api.v1.rule import router as rule_router
from app.api.v1.domain import router as domain_router
from app.api.v1.batch_import import router as batch_import_router
from app.api.v1.function_category import router as function_category_router
from app.api.v1.function import router as function_router, router_no_prefix as function_router_no_prefix
from app.api.v1.validation import router as validation_router

api_router = APIRouter()
api_router.include_router(ruleset_router)
api_router.include_router(rule_router)
api_router.include_router(domain_router)
api_router.include_router(batch_import_router)
api_router.include_router(function_category_router)
api_router.include_router(function_router)
api_router.include_router(function_router_no_prefix)
api_router.include_router(validation_router)
