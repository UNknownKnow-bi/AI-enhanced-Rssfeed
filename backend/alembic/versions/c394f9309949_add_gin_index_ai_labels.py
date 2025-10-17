"""add_gin_index_ai_labels

Revision ID: c394f9309949
Revises: ai_labels_001
Create Date: 2025-10-17 14:52:08.142152

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c394f9309949'
down_revision: Union[str, None] = 'ai_labels_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create GIN index on ai_labels JSONB column for efficient tag filtering
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_articles_ai_labels_gin "
        "ON articles USING GIN (ai_labels jsonb_path_ops)"
    )


def downgrade() -> None:
    # Drop the GIN index
    op.execute("DROP INDEX IF EXISTS idx_articles_ai_labels_gin")
