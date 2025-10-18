"""
Article service for managing article status operations (read, favorite, trash).
Handles business logic for article status updates with proper user authorization.
"""

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from typing import Optional

from app.models.article import Article
from app.core.exceptions import ArticleNotFoundError, UnauthorizedError


async def mark_as_read(
    db: AsyncSession,
    article_id: UUID,
    user_id: UUID,
    is_read: bool
) -> Article:
    """
    Mark an article as read or unread.

    Args:
        db: Database session
        article_id: UUID of the article
        user_id: UUID of the user (for authorization)
        is_read: True to mark as read, False to mark as unread

    Returns:
        Updated Article object

    Raises:
        ArticleNotFoundError: If article doesn't exist
        UnauthorizedError: If user doesn't own the article's source
    """
    # Fetch article with source for authorization check
    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        raise ArticleNotFoundError(f"Article {article_id} not found")

    # Check user authorization (via source ownership)
    from app.models.rss_source import RSSSource
    source_stmt = select(RSSSource).where(RSSSource.id == article.source_id)
    source_result = await db.execute(source_stmt)
    source = source_result.scalar_one_or_none()

    if not source or source.user_id != user_id:
        raise UnauthorizedError("You don't have permission to modify this article")

    # Update status
    article.is_read = is_read
    await db.commit()
    await db.refresh(article)

    return article


async def toggle_favorite(
    db: AsyncSession,
    article_id: UUID,
    user_id: UUID,
    is_favorite: bool
) -> Article:
    """
    Toggle article favorite status.

    Args:
        db: Database session
        article_id: UUID of the article
        user_id: UUID of the user (for authorization)
        is_favorite: True to favorite, False to unfavorite

    Returns:
        Updated Article object

    Raises:
        ArticleNotFoundError: If article doesn't exist
        UnauthorizedError: If user doesn't own the article's source
    """
    # Fetch article with source for authorization check
    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        raise ArticleNotFoundError(f"Article {article_id} not found")

    # Check user authorization (via source ownership)
    from app.models.rss_source import RSSSource
    source_stmt = select(RSSSource).where(RSSSource.id == article.source_id)
    source_result = await db.execute(source_stmt)
    source = source_result.scalar_one_or_none()

    if not source or source.user_id != user_id:
        raise UnauthorizedError("You don't have permission to modify this article")

    # Update status
    article.is_favorite = is_favorite
    await db.commit()
    await db.refresh(article)

    return article


async def move_to_trash(
    db: AsyncSession,
    article_id: UUID,
    user_id: UUID
) -> Article:
    """
    Move an article to trash (soft delete).

    Args:
        db: Database session
        article_id: UUID of the article
        user_id: UUID of the user (for authorization)

    Returns:
        Updated Article object

    Raises:
        ArticleNotFoundError: If article doesn't exist
        UnauthorizedError: If user doesn't own the article's source
    """
    # Fetch article with source for authorization check
    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        raise ArticleNotFoundError(f"Article {article_id} not found")

    # Check user authorization (via source ownership)
    from app.models.rss_source import RSSSource
    source_stmt = select(RSSSource).where(RSSSource.id == article.source_id)
    source_result = await db.execute(source_stmt)
    source = source_result.scalar_one_or_none()

    if not source or source.user_id != user_id:
        raise UnauthorizedError("You don't have permission to modify this article")

    # Update status
    article.is_trashed = True
    article.trashed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(article)

    return article


async def restore_from_trash(
    db: AsyncSession,
    article_id: UUID,
    user_id: UUID
) -> Article:
    """
    Restore an article from trash.

    Args:
        db: Database session
        article_id: UUID of the article
        user_id: UUID of the user (for authorization)

    Returns:
        Updated Article object

    Raises:
        ArticleNotFoundError: If article doesn't exist
        UnauthorizedError: If user doesn't own the article's source
    """
    # Fetch article with source for authorization check
    stmt = select(Article).where(Article.id == article_id)
    result = await db.execute(stmt)
    article = result.scalar_one_or_none()

    if not article:
        raise ArticleNotFoundError(f"Article {article_id} not found")

    # Check user authorization (via source ownership)
    from app.models.rss_source import RSSSource
    source_stmt = select(RSSSource).where(RSSSource.id == article.source_id)
    source_result = await db.execute(source_stmt)
    source = source_result.scalar_one_or_none()

    if not source or source.user_id != user_id:
        raise UnauthorizedError("You don't have permission to modify this article")

    # Update status
    article.is_trashed = False
    article.trashed_at = None
    await db.commit()
    await db.refresh(article)

    return article


async def empty_trash(
    db: AsyncSession,
    user_id: UUID
) -> int:
    """
    Permanently delete all trashed articles for a user.
    Hard deletes articles where is_trashed=True.

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Number of articles deleted
    """
    # First, get all article IDs to delete (with authorization check)
    from app.models.rss_source import RSSSource

    # Join articles with sources to ensure user ownership
    stmt = select(Article.id).join(
        RSSSource, Article.source_id == RSSSource.id
    ).where(
        and_(
            Article.is_trashed == True,
            RSSSource.user_id == user_id
        )
    )

    result = await db.execute(stmt)
    article_ids = [row[0] for row in result.all()]

    if not article_ids:
        return 0

    # Delete the articles
    delete_stmt = delete(Article).where(Article.id.in_(article_ids))
    result = await db.execute(delete_stmt)
    await db.commit()

    return result.rowcount


async def get_article_counts(
    db: AsyncSession,
    user_id: UUID
) -> dict:
    """
    Get counts of articles in different states (unread, favorite, trash).

    Args:
        db: Database session
        user_id: UUID of the user

    Returns:
        Dictionary with counts for different article states
    """
    from app.models.rss_source import RSSSource
    from sqlalchemy import func

    # Count unread articles (not trashed)
    unread_stmt = select(func.count(Article.id)).join(
        RSSSource, Article.source_id == RSSSource.id
    ).where(
        and_(
            Article.is_read == False,
            Article.is_trashed == False,
            RSSSource.user_id == user_id
        )
    )
    unread_result = await db.execute(unread_stmt)
    unread_count = unread_result.scalar() or 0

    # Count favorite articles (not trashed)
    favorite_stmt = select(func.count(Article.id)).join(
        RSSSource, Article.source_id == RSSSource.id
    ).where(
        and_(
            Article.is_favorite == True,
            Article.is_trashed == False,
            RSSSource.user_id == user_id
        )
    )
    favorite_result = await db.execute(favorite_stmt)
    favorite_count = favorite_result.scalar() or 0

    # Count trashed articles
    trashed_stmt = select(func.count(Article.id)).join(
        RSSSource, Article.source_id == RSSSource.id
    ).where(
        and_(
            Article.is_trashed == True,
            RSSSource.user_id == user_id
        )
    )
    trashed_result = await db.execute(trashed_stmt)
    trashed_count = trashed_result.scalar() or 0

    return {
        "unread": unread_count,
        "favorite": favorite_count,
        "trashed": trashed_count
    }
