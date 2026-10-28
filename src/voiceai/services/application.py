"""Business logic for job applications."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.models.application import JobApplication
from voiceai.models.candidate import Candidate
from voiceai.models.job import Job
from voiceai.schemas.application import ApplicationCreate


class JobNotFoundError(Exception):
    """Raised when a job_id does not exist."""


class CandidateNotFoundError(Exception):
    """Raised when a candidate_id does not exist."""


class DuplicateApplicationError(Exception):
    """Raised when the candidate already applied to the job."""


async def create_application(
    session: AsyncSession,
    data: ApplicationCreate,
) -> JobApplication:
    """Create an application after validating job and candidate exist."""

    job = await session.get(Job, data.job_id)
    if job is None:
        raise JobNotFoundError(
            f"Job not found: {data.job_id}. "
            "Create a job with POST /api/v1/jobs first."
        )

    candidate = await session.get(Candidate, data.candidate_id)
    if candidate is None:
        raise CandidateNotFoundError(
            f"Candidate not found: {data.candidate_id}. "
            "Create a candidate with POST /api/v1/candidates first."
        )

    existing = await session.scalar(
        select(JobApplication).where(
            JobApplication.job_id == data.job_id,
            JobApplication.candidate_id == data.candidate_id,
        )
    )
    if existing is not None:
        raise DuplicateApplicationError(
            f"Candidate {data.candidate_id} has already applied to job {data.job_id}."
        )

    application = JobApplication(
        job_id=data.job_id,
        candidate_id=data.candidate_id,
        status="applied",
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application


async def list_applications(
    session: AsyncSession,
    job_id: uuid.UUID | None = None,
    candidate_id: uuid.UUID | None = None,
) -> list[JobApplication]:
    statement = select(JobApplication).order_by(JobApplication.created_at.desc())
    if job_id is not None:
        statement = statement.where(JobApplication.job_id == job_id)
    if candidate_id is not None:
        statement = statement.where(JobApplication.candidate_id == candidate_id)
    result = await session.scalars(statement)
    return list(result.all())


async def get_application(
    session: AsyncSession,
    application_id: uuid.UUID,
) -> JobApplication | None:
    return await session.get(JobApplication, application_id)


async def update_application_status(
    session: AsyncSession,
    application_id: uuid.UUID,
    status: str,
) -> JobApplication | None:
    application = await session.get(JobApplication, application_id)
    if application is None:
        return None
    application.status = status
    await session.commit()
    await session.refresh(application)
    return application
