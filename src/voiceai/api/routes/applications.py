"""REST API routes for job applications."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.db.session import get_db_session
from voiceai.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationStatusUpdate,
)
from voiceai.services.application import (
    CandidateNotFoundError,
    DuplicateApplicationError,
    JobNotFoundError,
    create_application,
    get_application,
    list_applications,
    update_application_status,
)

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def create_application_endpoint(
    payload: ApplicationCreate,
    session: DatabaseSession,
) -> ApplicationRead:
    try:
        application = await create_application(session, payload)
    except JobNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except CandidateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except DuplicateApplicationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return ApplicationRead.model_validate(application)


@router.get("", response_model=list[ApplicationRead])
async def list_applications_endpoint(
    session: DatabaseSession,
    job_id: Annotated[UUID | None, Query()] = None,
    candidate_id: Annotated[UUID | None, Query()] = None,
) -> list[ApplicationRead]:
    applications = await list_applications(
        session=session,
        job_id=job_id,
        candidate_id=candidate_id,
    )
    return [ApplicationRead.model_validate(a) for a in applications]


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application_endpoint(
    application_id: UUID,
    session: DatabaseSession,
) -> ApplicationRead:
    application = await get_application(session, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return ApplicationRead.model_validate(application)


@router.patch("/{application_id}/status", response_model=ApplicationRead)
async def update_application_status_endpoint(
    application_id: UUID,
    payload: ApplicationStatusUpdate,
    session: DatabaseSession,
) -> ApplicationRead:
    application = await update_application_status(
        session=session,
        application_id=application_id,
        status=payload.status,
    )
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return ApplicationRead.model_validate(application)
