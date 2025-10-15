"""add timezone to datetime columns

Revision ID: timezone_support_001
Revises: 2da8fad2b2c4
Create Date: 2025-10-14 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'timezone_support_001'
down_revision: Union[str, None] = '2da8fad2b2c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade all DateTime columns to use TIMESTAMP WITH TIME ZONE (TIMESTAMPTZ).

    This migration converts:
    - TIMESTAMP WITHOUT TIME ZONE → TIMESTAMP WITH TIME ZONE

    PostgreSQL will interpret existing naive timestamps as UTC (server timezone)
    and add timezone metadata without changing the actual timestamp values.
    """
    # Users table
    op.alter_column('users', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False)

    # RSS Sources table
    op.alter_column('rss_sources', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False)

    op.alter_column('rss_sources', 'last_fetched',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=True)

    # Articles table
    op.alter_column('articles', 'pub_date',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=True)

    op.alter_column('articles', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False)


def downgrade() -> None:
    """
    Downgrade all DateTime columns back to TIMESTAMP WITHOUT TIME ZONE.

    WARNING: This will strip timezone information from the timestamps.
    """
    # Articles table (reverse order)
    op.alter_column('articles', 'created_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)

    op.alter_column('articles', 'pub_date',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=True)

    # RSS Sources table
    op.alter_column('rss_sources', 'last_fetched',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=True)

    op.alter_column('rss_sources', 'created_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)

    # Users table
    op.alter_column('users', 'created_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
