"""HTTP endpoints for managing candidates."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.db.session import get_db_session
from voiceai.schemas.candidate import CandidateCreate, CandidateRead
from voiceai.services.candidate import create_candidate, list_candidates

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])

DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    response_model=CandidateRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_endpoint(
    payload: CandidateCreate,
    session: DatabaseSession,
) -> CandidateRead:
    """Register a candidate."""

    candidate = await create_candidate(session, payload)
    return CandidateRead.model_validate(candidate)


@router.get("", response_model=list[CandidateRead])
async def list_candidates_endpoint(
    session: DatabaseSession,
    organization_id: Annotated[UUID | None, Query()] = None,
) -> list[CandidateRead]:
    """List candidates, optionally filtered by organization."""

    candidates = await list_candidates(session, organization_id)
    return [CandidateRead.model_validate(candidate) for candidate in candidates]
