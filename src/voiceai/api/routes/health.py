"""Infrastructure health endpoints."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a basic liveness response."""

    return {
        "status": "healthy",
        "service": "voiceai",
    }
