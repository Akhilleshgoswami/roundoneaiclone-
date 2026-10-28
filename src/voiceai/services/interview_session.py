"""Interview session lifecycle: start, voice credentials, transcript, end, evaluate."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from voiceai.core.config import get_settings
from voiceai.graphs.interview_graph import interview_eval_graph, interview_plan_graph
from voiceai.models.application import JobApplication
from voiceai.models.candidate import Candidate
from voiceai.models.interview import Interview
from voiceai.models.interview_turn import InterviewTurn
from voiceai.models.job import Job
from voiceai.schemas.voice_interview import (
    InterviewEvaluation,
    InterviewEvaluationResponse,
    InterviewSessionStatus,
    InterviewStartResponse,
    TranscriptEventIn,
    TranscriptListResponse,
    TranscriptTurnRead,
    VoiceSessionCreateResponse,
)
from voiceai.services.interview import (
    InterviewNotFoundError,
    InvalidInterviewStatusTransitionError,
)
from voiceai.services.redis_client import (
    clear_session_state,
    get_session_state,
    set_session_state,
)
from voiceai.services.voice import get_voice_provider

logger = logging.getLogger(__name__)


class ActiveSessionExistsError(Exception):
    """Raised when an interview already has an active voice session."""


class VoiceProviderUnavailableError(Exception):
    """Raised when realtime voice cannot be initialized."""


async def _load_interview_context(
    session: AsyncSession,
    interview_id: uuid.UUID,
) -> tuple[Interview, JobApplication, Job, Candidate]:
    interview = await session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFoundError(f"Interview not found: {interview_id}")

    application = await session.get(JobApplication, interview.application_id)
    if application is None:
        raise InterviewNotFoundError("Application for interview not found")

    job = await session.get(Job, application.job_id)
    candidate = await session.get(Candidate, application.candidate_id)
    if job is None or candidate is None:
        raise InterviewNotFoundError("Job or candidate for interview not found")
    return interview, application, job, candidate


async def start_interview_session(
    session: AsyncSession,
    interview_id: uuid.UUID,
) -> InterviewStartResponse:
    """Mark interview in progress and generate a question plan."""

    interview, _, job, candidate = await _load_interview_context(session, interview_id)
    settings = get_settings()

    if interview.status in {"completed", "failed"}:
        raise InvalidInterviewStatusTransitionError(
            f"Cannot start interview in status {interview.status!r}."
        )

    if interview.status == "in_progress" and interview.question_plan:
        return InterviewStartResponse(
            interview_id=interview.id,
            status=interview.status,
            opening_question=(
                interview.question_plan[0]
                if isinstance(interview.question_plan, list) and interview.question_plan
                else "Let's begin."
            ),
            question_plan=list(interview.question_plan or []),
            voice_available=bool(settings.openai_api_key),
        )

    plan_state = await interview_plan_graph.ainvoke(
        {
            "job_title": job.title,
            "job_description": job.description,
            "required_skills": job.required_skills,
            "candidate_name": candidate.full_name,
            "resume_text": candidate.resume_text or "",
            "max_questions": settings.interview_max_questions,
        }
    )

    questions = list(plan_state.get("questions") or [])
    opening = str(plan_state.get("opening_question") or (questions[0] if questions else ""))
    instructions = str(plan_state.get("instructions") or "")

    now = datetime.now(UTC)
    interview.status = "in_progress"
    if interview.started_at is None:
        interview.started_at = now
    interview.question_plan = questions
    await session.commit()
    await session.refresh(interview)

    await set_session_state(
        str(interview.id),
        {
            "status": "in_progress",
            "opening_question": opening,
            "instructions": instructions,
            "question_plan": questions,
            "started_at": now.isoformat(),
        },
        ttl=settings.interview_max_minutes * 60 + 600,
    )

    return InterviewStartResponse(
        interview_id=interview.id,
        status=interview.status,
        opening_question=opening,
        question_plan=questions,
        voice_available=bool(settings.openai_api_key),
    )


async def create_voice_session(
    session: AsyncSession,
    interview_id: uuid.UUID,
) -> VoiceSessionCreateResponse:
    """Mint short-lived OpenAI Realtime credentials for browser WebRTC."""

    interview, _, job, candidate = await _load_interview_context(session, interview_id)
    settings = get_settings()

    if interview.status in {"completed", "failed"}:
        raise InvalidInterviewStatusTransitionError(
            f"Cannot create voice session for status {interview.status!r}."
        )

    if interview.status == "scheduled":
        await start_interview_session(session, interview_id)
        await session.refresh(interview)

    redis_state = await get_session_state(str(interview.id)) or {}
    instructions = redis_state.get("instructions")
    opening = redis_state.get("opening_question")
    if not instructions:
        plan_state = await interview_plan_graph.ainvoke(
            {
                "job_title": job.title,
                "job_description": job.description,
                "required_skills": job.required_skills,
                "candidate_name": candidate.full_name,
                "resume_text": candidate.resume_text or "",
                "max_questions": settings.interview_max_questions,
            }
        )
        instructions = plan_state.get("instructions")
        opening = plan_state.get("opening_question")
        interview.question_plan = list(plan_state.get("questions") or [])
        await session.commit()

    try:
        provider = get_voice_provider()
        creds = await provider.create_ephemeral_session(
            instructions=str(instructions),
            safety_identifier=str(candidate.id),
        )
    except Exception as exc:
        logger.exception("voice_session_mint_failed interview_id=%s", interview_id)
        raise VoiceProviderUnavailableError(str(exc)) from exc

    interview.provider_session_id = (
        (creds.session or {}).get("id")
        or interview.provider_session_id
        or f"ek-{uuid.uuid4().hex[:16]}"
    )
    await session.commit()

    await set_session_state(
        str(interview.id),
        {
            "status": "voice_ready",
            "opening_question": opening,
            "instructions": instructions,
            "question_plan": interview.question_plan,
            "provider_session_id": interview.provider_session_id,
            "voice_model": creds.model,
        },
        ttl=settings.interview_max_minutes * 60 + 600,
    )

    return VoiceSessionCreateResponse(
        interview_id=interview.id,
        status=interview.status,
        client_secret=creds.client_secret,
        expires_at=creds.expires_at,
        model=creds.model,
        voice=creds.voice,
        realtime_url=creds.realtime_url,
        opening_question=opening,
        instructions_preview=(str(instructions)[:280] if instructions else None),
    )


async def get_interview_session_status(
    session: AsyncSession,
    interview_id: uuid.UUID,
) -> InterviewSessionStatus:
    interview = await session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFoundError(f"Interview not found: {interview_id}")

    turn_count = await session.scalar(
        select(func.count())
        .select_from(InterviewTurn)
        .where(InterviewTurn.interview_id == interview_id)
    )
    redis_state = await get_session_state(str(interview_id))
    plan = interview.question_plan or []
    return InterviewSessionStatus(
        interview_id=interview.id,
        status=interview.status,
        provider_session_id=interview.provider_session_id,
        started_at=interview.started_at,
        completed_at=interview.completed_at,
        question_count=len(plan) if isinstance(plan, list) else 0,
        turn_count=int(turn_count or 0),
        redis_state=redis_state,
    )


async def append_transcript_event(
    session: AsyncSession,
    interview_id: uuid.UUID,
    event: TranscriptEventIn,
) -> TranscriptTurnRead:
    interview = await session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFoundError(f"Interview not found: {interview_id}")

    if event.provider_event_id:
        existing = await session.scalar(
            select(InterviewTurn).where(
                InterviewTurn.interview_id == interview_id,
                InterviewTurn.provider_event_id == event.provider_event_id,
            )
        )
        if existing is not None:
            return TranscriptTurnRead.model_validate(existing)

    next_seq = await session.scalar(
        select(func.coalesce(func.max(InterviewTurn.sequence), 0)).where(
            InterviewTurn.interview_id == interview_id
        )
    )
    sequence = int(next_seq or 0) + 1
    turn = InterviewTurn(
        interview_id=interview_id,
        speaker=event.speaker,
        content=event.content.strip(),
        sequence=sequence,
        provider_event_id=event.provider_event_id,
    )
    session.add(turn)

    role = "assistant" if event.speaker == "interviewer" else "user"
    transcript = list(interview.transcript or [])
    transcript.append(
        {
            "role": role,
            "speaker": event.speaker,
            "content": event.content.strip(),
            "at": (event.at or datetime.now(UTC)).isoformat(),
        }
    )
    interview.transcript = transcript

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        if event.provider_event_id:
            existing = await session.scalar(
                select(InterviewTurn).where(
                    InterviewTurn.interview_id == interview_id,
                    InterviewTurn.provider_event_id == event.provider_event_id,
                )
            )
            if existing is not None:
                return TranscriptTurnRead.model_validate(existing)
        raise

    await session.refresh(turn)
    return TranscriptTurnRead.model_validate(turn)


async def get_transcript(
    session: AsyncSession,
    interview_id: uuid.UUID,
) -> TranscriptListResponse:
    interview = await session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFoundError(f"Interview not found: {interview_id}")

    result = await session.scalars(
        select(InterviewTurn)
        .where(InterviewTurn.interview_id == interview_id)
        .order_by(InterviewTurn.sequence.asc())
    )
    turns = list(result.all())
    return TranscriptListResponse(
        interview_id=interview.id,
        turns=[TranscriptTurnRead.model_validate(t) for t in turns],
        transcript=list(interview.transcript or []),
    )


async def end_interview_session(
    session: AsyncSession,
    interview_id: uuid.UUID,
    *,
    run_evaluation: bool = True,
) -> InterviewEvaluationResponse:
    interview, _, job, candidate = await _load_interview_context(session, interview_id)

    if interview.status not in {"in_progress", "scheduled", "completed"}:
        raise InvalidInterviewStatusTransitionError(
            f"Cannot end interview in status {interview.status!r}."
        )

    now = datetime.now(UTC)
    if interview.status != "completed":
        interview.status = "completed"
        if interview.completed_at is None:
            interview.completed_at = now
        await session.commit()

    evaluation_payload: dict[str, Any] | None = interview.evaluation
    if run_evaluation and not evaluation_payload:
        transcript_payload = list(interview.transcript or [])
        if not transcript_payload:
            turns = await get_transcript(session, interview_id)
            transcript_payload = [
                {"speaker": t.speaker, "content": t.content} for t in turns.turns
            ]
        eval_state = await interview_eval_graph.ainvoke(
            {
                "job_title": job.title,
                "job_description": job.description,
                "required_skills": job.required_skills,
                "candidate_name": candidate.full_name,
                "resume_text": candidate.resume_text or "",
                "transcript": transcript_payload,
            }
        )
        evaluation_payload = dict(eval_state.get("evaluation") or {})
        interview.evaluation = evaluation_payload
        overall = evaluation_payload.get("overall_score")
        interview.overall_score = float(overall) if overall is not None else None
        criteria = evaluation_payload.get("criteria") or []
        interview.skill_scores = {
            str(item.get("name")): item.get("score")
            for item in criteria
            if item.get("name") is not None
        }
        interview.summary = evaluation_payload.get("summary")
        await session.commit()

    await clear_session_state(str(interview_id))

    parsed: InterviewEvaluation | None = None
    if evaluation_payload:
        parsed = InterviewEvaluation.model_validate(evaluation_payload)

    return InterviewEvaluationResponse(
        interview_id=interview.id,
        status=interview.status,
        evaluation=parsed,
        overall_score=interview.overall_score,
        skill_scores=interview.skill_scores,
        summary=interview.summary,
    )


async def get_evaluation(
    session: AsyncSession,
    interview_id: uuid.UUID,
) -> InterviewEvaluationResponse:
    interview = await session.get(Interview, interview_id)
    if interview is None:
        raise InterviewNotFoundError(f"Interview not found: {interview_id}")

    parsed = None
    if interview.evaluation:
        parsed = InterviewEvaluation.model_validate(interview.evaluation)

    return InterviewEvaluationResponse(
        interview_id=interview.id,
        status=interview.status,
        evaluation=parsed,
        overall_score=interview.overall_score,
        skill_scores=interview.skill_scores,
        summary=interview.summary,
    )
