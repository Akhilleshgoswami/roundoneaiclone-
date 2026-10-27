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

    # Load application configuration.
    settings = get_settings()

    # Create a shared Redis client for this application process.
    redis_client = Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )

    # Expose shared infrastructure through application state.
    app.state.db_engine = engine
    app.state.redis = redis_client

    try:
        # Start serving requests.
        yield
    finally:
        # Release Redis and database resources during shutdown.
        await redis_client.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    # Load application settings.
    settings = get_settings()

    # Configure the application lifecycle and API documentation.
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    # Register infrastructure health endpoints.
    app.include_router(health_router)

    # Register job management endpoints.
    app.include_router(jobs_router)
    app.include_router(candidates_router)
    return app


# Export the ASGI application for Uvicorn.
app = create_app()
