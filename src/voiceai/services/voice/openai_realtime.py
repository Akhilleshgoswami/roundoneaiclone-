"""OpenAI Realtime API provider (ephemeral client secrets for WebRTC)."""

from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

from voiceai.core.config import get_settings
from voiceai.services.voice.base import VoiceSessionCredentials

logger = logging.getLogger(__name__)

REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"


class OpenAIRealtimeProvider:
    """Create ephemeral Realtime sessions for browser WebRTC."""

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for live voice interviews."
            )
        self._settings = settings
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def create_ephemeral_session(
        self,
        *,
        instructions: str,
        safety_identifier: str | None = None,
    ) -> VoiceSessionCredentials:
        settings = self._settings
        extra_headers: dict[str, str] = {}
        if safety_identifier:
            extra_headers["OpenAI-Safety-Identifier"] = safety_identifier

        session: dict[str, Any] = {
            "type": "realtime",
            "model": settings.openai_realtime_model,
            "instructions": instructions,
            "audio": {
                "output": {
                    "voice": settings.openai_realtime_voice,
                },
            },
        }

        response = await self._client.realtime.client_secrets.create(
            expires_after={
                "anchor": "created_at",
                "seconds": settings.voice_client_secret_ttl_seconds,
            },
            session=session,  # type: ignore[arg-type]
            extra_headers=extra_headers or None,
        )

        secret_value = response.value
        expires_at = getattr(response, "expires_at", None)
        session_payload = response.session
        if hasattr(session_payload, "model_dump"):
            session_dict = session_payload.model_dump(mode="json")
        else:
            session_dict = dict(session_payload) if session_payload else {}

        logger.info(
            "minted_realtime_client_secret model=%s expires_at=%s",
            settings.openai_realtime_model,
            expires_at,
        )

        return VoiceSessionCredentials(
            client_secret=secret_value,
            expires_at=int(expires_at) if expires_at is not None else None,
            model=settings.openai_realtime_model,
            voice=settings.openai_realtime_voice,
            realtime_url=REALTIME_CALLS_URL,
            session=session_dict,
        )


def get_voice_provider() -> OpenAIRealtimeProvider:
    return OpenAIRealtimeProvider()
