"""Pydantic schemas for job create and read APIs."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobCreate(BaseModel):
    organization_id: UUID
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10)
    required_skills: str = ""
    status: str = "draft"


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    title: str
    description: str
    required_skills: str
    status: str
    created_at: datetime
    updated_at: datetime
