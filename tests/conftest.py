"""Shared fixtures for VoiceAI API tests."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from voiceai.db.session import engine
from voiceai.main import app
from voiceai.models import Base


@pytest.fixture(autouse=True)
async def prepare_schema() -> AsyncIterator[None]:
    """Ensure tables exist for integration tests."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def organization_id(client: AsyncClient) -> str:
    response = await client.post("/api/v1/organizations/demo")
    assert response.status_code == 200, response.text
    return response.json()["id"]


@pytest.fixture
async def job_id(client: AsyncClient, organization_id: str) -> str:
    response = await client.post(
        "/api/v1/jobs",
        json={
            "organization_id": organization_id,
            "title": "Backend Engineer",
            "description": "Build APIs and interview tooling for hiring workflows.",
            "required_skills": "Python, FastAPI, PostgreSQL",
            "status": "published",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
async def candidate_id(client: AsyncClient, organization_id: str) -> str:
    response = await client.post(
        "/api/v1/candidates",
        json={
            "organization_id": organization_id,
            "full_name": "Test Candidate",
            "email": f"candidate-{uuid4().hex[:10]}@example.com",
            "resume_text": "Python engineer with FastAPI experience.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture
async def application_id(
    client: AsyncClient,
    job_id: str,
    candidate_id: str,
) -> str:
    response = await client.post(
        "/api/v1/applications",
        json={"job_id": job_id, "candidate_id": candidate_id},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]
