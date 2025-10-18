"""add_article_status_fields

Revision ID: 30dce70dc265
Revises: c41751321e50
Create Date: 2025-10-18 01:40:08.195454

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30dce70dc265'
down_revision: Union[str, None] = 'c41751321e50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: is_read column already exists, so we only add the new status fields
    # Add new boolean status fields with server defaults
    op.add_column('articles', sa.Column('is_favorite', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('articles', sa.Column('is_trashed', sa.Boolean(), server_default='false', nullable=False))

    # Add timestamp for tracking when article was trashed
    op.add_column('articles', sa.Column('trashed_at', sa.DateTime(timezone=True), nullable=True))

    # Create indexes for efficient querying
    op.create_index('idx_articles_is_trashed', 'articles', ['is_trashed'])
    op.create_index('idx_articles_favorite_not_trashed', 'articles', ['is_favorite', 'is_trashed'])
    op.create_index('idx_articles_read_not_trashed', 'articles', ['is_read', 'is_trashed'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_articles_read_not_trashed', table_name='articles')
    op.drop_index('idx_articles_favorite_not_trashed', table_name='articles')
    op.drop_index('idx_articles_is_trashed', table_name='articles')

    # Drop columns (is_read is not dropped since it existed before this migration)
    op.drop_column('articles', 'trashed_at')
    op.drop_column('articles', 'is_trashed')
    op.drop_column('articles', 'is_favorite')
