"""Add interview turns, question_plan, and evaluation columns.

Revision ID: 20261028_0002
Revises: 20261028_0001
Create Date: 2026-10-28
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20261028_0002"
down_revision: Union[str, Sequence[str], None] = "20261028_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE interviews
            ADD COLUMN IF NOT EXISTS question_plan JSONB,
            ADD COLUMN IF NOT EXISTS evaluation JSONB
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_turns (
            id UUID PRIMARY KEY,
            interview_id UUID NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
            speaker VARCHAR(32) NOT NULL,
            content TEXT NOT NULL,
            sequence INTEGER NOT NULL,
            provider_event_id VARCHAR(200),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_interview_turn_provider_event
            ON interview_turns (interview_id, provider_event_id)
            WHERE provider_event_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_interview_turns_interview_id
            ON interview_turns (interview_id)
        """
    )


def downgrade() -> None:
    """Preserve interview transcript data; do not drop tables."""

    pass
