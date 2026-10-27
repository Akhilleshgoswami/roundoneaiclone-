"""Pydantic schemas for candidate create and read APIs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateCreate(BaseModel):
    organization_id: UUID
    full_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    resume_filename: str | None = Field(default=None, max_length=255)
    resume_text: str | None = None


class CandidateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    full_name: str
    email: EmailStr
    resume_filename: str | None
    resume_text: str | None
    created_at: datetime
    updated_at: datetime
