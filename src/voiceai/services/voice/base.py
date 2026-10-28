"""Abstract voice interview provider interface."""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(slots=True)
class VoiceSessionCredentials:
    """Short-lived credentials for a browser WebRTC session."""

    client_secret: str
    expires_at: int | None
    model: str
    voice: str
    realtime_url: str
    session: dict[str, Any]


class VoiceInterviewProvider(Protocol):
    """Provider abstraction so OpenAI Realtime can be swapped later."""

    async def create_ephemeral_session(
        self,
        *,
        instructions: str,
        safety_identifier: str | None = None,
    ) -> VoiceSessionCredentials:
        """Mint short-lived client credentials for browser WebRTC."""
        ...
