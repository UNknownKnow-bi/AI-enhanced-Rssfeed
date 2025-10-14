from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import uuid
import logging
from datetime import datetime

from app.core.database import get_db
from app.schemas import (
    RSSValidateRequest,
    RSSValidateResponse,
    RSSSourceCreate,
    RSSSourceResponse,
)
from app.models import RSSSource, Article
from app.services.rss_parser import RSSParser
from app.services.rss_service import RSSService

router = APIRouter(prefix="/api", tags=["rss"])
logger = logging.getLogger(__name__)


async def fetch_source_articles(source: RSSSource, db: AsyncSession):
    """
    Fetch and store articles for a given RSS source
    """
    try:
        # Fetch and parse the feed
        feed_data = await RSSParser.fetch_feed(source.url)

        if not feed_data:
            logger.warning(f"Failed to fetch feed: {source.url}")
            return

        # Update source last_fetched time
        source.last_fetched = datetime.utcnow()

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


@router.post("/rss/validate", response_model=RSSValidateResponse)
async def validate_rss_url(
    request: RSSValidateRequest,
):
    """
    Validate an RSS feed URL by fetching and parsing it
    """
    result = await RSSParser.validate_feed(request.url)
    return RSSValidateResponse(**result)


@router.post("/sources", response_model=RSSSourceResponse)
async def create_rss_source(
    source: RSSSourceCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new RSS source for the user and immediately fetch articles
    """
    # First validate the RSS feed
    validation = await RSSParser.validate_feed(source.url)

    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid RSS feed: {validation['error']}"
        )

    # For now, use a default user ID (we'll implement auth later)
    # In production, get this from the authenticated user
    default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Create the RSS source
    db_source = RSSSource(
        user_id=default_user_id,
        url=source.url,
        title=source.title,
        description=validation["description"] or "",
        icon=validation["icon"] or "📰",  # Use favicon URL or fallback to emoji
        category=source.category,
    )

    db.add(db_source)
    await db.commit()
    await db.refresh(db_source)

    # Immediately fetch articles for this new source
    try:
        logger.info(f"Fetching articles immediately for new source: {db_source.title}")
        await fetch_source_articles(db_source, db)
    except Exception as e:
        logger.error(f"Error fetching articles for new source {db_source.url}: {e}")
        # Don't fail the source creation if fetching fails
        # The scheduler will retry later

    await db.refresh(db_source)
    return db_source


@router.get("/sources", response_model=List[RSSSourceResponse])
async def list_rss_sources(
    db: AsyncSession = Depends(get_db),
):
    """
    List all RSS sources for the user
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


@router.delete("/sources/{source_id}")
async def delete_rss_source(
    source_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an RSS source and all related articles

    This endpoint will:
    1. Validate user ownership
    2. Delete the RSS source and cascade delete all articles
    3. Run cleanup tasks in the background
    4. Return deletion statistics

    Args:
        source_id: UUID of the RSS source to delete
        background_tasks: FastAPI background tasks manager
        db: Database session

    Returns:
        Deletion statistics including number of articles deleted
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
