"""Job management API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.db.session import get_db_session
from voiceai.schemas.job import JobCreate, JobRead
from voiceai.services.job import create_job, list_jobs
from voiceai.services.organization import OrganizationNotFoundError

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job_endpoint(
    payload: JobCreate,
    session: DatabaseSession,
) -> JobRead:
    """Create a job for an organization."""

    try:
        job = await create_job(session, payload)
    except OrganizationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return JobRead.model_validate(job)


@router.get("", response_model=list[JobRead])
async def list_jobs_endpoint(
    session: DatabaseSession,
    organization_id: Annotated[UUID | None, Query()] = None,
) -> list[JobRead]:
    """List jobs, optionally filtered by organization."""

    jobs = await list_jobs(session, organization_id)
    return [JobRead.model_validate(job) for job in jobs]
