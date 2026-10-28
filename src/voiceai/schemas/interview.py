"""Pydantic schemas for interview sessions."""

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

InterviewStatus = Literal[
    "scheduled",
    "in_progress",
    "completed",
    "failed",
]


def ensure_aware_datetime(value: datetime | None) -> datetime | None:
    """Normalize datetimes to timezone-aware UTC."""

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class InterviewCreate(BaseModel):
    """Request to create an interview for an application."""

    application_id: UUID = Field(
        description=(
            "Copy `id` from POST /api/v1/applications. "
            "Do not use Swagger's example UUID."
        ),
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Optional timezone-aware schedule. Naive values are treated as UTC.",
    )

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, value: datetime | None) -> datetime | None:
        return ensure_aware_datetime(value)


class InterviewScheduleUpdate(BaseModel):
    """Partial update for interview scheduling.

    - Omitted `scheduled_at` means leave the current value unchanged.
    - Explicit `null` clears the schedule.
    """

    model_config = ConfigDict(extra="forbid")

    scheduled_at: datetime | None = Field(default=None)

    @field_validator("scheduled_at")
    @classmethod
    def validate_scheduled_at(cls, value: datetime | None) -> datetime | None:
        return ensure_aware_datetime(value)


class InterviewStatusUpdate(BaseModel):
    """Request to update the interview lifecycle status."""

    status: InterviewStatus


class InterviewRead(BaseModel):
    """Interview response schema aligned with the ORM model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    status: str
    scheduled_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    provider_session_id: str | None
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    question_plan: list[Any] | None = None
    evaluation: dict[str, Any] | None = None
    overall_score: float | None = None
    skill_scores: dict[str, Any] | None = None
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
