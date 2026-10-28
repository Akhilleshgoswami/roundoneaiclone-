"""Ensure interview scheduling columns exist.

Revision ID: 20261028_0001
Revises:
Create Date: 2026-10-28

Idempotent: safe on databases that already created tables via metadata.create_all.
Does not drop data. scheduled_at lives on interviews only (not job_applications).
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261028_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add interview scheduling columns only if they are missing."""

    op.execute(
        """
        ALTER TABLE interviews
            ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS started_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP WITH TIME ZONE,
            ADD COLUMN IF NOT EXISTS provider_session_id VARCHAR(200),
            ADD COLUMN IF NOT EXISTS transcript JSONB NOT NULL DEFAULT '[]'::jsonb,
            ADD COLUMN IF NOT EXISTS overall_score DOUBLE PRECISION,
            ADD COLUMN IF NOT EXISTS skill_scores JSONB,
            ADD COLUMN IF NOT EXISTS summary TEXT
        """
    )


def downgrade() -> None:
    """Do not drop scheduling columns — preserves existing interview data."""

    pass
