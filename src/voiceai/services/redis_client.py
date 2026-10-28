"""Optional Redis helpers for ephemeral interview session state."""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

from voiceai.core.config import get_settings

logger = logging.getLogger(__name__)


async def _with_redis() -> Redis | None:
    """Open a short-lived Redis client (safe across pytest event loops)."""

    settings = get_settings()
    client = Redis.from_url(settings.redis_url, decode_responses=True)
    try:
        await client.ping()
    except (OSError, RedisError, TimeoutError):
        logger.warning("redis_unavailable")
        await client.aclose()
        return None
    return client


async def set_session_state(
    interview_id: str,
    payload: dict[str, Any],
    ttl: int = 3600,
) -> None:
    client = await _with_redis()
    if client is None:
        return
    try:
        await client.set(
            f"interview:session:{interview_id}",
            json.dumps(payload),
            ex=ttl,
        )
    except (OSError, RedisError, TimeoutError, RuntimeError):
        logger.warning("redis_set_session_failed interview_id=%s", interview_id)
    finally:
        await client.aclose()


async def get_session_state(interview_id: str) -> dict[str, Any] | None:
    client = await _with_redis()
    if client is None:
        return None
    try:
        raw = await client.get(f"interview:session:{interview_id}")
        if not raw:
            return None
        return json.loads(raw)
    except (OSError, RedisError, TimeoutError, RuntimeError, json.JSONDecodeError):
        logger.warning("redis_get_session_failed interview_id=%s", interview_id)
        return None
    finally:
        await client.aclose()


async def clear_session_state(interview_id: str) -> None:
    client = await _with_redis()
    if client is None:
        return
    try:
        await client.delete(f"interview:session:{interview_id}")
    except (OSError, RedisError, TimeoutError, RuntimeError):
        logger.warning("redis_clear_session_failed interview_id=%s", interview_id)
    finally:
        await client.aclose()
