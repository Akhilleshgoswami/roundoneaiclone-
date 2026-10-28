"""Business logic for interview sessions."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.models.application import JobApplication
from voiceai.models.interview import Interview
from voiceai.schemas.interview import InterviewCreate, InterviewScheduleUpdate

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "scheduled": {"in_progress", "failed", "scheduled"},
    "in_progress": {"completed", "failed", "in_progress"},
    "completed": {"completed"},
    "failed": {"failed"},
}


class ApplicationNotFoundError(Exception):
    """Raised when an interview references a missing application."""


class InterviewNotFoundError(Exception):
    """Raised when an interview cannot be found."""


class InvalidInterviewStatusTransitionError(Exception):
    """Raised when a status transition is not allowed."""


async def create_interview(
    session: AsyncSession,
    data: InterviewCreate,
) -> Interview:
    """Create an interview for an existing application."""

    application = await session.get(JobApplication, data.application_id)
    if application is None:
        raise ApplicationNotFoundError(
            f"Application not found: {data.application_id}. "
            "Create one with POST /api/v1/applications first."
        )

    interview = Interview(
        application_id=data.application_id,
        scheduled_at=data.scheduled_at,
        status="scheduled",
        transcript=[],
    )

    session.add(interview)
    await session.commit()
    await session.refresh(interview)
    return interview


async def list_interviews(
    session: AsyncSession,
    application_id: UUID | None = None,
) -> list[Interview]:
    """List interviews, optionally filtered by application."""

    statement = select(Interview).order_by(Interview.created_at.desc())

    if application_id is not None:
        statement = statement.where(Interview.application_id == application_id)

    result = await session.scalars(statement)
    return list(result.all())


async def get_interview(
    session: AsyncSession,
    interview_id: UUID,
) -> Interview | None:
    """Retrieve an interview by ID."""

    return await session.get(Interview, interview_id)


async def update_interview_schedule(
    session: AsyncSession,
    interview_id: UUID,
    data: InterviewScheduleUpdate,
) -> Interview:
    """Update or clear scheduled_at without touching omitted fields."""

    interview = await session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFoundError(f"Interview not found: {interview_id}")

    # Distinguish omitted vs explicit null via model_fields_set.
    if "scheduled_at" in data.model_fields_set:
        interview.scheduled_at = data.scheduled_at

    await session.commit()
    await session.refresh(interview)
    return interview


async def update_interview_status(
    session: AsyncSession,
    interview_id: UUID,
    new_status: str,
) -> Interview:
    """Update interview status and lifecycle timestamps."""

    interview = await session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFoundError(f"Interview not found: {interview_id}")

    current = interview.status
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current, set())
    if new_status not in allowed:
        raise InvalidInterviewStatusTransitionError(
            f"Cannot transition interview from {current!r} to {new_status!r}."
        )

    now = datetime.now(UTC)
    interview.status = new_status

    if new_status == "in_progress" and interview.started_at is None:
        interview.started_at = now

    if new_status in {"completed", "failed"} and interview.completed_at is None:
        interview.completed_at = now

    await session.commit()
    await session.refresh(interview)
    return interview


async def set_provider_session_id(
    session: AsyncSession,
    interview_id: UUID,
    provider_session_id: str,
) -> Interview | None:
    """Store the external voice provider's session identifier."""

    interview = await session.get(Interview, interview_id)
    if interview is None:
        return None

    interview.provider_session_id = provider_session_id
    await session.commit()
    await session.refresh(interview)
    return interview
