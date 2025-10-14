import asyncio
import logging
from datetime import datetime
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.models import RSSSource, Article
from app.services.rss_parser import RSSParser
from app.core.config import settings

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

            self.scheduler.start()
            self.is_running = True
            logger.info(f"RSS Scheduler started. Fetching feeds every {settings.SCRAPE_INTERVAL_MINUTES} minutes")

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
            logger.error(f"Error in fetch_and_store_feed for {source.url}: {e}")
            raise


# Global scheduler instance
_scheduler_instance = None


def get_scheduler(get_db_session) -> RSSScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = RSSScheduler(get_db_session)
    return _scheduler_instance
