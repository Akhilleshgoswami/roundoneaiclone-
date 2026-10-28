"""Business logic for candidate registration and listing."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.models.candidate import Candidate
from voiceai.schemas.candidate import CandidateCreate
from voiceai.services.organization import require_organization


async def create_candidate(
    session: AsyncSession,
    payload: CandidateCreate,
) -> Candidate:
    """Create and persist a candidate."""

    await require_organization(session, payload.organization_id)

    candidate = Candidate(**payload.model_dump())
    session.add(candidate)
    await session.commit()
    await session.refresh(candidate)
    return candidate


async def list_candidates(
    session: AsyncSession,
    organization_id: UUID | None = None,
) -> list[Candidate]:
    """List candidates, optionally filtered by organization."""

    statement = select(Candidate).order_by(Candidate.created_at.desc())

    if organization_id is not None:
        statement = statement.where(Candidate.organization_id == organization_id)

    result = await session.scalars(statement)
    return list(result.all())
