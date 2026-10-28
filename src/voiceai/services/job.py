"""Business logic for job create and list."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.models.job import Job
from voiceai.schemas.job import JobCreate
from voiceai.services.organization import require_organization


async def create_job(session: AsyncSession, payload: JobCreate) -> Job:
    """Create and persist a job for an existing organization."""

    await require_organization(session, payload.organization_id)

    job = Job(**payload.model_dump())
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def list_jobs(
    session: AsyncSession,
    organization_id: UUID | None = None,
) -> list[Job]:
    statement = select(Job).order_by(Job.created_at.desc())

    if organization_id is not None:
        statement = statement.where(Job.organization_id == organization_id)

    result = await session.scalars(statement)
    return list(result.all())
