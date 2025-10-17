import asyncio
import logging
from datetime import datetime, timezone
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models import RSSSource, Article
from app.services.rss_parser import RSSParser
from app.services.ai_labeler import get_ai_labeler
from app.services.ai_summarizer import get_ai_summarizer
from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class RSSScheduler:
    """Scheduler to fetch RSS feeds periodically"""

    def __init__(self, get_db_session):
        self.scheduler = AsyncIOScheduler()
        self.get_db_session = get_db_session
        self.is_running = False

    def start(self):
        """Start the scheduler"""
        if not self.is_running:
            # Schedule RSS fetching every N minutes
            self.scheduler.add_job(
                self.fetch_all_feeds,
                'interval',
                minutes=settings.SCRAPE_INTERVAL_MINUTES,
                id='fetch_rss_feeds',
                replace_existing=True,
            )

            # Schedule retry of error articles every N minutes
            self.scheduler.add_job(
                self.retry_error_labels,
                'interval',
                minutes=settings.AI_RETRY_INTERVAL_MINUTES,
                id='retry_error_ai_labels',
                replace_existing=True,
            )

            # Schedule AI summary generation every N minutes
            self.scheduler.add_job(
                self.process_pending_summaries,
                'interval',
                minutes=settings.AI_SUMMARY_INTERVAL_MINUTES,
                id='process_ai_summaries',
                replace_existing=True,
            )

            # Schedule retry of error summaries every N minutes
            self.scheduler.add_job(
                self.retry_error_summaries,
                'interval',
                minutes=settings.AI_SUMMARY_RETRY_INTERVAL_MINUTES,
                id='retry_error_ai_summaries',
                replace_existing=True,
            )

            self.scheduler.start()
            self.is_running = True
            logger.info(f"RSS Scheduler started. Fetching feeds every {settings.SCRAPE_INTERVAL_MINUTES} minutes")
            logger.info(f"AI Retry Scheduler started. Retrying error labels every {settings.AI_RETRY_INTERVAL_MINUTES} minutes")
            logger.info(f"AI Summary Scheduler started. Processing summaries every {settings.AI_SUMMARY_INTERVAL_MINUTES} minutes")
            logger.info(f"AI Summary Retry Scheduler started. Retrying error summaries every {settings.AI_SUMMARY_RETRY_INTERVAL_MINUTES} minutes")

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("RSS Scheduler stopped")

    async def fetch_all_feeds(self):
        """Fetch all RSS feeds with 2-minute gap between each"""
        logger.info("Starting RSS feed fetch cycle")

        async with self.get_db_session() as db:
            try:
                # Get all active RSS sources
                result = await db.execute(
                    select(RSSSource).order_by(RSSSource.last_fetched.asc().nulls_first())
                )
                sources = result.scalars().all()

                logger.info(f"Found {len(sources)} RSS sources to fetch")

                for index, source in enumerate(sources):
                    try:
                        logger.info(f"Fetching RSS feed {index + 1}/{len(sources)}: {source.title} ({source.url})")
                        await self.fetch_and_store_feed(db, source)

                        # Wait 2 minutes before fetching next source (except for the last one)
                        if index < len(sources) - 1:
                            logger.info(f"Waiting {settings.SOURCE_FETCH_GAP_SECONDS} seconds before next feed...")
                            await asyncio.sleep(settings.SOURCE_FETCH_GAP_SECONDS)

                    except Exception as e:
                        logger.error(f"Error fetching feed {source.title}: {e}")
                        continue

                await db.commit()
                logger.info("RSS feed fetch cycle completed")

                # Trigger AI labeling for pending articles
                asyncio.create_task(self.process_ai_labeling())

            except Exception as e:
                logger.error(f"Error in fetch_all_feeds: {e}")
                await db.rollback()

    async def fetch_and_store_feed(self, db: AsyncSession, source: RSSSource):
        """Fetch a single RSS feed and store new articles"""
        try:
            # Fetch and parse the feed
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
            logger.error(f"Error in fetch_and_store_feed for {source.url}: {e}")
            raise

    async def process_ai_labeling(self):
        """Process pending articles for AI labeling in a background task"""
        try:
            logger.info("Starting AI labeling task for pending articles")

            # Create a new database session for this background task
            async with AsyncSessionLocal() as db:
                ai_labeler = get_ai_labeler()
                processed_count = await ai_labeler.process_pending_articles(db)

                if processed_count > 0:
                    logger.info(f"AI labeling completed: {processed_count} articles labeled")
                else:
                    logger.info("AI labeling completed: no articles processed")

        except Exception as e:
            logger.error(f"Error in process_ai_labeling background task: {e}")

    async def retry_error_labels(self):
        """Retry AI labeling for articles with error status"""
        logger.info("Starting retry cycle for error articles")

        async with self.get_db_session() as db:
            try:
                # Check if there are any error articles first
                result = await db.execute(
                    select(Article)
                    .where(Article.ai_label_status == 'error')
                    .limit(1)
                )
                has_errors = result.scalar_one_or_none() is not None

                if not has_errors:
                    logger.info("No error articles found, skipping retry cycle")
                    return

                logger.info("Found error articles, triggering retry process")

                # Trigger retry in background task
                asyncio.create_task(self.process_error_ai_labeling())

            except Exception as e:
                logger.error(f"Error in retry_error_labels: {e}")
                await db.rollback()

    async def process_error_ai_labeling(self):
        """Process error articles for AI labeling retry in a background task"""
        try:
            logger.info("Starting AI retry labeling task for error articles")

            # Create a new database session for this background task
            async with AsyncSessionLocal() as db:
                ai_labeler = get_ai_labeler()
                processed_count = await ai_labeler.process_error_articles(db)

                if processed_count > 0:
                    logger.info(f"AI retry labeling completed: {processed_count} articles successfully labeled")
                else:
                    logger.info("AI retry labeling completed: no articles successfully processed")

        except Exception as e:
            logger.error(f"Error in process_error_ai_labeling background task: {e}")

    async def process_pending_summaries(self):
        """Process pending articles for AI summarization"""
        logger.info("Starting pending summaries processing cycle")

        async with self.get_db_session() as db:
            try:
                # Check if there are any pending summaries first
                result = await db.execute(
                    select(Article)
                    .where(
                        Article.ai_summary_status == 'pending',
                        Article.ai_label_status == 'done'
                    )
                    .limit(1)
                )
                has_pending = result.scalar_one_or_none() is not None

                if not has_pending:
                    logger.info("No pending summaries found, skipping processing cycle")
                    return

                logger.info("Found pending summaries, triggering processing")

                # Trigger processing in background task
                asyncio.create_task(self.process_ai_summaries_background())

            except Exception as e:
                logger.error(f"Error in process_pending_summaries: {e}")
                await db.rollback()

    async def process_ai_summaries_background(self):
        """Process pending summaries in a background task"""
        try:
            logger.info("Starting AI summary generation task for pending articles")

            # Create a new database session for this background task
            async with AsyncSessionLocal() as db:
                summarizer = get_ai_summarizer()
                processed_count = await summarizer.process_pending_summaries(db)

                if processed_count > 0:
                    logger.info(f"AI summary generation completed: {processed_count} articles summarized")
                else:
                    logger.info("AI summary generation completed: no articles processed")

        except Exception as e:
            logger.error(f"Error in process_ai_summaries_background task: {e}")

    async def retry_error_summaries(self):
        """Retry AI summarization for articles with error status"""
        logger.info("Starting retry cycle for error summaries")

        async with self.get_db_session() as db:
            try:
                # Check if there are any error summaries first
                result = await db.execute(
                    select(Article)
                    .where(
                        Article.ai_summary_status == 'error',
                        Article.ai_label_status == 'done'
                    )
                    .limit(1)
                )
                has_errors = result.scalar_one_or_none() is not None

                if not has_errors:
                    logger.info("No error summaries found, skipping retry cycle")
                    return

                logger.info("Found error summaries, triggering retry process")

                # Trigger retry in background task
                asyncio.create_task(self.process_error_ai_summaries_background())

            except Exception as e:
                logger.error(f"Error in retry_error_summaries: {e}")
                await db.rollback()

    async def process_error_ai_summaries_background(self):
        """Process error summaries for retry in a background task"""
        try:
            logger.info("Starting AI summary retry task for error articles")

            # Create a new database session for this background task
            async with AsyncSessionLocal() as db:
                summarizer = get_ai_summarizer()
                processed_count = await summarizer.process_error_summaries(db)

                if processed_count > 0:
                    logger.info(f"AI summary retry completed: {processed_count} articles successfully summarized")
                else:
                    logger.info("AI summary retry completed: no articles successfully processed")

        except Exception as e:
            logger.error(f"Error in process_error_ai_summaries_background task: {e}")


# Global scheduler instance
_scheduler_instance = None


def get_scheduler(get_db_session) -> RSSScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = RSSScheduler(get_db_session)
    return _scheduler_instance
