from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.models.job import Job
from voiceai.schemas.job import JobCreate


async def create_job(session: AsyncSession, payload: JobCreate) -> Job:
    job = Job(**payload.model_dump())
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def list_jobs(
    session: AsyncSession, organization_id: UUID | None = None
) -> list[Job]:
    statement = select(Job).order_by(Job.created_at.desc())

    if organization_id is not None:
        statement = statement.where(Job.organization_id == organization_id)
    result = await session.scalars(statement)
    return list(result.all())
