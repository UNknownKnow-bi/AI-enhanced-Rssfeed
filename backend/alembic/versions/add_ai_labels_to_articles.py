"""add ai labels to articles

Revision ID: ai_labels_001
Revises: timezone_support_001
Create Date: 2025-10-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'ai_labels_001'
down_revision: Union[str, None] = 'timezone_support_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add AI labeling columns to articles table.

    Adds:
    - ai_labels: JSONB column to store AI-generated labels
    - ai_label_status: String column to track labeling status (pending|processing|done|error)
    - ai_label_error: Text column to store error messages if labeling fails
    """
    # Add ai_labels column (JSONB)
    op.add_column('articles', sa.Column('ai_labels', postgresql.JSONB(), nullable=True))

    # Add ai_label_status column with default 'pending'
    op.add_column('articles', sa.Column('ai_label_status', sa.String(), nullable=False, server_default='pending'))

    # Add ai_label_error column
    op.add_column('articles', sa.Column('ai_label_error', sa.Text(), nullable=True))

    # Create index on ai_label_status for efficient querying
    op.create_index('ix_articles_ai_label_status', 'articles', ['ai_label_status'])


def downgrade() -> None:
    """
    Remove AI labeling columns from articles table.
    """
    # Drop index
    op.drop_index('ix_articles_ai_label_status', table_name='articles')

    # Drop columns
    op.drop_column('articles', 'ai_label_error')
    op.drop_column('articles', 'ai_label_status')
    op.drop_column('articles', 'ai_labels')
