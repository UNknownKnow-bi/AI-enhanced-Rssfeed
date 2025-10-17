"""normalize_existing_tags

Revision ID: c85b81cde9f1
Revises: c394f9309949
Create Date: 2025-10-17 19:17:10.836107

This migration ensures all tags in ai_labels JSONB field start with '#'.
It normalizes tags in identities, themes, and extra arrays.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c85b81cde9f1'
down_revision: Union[str, None] = 'c394f9309949'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Normalize all existing tags to ensure they start with '#'.

    Uses PostgreSQL JSONB functions to:
    1. Extract tag arrays from identities, themes, and extra
    2. Add '#' prefix to any tag that doesn't have it
    3. Update the ai_labels field with normalized tags
    """
    # SQL function to normalize a single tag (add # if missing)
    normalize_tag_func = """
    CREATE OR REPLACE FUNCTION normalize_tag(tag text)
    RETURNS text AS $$
    BEGIN
        IF tag IS NULL OR tag = '' THEN
            RETURN tag;
        END IF;
        tag := TRIM(tag);
        IF NOT tag LIKE '#%' THEN
            RETURN '#' || tag;
        END IF;
        RETURN tag;
    END;
    $$ LANGUAGE plpgsql IMMUTABLE;
    """

    # Create the normalize_tag function
    op.execute(normalize_tag_func)

    # Update articles with normalized tags
    # This handles identities, themes, and extra arrays
    normalize_labels_sql = """
    UPDATE articles
    SET ai_labels = jsonb_build_object(
        'identities', COALESCE(
            (SELECT jsonb_agg(normalize_tag(elem::text))
             FROM jsonb_array_elements_text(ai_labels->'identities') AS elem),
            '[]'::jsonb
        ),
        'themes', COALESCE(
            (SELECT jsonb_agg(normalize_tag(elem::text))
             FROM jsonb_array_elements_text(ai_labels->'themes') AS elem),
            '[]'::jsonb
        ),
        'extra', COALESCE(
            (SELECT jsonb_agg(normalize_tag(elem::text))
             FROM jsonb_array_elements_text(ai_labels->'extra') AS elem),
            '[]'::jsonb
        ),
        'vibe_coding', COALESCE(ai_labels->'vibe_coding', 'false'::jsonb)
    )
    WHERE ai_labels IS NOT NULL
      AND ai_label_status = 'done'
      AND (
          ai_labels ? 'identities' OR
          ai_labels ? 'themes' OR
          ai_labels ? 'extra'
      );
    """

    op.execute(normalize_labels_sql)

    # Drop the helper function
    op.execute("DROP FUNCTION IF EXISTS normalize_tag(text);")


def downgrade() -> None:
    """
    Downgrade is a no-op since removing '#' prefix could break functionality.
    This migration is safe and doesn't need to be reversed.
    """
    pass
