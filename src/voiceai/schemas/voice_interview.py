"""Schemas for realtime voice interview sessions and evaluation."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class VoiceSessionCreateResponse(BaseModel):
    interview_id: UUID
    status: str
    client_secret: str
    expires_at: int | None = None
    model: str
    voice: str
    realtime_url: str
    opening_question: str | None = None
    instructions_preview: str | None = None


class InterviewSessionStatus(BaseModel):
    interview_id: UUID
    status: str
    provider_session_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    question_count: int = 0
    turn_count: int = 0
    redis_state: dict[str, Any] | None = None


class TranscriptEventIn(BaseModel):
    speaker: Literal["interviewer", "candidate"]
    content: str = Field(min_length=1, max_length=20000)
    provider_event_id: str | None = Field(default=None, max_length=200)
    at: datetime | None = None


class TranscriptTurnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    interview_id: UUID
    speaker: str
    content: str
    sequence: int
    provider_event_id: str | None
    created_at: datetime


class TranscriptListResponse(BaseModel):
    interview_id: UUID
    turns: list[TranscriptTurnRead]
    transcript: list[dict[str, Any]]


class CriterionScore(BaseModel):
    name: str
    score: float | None = None
    evidence: str
    assessment: str


class InterviewEvaluation(BaseModel):
    overall_score: float | None = None
    criteria: list[CriterionScore] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    summary: str
    insufficient_evidence: bool = False


class InterviewEvaluationResponse(BaseModel):
    interview_id: UUID
    status: str
    evaluation: InterviewEvaluation | None = None
    overall_score: float | None = None
    skill_scores: dict[str, Any] | None = None
    summary: str | None = None


class InterviewStartResponse(BaseModel):
    interview_id: UUID
    status: str
    opening_question: str
    question_plan: list[str]
    voice_available: bool
