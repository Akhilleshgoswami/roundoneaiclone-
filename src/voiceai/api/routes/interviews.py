"""REST API routes for interview sessions and realtime voice."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.db.session import get_db_session
from voiceai.schemas.interview import (
    InterviewCreate,
    InterviewRead,
    InterviewScheduleUpdate,
    InterviewStatusUpdate,
)
from voiceai.schemas.voice_interview import (
    InterviewEvaluationResponse,
    InterviewSessionStatus,
    InterviewStartResponse,
    TranscriptEventIn,
    TranscriptListResponse,
    TranscriptTurnRead,
    VoiceSessionCreateResponse,
)
from voiceai.services.interview import (
    ApplicationNotFoundError,
    InterviewNotFoundError,
    InvalidInterviewStatusTransitionError,
    create_interview,
    get_interview,
    list_interviews,
    update_interview_schedule,
    update_interview_status,
)
from voiceai.services.interview_session import (
    VoiceProviderUnavailableError,
    append_transcript_event,
    create_voice_session,
    end_interview_session,
    get_evaluation,
    get_interview_session_status,
    get_transcript,
    start_interview_session,
)

router = APIRouter(
    prefix="/api/v1/interviews",
    tags=["Interviews"],
)
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.post(
    "",
    response_model=InterviewRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_interview_endpoint(
    payload: InterviewCreate,
    session: DatabaseSession,
) -> InterviewRead:
    """Create an interview for an application (schedule optional)."""

    try:
        interview = await create_interview(session, payload)
    except ApplicationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return InterviewRead.model_validate(interview)


@router.get(
    "",
    response_model=list[InterviewRead],
)
async def list_interviews_endpoint(
    session: DatabaseSession,
    application_id: Annotated[UUID | None, Query()] = None,
) -> list[InterviewRead]:
    """List interviews, optionally filtered by application."""

    interviews = await list_interviews(
        session=session,
        application_id=application_id,
    )
    return [InterviewRead.model_validate(interview) for interview in interviews]


@router.get(
    "/{interview_id}",
    response_model=InterviewRead,
)
async def get_interview_endpoint(
    interview_id: UUID,
    session: DatabaseSession,
) -> InterviewRead:
    """Retrieve an interview by ID."""

    interview = await get_interview(session, interview_id)
    if interview is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview not found",
        )
    return InterviewRead.model_validate(interview)


@router.patch(
    "/{interview_id}/schedule",
    response_model=InterviewRead,
)
async def update_interview_schedule_endpoint(
    interview_id: UUID,
    payload: InterviewScheduleUpdate,
    session: DatabaseSession,
) -> InterviewRead:
    """Set or clear `scheduled_at` without changing status."""

    try:
        interview = await update_interview_schedule(
            session=session,
            interview_id=interview_id,
            data=payload,
        )
    except InterviewNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return InterviewRead.model_validate(interview)


@router.patch(
    "/{interview_id}/status",
    response_model=InterviewRead,
)
async def update_interview_status_endpoint(
    interview_id: UUID,
    payload: InterviewStatusUpdate,
    session: DatabaseSession,
) -> InterviewRead:
    """Update an interview's lifecycle status and timestamps."""

    try:
        interview = await update_interview_status(
            session=session,
            interview_id=interview_id,
            new_status=payload.status,
        )
    except InterviewNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidInterviewStatusTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return InterviewRead.model_validate(interview)


@router.post(
    "/{interview_id}/start",
    response_model=InterviewStartResponse,
)
async def start_interview_endpoint(
    interview_id: UUID,
    session: DatabaseSession,
) -> InterviewStartResponse:
    """Start an interview session and generate the question plan."""

    try:
        return await start_interview_session(session, interview_id)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidInterviewStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/{interview_id}/voice-session",
    response_model=VoiceSessionCreateResponse,
)
async def create_voice_session_endpoint(
    interview_id: UUID,
    session: DatabaseSession,
) -> VoiceSessionCreateResponse:
    """Mint short-lived OpenAI Realtime credentials for browser WebRTC."""

    try:
        return await create_voice_session(session, interview_id)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidInterviewStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except VoiceProviderUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Voice provider unavailable. Set OPENAI_API_KEY and ensure "
                f"Realtime access is enabled. ({exc})"
            ),
        ) from exc


@router.get(
    "/{interview_id}/session",
    response_model=InterviewSessionStatus,
)
async def get_session_endpoint(
    interview_id: UUID,
    session: DatabaseSession,
) -> InterviewSessionStatus:
    """Return current interview session status."""

    try:
        return await get_interview_session_status(session, interview_id)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{interview_id}/transcript-events",
    response_model=TranscriptTurnRead,
    status_code=status.HTTP_201_CREATED,
)
async def append_transcript_event_endpoint(
    interview_id: UUID,
    payload: TranscriptEventIn,
    session: DatabaseSession,
) -> TranscriptTurnRead:
    """Persist a transcript turn from the realtime client (idempotent)."""

    try:
        return await append_transcript_event(session, interview_id, payload)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{interview_id}/transcript",
    response_model=TranscriptListResponse,
)
async def get_transcript_endpoint(
    interview_id: UUID,
    session: DatabaseSession,
) -> TranscriptListResponse:
    """Fetch ordered transcript turns for an interview."""

    try:
        return await get_transcript(session, interview_id)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{interview_id}/end",
    response_model=InterviewEvaluationResponse,
)
async def end_interview_endpoint(
    interview_id: UUID,
    session: DatabaseSession,
) -> InterviewEvaluationResponse:
    """End the interview and generate a structured evaluation."""

    try:
        return await end_interview_session(session, interview_id, run_evaluation=True)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except InvalidInterviewStatusTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get(
    "/{interview_id}/evaluation",
    response_model=InterviewEvaluationResponse,
)
async def get_evaluation_endpoint(
    interview_id: UUID,
    session: DatabaseSession,
) -> InterviewEvaluationResponse:
    """Retrieve the structured interview evaluation."""

    try:
        return await get_evaluation(session, interview_id)
    except InterviewNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
