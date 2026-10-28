"""Integration tests for application + interview scheduling consistency."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_application_create_without_scheduled_at(
    client: AsyncClient,
    job_id: str,
    candidate_id: str,
) -> None:
    response = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "candidate_id": candidate_id},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert "scheduled_at" not in body
    assert body["status"] == "applied"
    assert body["job_id"] == job_id
    assert body["candidate_id"] == candidate_id


@pytest.mark.asyncio
async def test_application_endpoints_continue_working(
    client: AsyncClient,
    application_id: str,
) -> None:
    listed = await client.get("/api/v1/applications")
    assert listed.status_code == 200
    assert any(item["id"] == application_id for item in listed.json())

    fetched = await client.get(f"/api/v1/applications/{application_id}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == application_id

    patched = await client.patch(
        f"/api/v1/applications/{application_id}/status",
        json={"status": "screening"},
    )
    assert patched.status_code == 200
    assert patched.json()["status"] == "screening"


@pytest.mark.asyncio
async def test_interview_create_without_scheduled_at(
    client: AsyncClient,
    application_id: str,
) -> None:
    response = await client.post(
        "/api/v1/interviews",
        json={"application_id": application_id},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["application_id"] == application_id
    assert body["status"] == "scheduled"
    assert body["scheduled_at"] is None
    assert body["started_at"] is None
    assert body["completed_at"] is None
    assert isinstance(body["transcript"], list)


@pytest.mark.asyncio
async def test_interview_create_with_scheduled_at(
    client: AsyncClient,
    application_id: str,
) -> None:
    scheduled = datetime(2026, 11, 1, 15, 30, tzinfo=UTC)
    response = await client.post(
        "/api/v1/interviews",
        json={
            "application_id": application_id,
            "scheduled_at": scheduled.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["scheduled_at"] is not None
    parsed = datetime.fromisoformat(body["scheduled_at"])
    assert parsed == scheduled


@pytest.mark.asyncio
async def test_interview_create_naive_datetime_normalized_to_utc(
    client: AsyncClient,
    application_id: str,
) -> None:
    response = await client.post(
        "/api/v1/interviews",
        json={
            "application_id": application_id,
            "scheduled_at": "2026-11-02T10:00:00",
        },
    )
    assert response.status_code == 201, response.text
    parsed = datetime.fromisoformat(response.json()["scheduled_at"])
    assert parsed.tzinfo is not None
    assert parsed == datetime(2026, 11, 2, 10, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_interview_update_schedule_and_retrieve(
    client: AsyncClient,
    application_id: str,
) -> None:
    created = await client.post(
        "/api/v1/interviews",
        json={"application_id": application_id},
    )
    interview_id = created.json()["id"]

    scheduled = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
    updated = await client.patch(
        f"/api/v1/interviews/{interview_id}/schedule",
        json={"scheduled_at": scheduled.isoformat()},
    )
    assert updated.status_code == 200, updated.text
    assert datetime.fromisoformat(updated.json()["scheduled_at"]) == scheduled

    fetched = await client.get(f"/api/v1/interviews/{interview_id}")
    assert fetched.status_code == 200
    assert datetime.fromisoformat(fetched.json()["scheduled_at"]) == scheduled

    cleared = await client.patch(
        f"/api/v1/interviews/{interview_id}/schedule",
        json={"scheduled_at": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["scheduled_at"] is None


@pytest.mark.asyncio
async def test_interview_schedule_omit_leaves_value_unchanged(
    client: AsyncClient,
    application_id: str,
) -> None:
    scheduled = datetime(2026, 12, 5, 12, 0, tzinfo=UTC)
    created = await client.post(
        "/api/v1/interviews",
        json={
            "application_id": application_id,
            "scheduled_at": scheduled.isoformat(),
        },
    )
    interview_id = created.json()["id"]

    untouched = await client.patch(
        f"/api/v1/interviews/{interview_id}/schedule",
        json={},
    )
    assert untouched.status_code == 200
    assert datetime.fromisoformat(untouched.json()["scheduled_at"]) == scheduled


@pytest.mark.asyncio
async def test_interview_invalid_application_reference(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/interviews",
        json={"application_id": str(uuid4())},
    )
    assert response.status_code == 404
    assert "Application not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_interview_invalid_datetime_input(
    client: AsyncClient,
    application_id: str,
) -> None:
    response = await client.post(
        "/api/v1/interviews",
        json={
            "application_id": application_id,
            "scheduled_at": "not-a-datetime",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_interview_status_sets_timestamps(
    client: AsyncClient,
    application_id: str,
) -> None:
    created = await client.post(
        "/api/v1/interviews",
        json={"application_id": application_id},
    )
    interview_id = created.json()["id"]

    started = await client.patch(
        f"/api/v1/interviews/{interview_id}/status",
        json={"status": "in_progress"},
    )
    assert started.status_code == 200, started.text
    assert started.json()["started_at"] is not None

    completed = await client.patch(
        f"/api/v1/interviews/{interview_id}/status",
        json={"status": "completed"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_interview_invalid_status_transition(
    client: AsyncClient,
    application_id: str,
) -> None:
    created = await client.post(
        "/api/v1/interviews",
        json={"application_id": application_id},
    )
    interview_id = created.json()["id"]

    response = await client.patch(
        f"/api/v1/interviews/{interview_id}/status",
        json={"status": "completed"},
    )
    assert response.status_code == 409
