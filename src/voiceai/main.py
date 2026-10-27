"""Application entry point for the Voice AI Interview Platform."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from redis.asyncio import Redis

from voiceai.api.routes.candidates import router as candidates_router
from voiceai.api.routes.health import router as health_router
from voiceai.api.routes.jobs import router as jobs_router
from voiceai.core.config import get_settings
from voiceai.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize shared resources and clean them up at shutdown."""

    settings = get_settings()

    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    app.state.db_engine = engine
    app.state.redis = redis_client

    try:
        yield
    finally:
        await redis_client.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(jobs_router)
    app.include_router(candidates_router)

    return app


# Export the ASGI application for Uvicorn: voiceai.main:app
app = create_app()
