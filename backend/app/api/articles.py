from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.schemas import ArticleResponse, ArticleListResponse
from app.models import Article, RSSSource

router = APIRouter(prefix="/api", tags=["articles"])


@router.get("/articles", response_model=List[ArticleListResponse])
async def list_articles(
    source_id: Optional[UUID] = Query(None, description="Filter by RSS source ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Filter by AI tags (comma-separated, AND logic)"),
    limit: int = Query(50, ge=1, le=100, description="Number of articles to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
):
    """
    List articles with optional filtering by source, category, and/or AI tags.
    Priority: source_id > category > tags (combined with AND logic).
    """
    query = select(Article, RSSSource).join(
        RSSSource, Article.source_id == RSSSource.id
    )

    # Filter by source if provided (takes priority over category)
    if source_id:
        query = query.where(Article.source_id == source_id)
    # Otherwise filter by category if provided
    elif category:
        query = query.where(RSSSource.category == category)

    # Filter by tags if provided (combined with AND logic)
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        for tag in tag_list:
            if tag == '#VibeCoding':
                # Special handling for VibeCoding flag
                query = query.where(Article.ai_labels['vibe_coding'].astext == 'true')
            else:
                # Check if tag exists in any of the three arrays: identities, themes, extra
                # Use Python dict instead of f-string to ensure proper JSONB type binding
                query = query.where(
                    Article.ai_labels.op('@>')({"identities": [tag]})
                    | Article.ai_labels.op('@>')({"themes": [tag]})
                    | Article.ai_labels.op('@>')({"extra": [tag]})
                )

    # Order by publication date (newest first)
    query = query.order_by(Article.pub_date.desc().nulls_last(), Article.created_at.desc())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    rows = result.all()

    # Build response with source info
    articles = []
    for article, source in rows:
        article_dict = {
            "id": article.id,
            "source_id": article.source_id,
            "title": article.title,
            "description": article.description,
            "cover_image": article.cover_image,
            "pub_date": article.pub_date,
            "is_read": article.is_read,
            "created_at": article.created_at,
            "source_name": source.title,
            "source_icon": source.icon,

            # AI Labeling fields
            "ai_labels": article.ai_labels,
            "ai_label_status": article.ai_label_status,
        }
        articles.append(ArticleListResponse(**article_dict))

    return articles


@router.get("/articles/tags", response_model=List[str])
async def get_available_tags(
    source_id: Optional[UUID] = Query(None, description="Filter by RSS source ID"),
    category: Optional[str] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all unique AI tags from articles (respects source/category filter).
    Returns deduplicated list of all tags from identities, themes, extra, and vibe_coding.
    """
    # Build query with filters
    query = select(Article.ai_labels).where(Article.ai_label_status == 'done')

    if source_id:
        query = query.where(Article.source_id == source_id)
    elif category:
        query = query.join(RSSSource).where(RSSSource.category == category)

    result = await db.execute(query)
    all_labels = result.scalars().all()

    # Extract unique tags
    tags = set()
    for labels in all_labels:
        if labels:
            tags.update(labels.get('identities', []))
            tags.update(labels.get('themes', []))
            tags.update(labels.get('extra', []))
            if labels.get('vibe_coding'):
                tags.add('#VibeCoding')

    return sorted(list(tags))


@router.get("/articles/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full article details
    """
    result = await db.execute(
        select(Article, RSSSource)
        .join(RSSSource, Article.source_id == RSSSource.id)
        .where(Article.id == article_id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Article not found")

    article, source = row

    # Build response with source info
    article_dict = {
        "id": article.id,
        "source_id": article.source_id,
        "guid": article.guid,
        "title": article.title,
        "link": article.link,
        "description": article.description,
        "content": article.content,
        "cover_image": article.cover_image,
        "pub_date": article.pub_date,
        "is_read": article.is_read,
        "created_at": article.created_at,
        "source_name": source.title,
        "source_icon": source.icon,

        # AI Labeling fields
        "ai_labels": article.ai_labels,
        "ai_label_status": article.ai_label_status,

        # Optional: Extract vibe_coding for convenience
        "vibe_coding": article.ai_labels.get("vibe_coding", False) if article.ai_labels else None,
    }

    return ArticleResponse(**article_dict)


@router.patch("/articles/{article_id}/read")
async def mark_article_read(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an article as read
    """
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.is_read = True
    await db.commit()

    return {"message": "Article marked as read"}
