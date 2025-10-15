from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
import logging
from datetime import datetime, timezone

from app.core.database import get_db
from app.schemas import (
    RSSValidateRequest,
    RSSValidateResponse,
    RSSSourceCreate,
    RSSSourceUpdate,
    RSSSourceResponse,
)
from app.models import RSSSource, Article
from app.services.rss_parser import RSSParser
from app.services.rss_service import RSSService

router = APIRouter(prefix="/api", tags=["rss"])
logger = logging.getLogger(__name__)


async def fetch_source_articles(
    source: RSSSource,
    db: AsyncSession,
    feed_data: Optional[Dict[str, Any]] = None
):
    """
    Fetch and store articles for a given RSS source.

    Args:
        source: RSSSource model instance
        db: Database session
        feed_data: Optional pre-fetched feed data from cache or previous fetch.
                   If provided, skips the network fetch step.
    """
    try:
        # Use provided feed_data if available, otherwise fetch from network/cache
        if not feed_data:
            feed_data = await RSSParser.fetch_feed(source.url)

        if not feed_data:
            logger.warning(f"Failed to fetch feed: {source.url}")
            return

        # Update source last_fetched time
        source.last_fetched = datetime.now(timezone.utc)

        # Store new articles
        new_articles_count = 0
        for article_data in feed_data["articles"]:
            # Check if article already exists (by guid)
            result = await db.execute(
                select(Article).where(Article.guid == article_data["guid"])
            )
            existing_article = result.scalar_one_or_none()

            if existing_article:
                continue

            # Create new article
            new_article = Article(
                source_id=source.id,
                guid=article_data["guid"],
                title=article_data["title"],
                link=article_data["link"],
                description=article_data.get("description"),
                content=article_data.get("content"),
                cover_image=article_data.get("cover_image"),
                pub_date=article_data.get("pub_date"),
            )

            db.add(new_article)
            new_articles_count += 1

        # Update unread count for this source
        result = await db.execute(
            select(Article)
            .where(Article.source_id == source.id, Article.is_read == False)
        )
        unread_articles = result.scalars().all()
        source.unread_count = len(unread_articles)

        await db.commit()
        logger.info(f"Stored {new_articles_count} new articles from {source.title}")

    except Exception as e:
        logger.error(f"Error fetching articles for {source.url}: {e}")
        raise


@router.post(
    "/rss/validate",
    response_model=RSSValidateResponse,
    summary="Validate RSS Feed URL",
    description="Validate an RSS feed URL by fetching and parsing it. Returns feed metadata if valid.",
    tags=["Validation"]
)
async def validate_rss_url(
    request: RSSValidateRequest,
):
    """
    Validate an RSS feed URL by fetching and parsing it.
    """
    result = await RSSParser.validate_feed(request.url)
    return RSSValidateResponse(**result)


