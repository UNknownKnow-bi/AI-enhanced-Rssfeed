"""add_ai_summary_fields

Revision ID: c41751321e50
Revises: c85b81cde9f1
Create Date: 2025-10-17 19:53:43.057308

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c41751321e50'
down_revision: Union[str, None] = 'c85b81cde9f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add AI summary fields to articles table
    op.add_column('articles', sa.Column('ai_summary', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('ai_summary_status', sa.String(), nullable=False, server_default='pending'))
    op.add_column('articles', sa.Column('ai_summary_error', sa.Text(), nullable=True))
    op.add_column('articles', sa.Column('ai_summary_generated_at', sa.DateTime(timezone=True), nullable=True))

    # Add index on ai_summary_status for efficient querying
    op.create_index('idx_articles_ai_summary_status', 'articles', ['ai_summary_status'])


def downgrade() -> None:
    # Drop index first
    op.drop_index('idx_articles_ai_summary_status', table_name='articles')

    # Drop columns
    op.drop_column('articles', 'ai_summary_generated_at')
    op.drop_column('articles', 'ai_summary_error')
    op.drop_column('articles', 'ai_summary_status')
    op.drop_column('articles', 'ai_summary')
