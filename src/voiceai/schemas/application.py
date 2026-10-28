"""Pydantic schemas for job applications."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ApplicationStatus = Literal[
    "applied",
    "screening",
    "shortlisted",
    "interview",
    "rejected",
    "hired",
]


class ApplicationCreate(BaseModel):
    """Use real ids from create/list responses — not Swagger placeholder UUIDs."""

    job_id: uuid.UUID = Field(
        description=(
            "Copy `id` from the POST /api/v1/jobs response body. "
            "Do not use Swagger's example UUID (3fa85f64-...)."
        ),
    )
    candidate_id: uuid.UUID = Field(
        description=(
            "Copy `id` from the POST /api/v1/candidates response body. "
            "Do not use Swagger's example UUID (3fa85f64-...)."
        ),
    )


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime
