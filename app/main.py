from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.v1 import api_router as v1_router
from app.core.database import engine, Base
from app.models import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Light Rules API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(v1_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