@router.post(
    "/sources",
    response_model=RSSSourceResponse,
    summary="Create RSS Source",
    description="""
Add a new RSS feed source and immediately fetch articles.

**Recommended workflow:**
1. First call `POST /api/rss/validate` to validate the URL
2. Then call this endpoint to create the source

If validation was called within 3 minutes, cached feed data will be reused
to avoid duplicate network requests.
    """,
    tags=["RSS Sources"]
)
async def create_rss_source(
    source: RSSSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new RSS source and immediately fetch articles.
    """
    # For now, use a default user ID (we'll implement auth later)
    # In production, get this from the authenticated user
    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Fetch the feed (checks cache first, falls back to network)
    # This will use cached data from validate_feed() if available
    feed_data = await RSSParser.fetch_feed(source.url)

    if not feed_data:
        raise HTTPException(
            status_code=400,
            detail="Failed to fetch RSS feed. Please validate the feed URL first."
        )

    # Extract metadata from feed data
    feed_info = feed_data.get("feed", {})
    description = feed_info.get("description", "")

    # Note: favicon is only available if this was cached from validate_feed()
    # For cache misses, we use a default emoji
    # This is acceptable because validate_feed() should always be called first
    icon = "📰"  # Default fallback

    # Create the RSS source
    db_source = RSSSource(
        user_id=default_user_id,
        url=source.url,
        title=source.title,
        description=description,
        icon=icon,
        category=source.category,
    )

    db.add(db_source)
    await db.commit()
    await db.refresh(db_source)

    # Immediately store articles using the fetched/cached feed data
    try:
        logger.info(f"Storing articles for new source: {db_source.title}")
        await fetch_source_articles(db_source, db, feed_data=feed_data)
    except Exception as e:
        logger.error(f"Error storing articles for new source {db_source.url}: {e}")
        # Don't fail the source creation if article storage fails
        # The scheduler will retry later

    await db.refresh(db_source)
    return db_source


@router.get(
    "/sources",
    response_model=List[RSSSourceResponse],
    summary="List RSS Sources",
    description="Retrieve all RSS sources for the authenticated user, ordered by creation date (newest first).",
    tags=["RSS Sources"]
)
async def list_rss_sources(
    db: AsyncSession = Depends(get_db),
):
    """
    List all RSS sources for the authenticated user.
    """
    # For now, use default user ID
    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    result = await db.execute(
        select(RSSSource)
        .where(RSSSource.user_id == default_user_id)
        .order_by(RSSSource.created_at.desc())
    )
    sources = result.scalars().all()

    return sources


@router.patch(
    "/sources/{source_id}",
    response_model=RSSSourceResponse,
    summary="Update RSS Source",
    description="""
Update an existing RSS source's metadata fields.

This endpoint supports **partial updates** - only the provided fields will be modified.
All fields are optional, but at least one must be provided.

## Update Operations

### Rename Source
Update the `title` field to change the display name of the RSS source.

### Change Icon
Update the `icon` field with:
- **Emoji**: Single or multiple Unicode emoji characters (🚀, 📰, 🎯)
- **Image URL**: Full URL to an icon image (https://example.com/icon.png)

### Change Category
Update the `category` field to organize sources. Defaults to "未分类" if empty.

## Validation Rules

- **Title**: Cannot be empty (whitespace is trimmed)
- **Icon**: Cannot be empty (whitespace is trimmed)
- **Category**: Defaults to "未分类" if empty or whitespace-only
- **At least one field** must be provided in the request body

## Authorization

Currently uses a default user ID. In production, this will validate the authenticated user's ownership.
    """,
    responses={
        200: {
            "description": "Successfully updated RSS source",
            "content": {
                "application/json": {
                    "example": {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "user_id": "00000000-0000-0000-0000-000000000001",
                        "url": "https://hnrss.org/frontpage",
                        "title": "Hacker News - Updated Title",
                        "description": "Hacker News RSS Feed",
                        "icon": "🚀",
                        "category": "Tech",
                        "unread_count": 42,
                        "created_at": "2025-01-01T00:00:00Z",
                        "last_fetched": "2025-01-01T12:00:00Z"
                    }
                }
            }
        },
        400: {
            "description": "Bad Request - Invalid input",
            "content": {
                "application/json": {
                    "examples": {
                        "no_fields": {
                            "summary": "No fields provided",
                            "value": {
                                "detail": "At least one field (title, icon, or category) must be provided"
                            }
                        },
                        "empty_title": {
                            "summary": "Empty title",
                            "value": {
                                "detail": "Title cannot be empty"
                            }
                        },
                        "empty_icon": {
                            "summary": "Empty icon",
                            "value": {
                                "detail": "Icon cannot be empty"
                            }
                        }
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Not authorized to update this source",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authorized to update this RSS source"
                    }
                }
            }
        },
        404: {
            "description": "Not Found - RSS source does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "RSS source not found"
                    }
                }
            }
        }
    },
    tags=["RSS Sources"]
)
async def update_rss_source(
    source_id: UUID,
    updates: RSSSourceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update RSS source metadata (title, icon, category).
    """
    # For now, use default user ID (same as in other endpoints)
    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Check if at least one field is provided
    if updates.title is None and updates.icon is None and updates.category is None:
        raise HTTPException(
            status_code=400,
            detail="At least one field (title, icon, or category) must be provided"
        )

    # Get the RSS source
    result = await db.execute(
        select(RSSSource).where(RSSSource.id == source_id)
    )
    source = result.scalar_one_or_none()

    if not source:
        logger.warning(f"Attempted to update non-existent source: {source_id}")
        raise HTTPException(
            status_code=404,
            detail="RSS source not found"
        )

    # Verify ownership
    if source.user_id != default_user_id:
        logger.warning(
            f"User {default_user_id} attempted to update source {source_id} "
            f"owned by {source.user_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="Not authorized to update this RSS source"
        )

    # Apply updates (only update fields that are provided)
    if updates.title is not None:
        # Validate title is not empty after stripping whitespace
        title_stripped = updates.title.strip()
        if not title_stripped:
            raise HTTPException(
                status_code=400,
                detail="Title cannot be empty"
            )
        source.title = title_stripped
        logger.info(f"Updated title for source {source_id}: {title_stripped}")

    if updates.icon is not None:
        # Validate icon is not empty
        if not updates.icon.strip():
            raise HTTPException(
                status_code=400,
                detail="Icon cannot be empty"
            )
        source.icon = updates.icon.strip()
        logger.info(f"Updated icon for source {source_id}: {updates.icon[:20]}...")

    if updates.category is not None:
        category_stripped = updates.category.strip() or "未分类"
        source.category = category_stripped
        logger.info(f"Updated category for source {source_id}: {category_stripped}")

    # Commit changes
    await db.commit()
    await db.refresh(source)

    logger.info(f"Successfully updated RSS source: {source.title} (ID: {source_id})")
    return source


@router.delete(
    "/sources/{source_id}",
    summary="Delete RSS Source",
    description="""
Delete an RSS source and all its associated articles.

**Warning:** This is a destructive operation that cannot be undone.

The deletion process:
1. Validates user ownership (403 if unauthorized)
2. Deletes the RSS source from database
3. CASCADE deletes all related articles
4. Runs background cleanup tasks (cache, logs, metrics)
5. Returns deletion statistics

**Authorization required:** User must own the source to delete it.
    """,
    responses={
        200: {
            "description": "Successfully deleted RSS source",
            "content": {
                "application/json": {
                    "example": {
                        "source_id": "123e4567-e89b-12d3-a456-426614174000",
                        "source_title": "Hacker News",
                        "source_url": "https://hnrss.org/frontpage",
                        "category": "Tech",
                        "articles_deleted": 42,
                        "message": "RSS source deleted successfully"
                    }
                }
            }
        },
        403: {
            "description": "Forbidden - Not authorized to delete this source",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Not authorized to delete this RSS source"
                    }
                }
            }
        },
        404: {
            "description": "Not Found - RSS source does not exist",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "RSS source not found"
                    }
                }
            }
        }
    },
    tags=["RSS Sources"]
)
async def delete_rss_source(
    source_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an RSS source and all related articles.
    """
    # For now, use default user ID (same as in other endpoints)
    # In production, get this from authenticated user
    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Delete source using service layer
    result = await RSSService.delete_source(source_id, default_user_id, db)

    # Add background cleanup task
    background_tasks.add_task(
        RSSService.cleanup_source_resources,
        source_id,
        result["source_title"]
    )

    logger.info(
        f"Deleted RSS source '{result['source_title']}' "
        f"({result['articles_deleted']} articles)"
    )

    return result
