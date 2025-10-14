import logging
from typing import Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import HTTPException

from app.models import RSSSource, Article

logger = logging.getLogger(__name__)


class RSSService:
    """Service layer for RSS source operations"""

    @staticmethod
    async def delete_source(
        source_id: UUID,
        user_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Delete an RSS source with validation and statistics

        Args:
            source_id: ID of the RSS source to delete
            user_id: ID of the user requesting deletion
            db: Database session

        Returns:
            Dictionary with deletion statistics

        Raises:
            HTTPException: If source not found or user not authorized
        """
        try:
            # Get the RSS source
            result = await db.execute(
                select(RSSSource).where(RSSSource.id == source_id)
            )
            source = result.scalar_one_or_none()

            if not source:
                logger.warning(f"Attempted to delete non-existent source: {source_id}")
                raise HTTPException(
                    status_code=404,
                    detail="RSS source not found"
                )

            # Verify ownership
            if source.user_id != user_id:
                logger.warning(
                    f"User {user_id} attempted to delete source {source_id} "
                    f"owned by {source.user_id}"
                )
                raise HTTPException(
                    status_code=403,
                    detail="Not authorized to delete this RSS source"
                )

            # Count articles before deletion (for statistics)
            article_count_result = await db.execute(
                select(func.count(Article.id))
                .where(Article.source_id == source_id)
            )
            article_count = article_count_result.scalar() or 0

            # Store source info for return value
            source_title = source.title
            source_url = source.url
            source_category = source.category

            # Delete the source (cascade will handle articles)
            await db.delete(source)
            await db.commit()

            logger.info(
                f"Successfully deleted RSS source '{source_title}' (ID: {source_id}) "
                f"with {article_count} articles"
            )

            return {
                "source_id": str(source_id),
                "source_title": source_title,
                "source_url": source_url,
                "category": source_category,
                "articles_deleted": article_count,
                "message": "RSS source deleted successfully"
            }

        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"Error deleting RSS source {source_id}: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete RSS source: {str(e)}"
            )

    @staticmethod
    async def cleanup_source_resources(source_id: UUID, source_title: str):
        """
        Background task to clean up resources after source deletion

        Args:
            source_id: ID of the deleted source
            source_title: Title of the deleted source
        """
        try:
            logger.info(f"Running cleanup for deleted source: {source_title} ({source_id})")

            # TODO: Future enhancements
            # - Remove cached favicon files
            # - Clear application cache for this source
            # - Update analytics/metrics
            # - Notify external services (if any)

            logger.info(f"Cleanup completed for source: {source_title}")

        except Exception as e:
            logger.error(f"Error during cleanup for source {source_id}: {e}")
            # Don't raise - this is a background task
