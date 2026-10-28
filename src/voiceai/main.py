"""Application entry point for the Voice AI Interview Platform."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis
from redis.exceptions import RedisError

from voiceai.api.routes.applications import router as applications_router
from voiceai.api.routes.candidates import router as candidates_router
from voiceai.api.routes.health import router as health_router
from voiceai.api.routes.interviews import router as interviews_router
from voiceai.api.routes.jobs import router as jobs_router
from voiceai.api.routes.organizations import router as organizations_router
from voiceai.core.config import get_settings
from voiceai.db.session import SessionFactory, engine
from voiceai.models import Base
from voiceai.services.organization import ensure_demo_organization


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()

    # Dev bootstrap: create tables if missing (Alembic can replace later).
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure a demo organization exists for local Swagger / UI flows.
    async with SessionFactory() as session:
        await ensure_demo_organization(session)

    redis_client = None
    try:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
        await redis_client.ping()
    except (OSError, RedisError, TimeoutError):
        redis_client = None

    app.state.db_engine = engine
    app.state.redis = redis_client

    try:
        yield
    finally:
        if redis_client is not None:
            await redis_client.aclose()
        await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(organizations_router)
    app.include_router(jobs_router)
    app.include_router(candidates_router)
    app.include_router(applications_router)
    app.include_router(interviews_router)
    return app


app = create_app()
