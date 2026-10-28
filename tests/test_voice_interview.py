"""Tests for realtime voice interview session lifecycle."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import AsyncClient

from voiceai.services.voice.base import VoiceSessionCredentials


@pytest.fixture
async def interview_id(client: AsyncClient, application_id: str) -> str:
    response = await client.post(
        "/api/v1/interviews",
        json={"application_id": application_id},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_start_valid_interview(client: AsyncClient, interview_id: str) -> None:
    response = await client.post(f"/api/v1/interviews/{interview_id}/start")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["interview_id"] == interview_id
    assert body["status"] == "in_progress"
    assert body["opening_question"]
    assert isinstance(body["question_plan"], list)
    assert len(body["question_plan"]) >= 1


@pytest.mark.asyncio
async def test_start_rejects_invalid_interview_id(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/interviews/{uuid4()}/start")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_voice_session_requires_provider(
    client: AsyncClient,
    interview_id: str,
) -> None:
    with patch(
        "voiceai.services.interview_session.get_voice_provider",
        side_effect=RuntimeError("OPENAI_API_KEY is required"),
    ):
        response = await client.post(f"/api/v1/interviews/{interview_id}/voice-session")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_voice_session_mints_ephemeral_credentials(
    client: AsyncClient,
    interview_id: str,
) -> None:
    fake = VoiceSessionCredentials(
        client_secret="ek_test_secret",
        expires_at=1_700_000_000,
        model="gpt-realtime",
        voice="marin",
        realtime_url="https://api.openai.com/v1/realtime/calls",
        session={"id": "sess_test"},
    )
    mock_provider = AsyncMock()
    mock_provider.create_ephemeral_session = AsyncMock(return_value=fake)

    with patch(
        "voiceai.services.interview_session.get_voice_provider",
        return_value=mock_provider,
    ):
        response = await client.post(f"/api/v1/interviews/{interview_id}/voice-session")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["client_secret"] == "ek_test_secret"
    assert body["realtime_url"].endswith("/realtime/calls")
    assert body["model"] == "gpt-realtime"
    mock_provider.create_ephemeral_session.assert_awaited()


@pytest.mark.asyncio
async def test_transcript_persistence_and_idempotency(
    client: AsyncClient,
    interview_id: str,
) -> None:
    await client.post(f"/api/v1/interviews/{interview_id}/start")

    first = await client.post(
        f"/api/v1/interviews/{interview_id}/transcript-events",
        json={
            "speaker": "interviewer",
            "content": "Tell me about a recent backend project.",
            "provider_event_id": "evt-1",
            "at": datetime.now(UTC).isoformat(),
        },
    )
    assert first.status_code == 201, first.text
    turn_id = first.json()["id"]

    duplicate = await client.post(
        f"/api/v1/interviews/{interview_id}/transcript-events",
        json={
            "speaker": "interviewer",
            "content": "Tell me about a recent backend project.",
            "provider_event_id": "evt-1",
        },
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == turn_id

    candidate = await client.post(
        f"/api/v1/interviews/{interview_id}/transcript-events",
        json={
            "speaker": "candidate",
            "content": "I built FastAPI services with PostgreSQL.",
            "provider_event_id": "evt-2",
        },
    )
    assert candidate.status_code == 201

    transcript = await client.get(f"/api/v1/interviews/{interview_id}/transcript")
    assert transcript.status_code == 200
    body = transcript.json()
    assert len(body["turns"]) == 2
    assert body["turns"][0]["sequence"] == 1
    assert body["turns"][1]["speaker"] == "candidate"


@pytest.mark.asyncio
async def test_end_interview_produces_evaluation(
    client: AsyncClient,
    interview_id: str,
) -> None:
    await client.post(f"/api/v1/interviews/{interview_id}/start")
    await client.post(
        f"/api/v1/interviews/{interview_id}/transcript-events",
        json={
            "speaker": "candidate",
            "content": "I designed PostgreSQL schemas and FastAPI endpoints.",
            "provider_event_id": "evt-end-1",
        },
    )

    ended = await client.post(f"/api/v1/interviews/{interview_id}/end")
    assert ended.status_code == 200, ended.text
    body = ended.json()
    assert body["status"] == "completed"
    assert body["evaluation"] is not None
    assert body["evaluation"]["summary"]

    fetched = await client.get(f"/api/v1/interviews/{interview_id}/evaluation")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_session_status_endpoint(
    client: AsyncClient,
    interview_id: str,
) -> None:
    await client.post(f"/api/v1/interviews/{interview_id}/start")
    response = await client.get(f"/api/v1/interviews/{interview_id}/session")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["question_count"] >= 1


@pytest.mark.asyncio
async def test_existing_application_interview_endpoints_still_work(
    client: AsyncClient,
    application_id: str,
) -> None:
    created = await client.post(
        "/api/v1/interviews",
        json={"application_id": application_id},
    )
    assert created.status_code == 201
    interview_id = created.json()["id"]

    listed = await client.get("/api/v1/interviews")
    assert listed.status_code == 200
    assert any(item["id"] == interview_id for item in listed.json())

    apps = await client.get("/api/v1/applications")
    assert apps.status_code == 200
    assert any(item["id"] == application_id for item in apps.json())
