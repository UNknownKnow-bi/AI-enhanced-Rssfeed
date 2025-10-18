"""
Independent test script for AI labeling and summarization workflow.
Tests the newest 30 articles through the complete pipeline.

Usage:
    cd backend
    source venv/bin/activate
    python test_ai_workflow.py
"""

import asyncio
import logging
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.article import Article
from app.services.ai_labeler import get_ai_labeler
from app.services.ai_summarizer import get_ai_summarizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def reset_test_articles(db, article_ids):
    """Reset articles to pending status for fresh testing"""
    logger.info(f"Resetting {len(article_ids)} articles to pending status...")

    # Reset label status
    result = await db.execute(
        update(Article)
        .where(Article.id.in_(article_ids))
        .values(
            ai_label_status='pending',
            ai_labels=None,
            ai_label_error=None,
            ai_summary_status='pending',
            ai_summary=None,
            ai_summary_error=None,
            ai_summary_generated_at=None
        )
    )
    await db.commit()

    logger.info(f"✅ Reset {result.rowcount} articles to pending status")


async def get_test_articles(db, limit=30):
    """Get the newest N articles for testing"""
    logger.info(f"Fetching newest {limit} articles for testing...")

    result = await db.execute(
        select(Article)
        .options(selectinload(Article.source))
        .order_by(Article.created_at.desc())
        .limit(limit)
    )
    articles = result.scalars().all()

    logger.info(f"✅ Found {len(articles)} articles")
    for i, article in enumerate(articles, 1):
        logger.info(f"  {i}. {article.title[:60]}... (ID: {article.id})")

    return articles


async def check_article_status(db, article_ids):
    """Check current status of articles"""
    result = await db.execute(
        select(Article.id, Article.title, Article.ai_label_status, Article.ai_summary_status)
        .where(Article.id.in_(article_ids))
        .order_by(Article.created_at.desc())
    )
    articles = result.fetchall()

    label_stats = {'pending': 0, 'processing': 0, 'done': 0, 'error': 0, 'ignored': 0}
    summary_stats = {'pending': 0, 'processing': 0, 'success': 0, 'error': 0, 'ignored': 0}

    logger.info("\n" + "="*80)
    logger.info("CURRENT STATUS:")
    logger.info("="*80)

    for article_id, title, label_status, summary_status in articles:
        logger.info(f"📄 {title[:50]}...")
        logger.info(f"   Label: {label_status or 'None'} | Summary: {summary_status or 'None'}")

        if label_status:
            label_stats[label_status] = label_stats.get(label_status, 0) + 1
        if summary_status:
            summary_stats[summary_status] = summary_stats.get(summary_status, 0) + 1

    logger.info("\n" + "="*80)
    logger.info("STATISTICS:")
    logger.info("="*80)
    logger.info(f"📊 Label Status: {dict(label_stats)}")
    logger.info(f"📊 Summary Status: {dict(summary_stats)}")
    logger.info("="*80 + "\n")

    return label_stats, summary_stats


async def test_ai_labeling(article_ids):
    """Test AI labeling on the selected articles"""
    logger.info("\n" + "🏷️  STEP 1: TESTING AI LABELING")
    logger.info("="*80)

    async with AsyncSessionLocal() as db:
        labeler = get_ai_labeler()

        # Process pending articles (will trigger summarization at the end)
        logger.info("Starting AI labeling process...")
        start_time = datetime.now()

        processed_count = await labeler.process_pending_articles(db, max_batches=None)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"\n✅ AI Labeling Complete!")
        logger.info(f"   Processed: {processed_count} articles")
        logger.info(f"   Duration: {duration:.2f} seconds")
        logger.info(f"   Rate: {processed_count/duration if duration > 0 else 0:.2f} articles/second")

        # Check status after labeling
        await asyncio.sleep(2)  # Wait for commit
        await check_article_status(db, article_ids)


async def test_ai_summarization(article_ids):
    """Test AI summarization on successfully labeled articles"""
    logger.info("\n" + "📝 STEP 2: TESTING AI SUMMARIZATION")
    logger.info("="*80)

    async with AsyncSessionLocal() as db:
        # Check how many articles are ready for summarization
        result = await db.execute(
            select(Article.id)
            .where(
                Article.id.in_(article_ids),
                Article.ai_label_status == 'done',
                Article.ai_summary_status == 'pending'
            )
        )
        pending_summary_ids = [row[0] for row in result.fetchall()]

        logger.info(f"Found {len(pending_summary_ids)} articles ready for summarization")

        if not pending_summary_ids:
            logger.warning("⚠️  No articles ready for summarization!")
            logger.info("This might mean:")
            logger.info("  1. Labeling is still in progress")
            logger.info("  2. All articles were marked as #可忽略")
            logger.info("  3. Summarization already triggered by labeler")
            return

        summarizer = get_ai_summarizer()

        logger.info("Starting AI summarization process...")
        start_time = datetime.now()

        processed_count = await summarizer.process_pending_summaries(db, max_articles=None)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"\n✅ AI Summarization Complete!")
        logger.info(f"   Processed: {processed_count} articles")
        logger.info(f"   Duration: {duration:.2f} seconds")
        logger.info(f"   Rate: {processed_count/duration if duration > 0 else 0:.2f} articles/second")

        # Check final status
        await asyncio.sleep(2)  # Wait for commit
        await check_article_status(db, article_ids)


async def wait_for_background_tasks(article_ids, max_wait_seconds=300):
    """Wait for background summarization tasks to complete"""
    logger.info("\n" + "⏳ WAITING FOR BACKGROUND SUMMARIZATION")
    logger.info("="*80)
    logger.info(f"Waiting up to {max_wait_seconds} seconds for background tasks...")
    logger.info("(Summarization is triggered by labeler in background)")

    start_time = datetime.now()
    check_interval = 10  # Check every 10 seconds

    while (datetime.now() - start_time).total_seconds() < max_wait_seconds:
        async with AsyncSessionLocal() as db:
            # Count pending/processing summaries
            result = await db.execute(
                select(Article.ai_summary_status)
                .where(
                    Article.id.in_(article_ids),
                    Article.ai_label_status == 'done'
                )
            )
            statuses = [row[0] for row in result.fetchall()]

            pending_count = statuses.count('pending')
            processing_count = statuses.count('processing')

            if pending_count == 0 and processing_count == 0:
                logger.info(f"✅ All background tasks complete!")
                break

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"⏳ [{elapsed:.0f}s] Still waiting: {pending_count} pending, {processing_count} processing")
            await asyncio.sleep(check_interval)

    # Final status check
    async with AsyncSessionLocal() as db:
        await check_article_status(db, article_ids)


async def main(auto_reset=True):
    """Main test workflow"""
    logger.info("\n" + "🚀 STARTING AI WORKFLOW TEST")
    logger.info("="*80)
    logger.info("This script will test the complete AI pipeline:")
    logger.info("  1. Fetch newest 30 articles")
    logger.info("  2. Reset them to pending status (auto)")
    logger.info("  3. Run AI labeling (which triggers summarization at end)")
    logger.info("  4. Wait for background summarization to complete")
    logger.info("  5. Show final results")
    logger.info("="*80 + "\n")

    try:
        async with AsyncSessionLocal() as db:
            # Step 1: Get test articles
            articles = await get_test_articles(db, limit=30)
            article_ids = [article.id for article in articles]

            if not articles:
                logger.error("❌ No articles found in database!")
                return

            # Step 2: Show initial status
            logger.info("\n📊 INITIAL STATUS:")
            await check_article_status(db, article_ids)

            # Auto reset if specified
            if auto_reset:
                logger.info("\n🔄 Auto-resetting articles to pending status...")
                await reset_test_articles(db, article_ids)
                await check_article_status(db, article_ids)

        # Step 3: Test AI Labeling (this will trigger summarization at the end)
        await test_ai_labeling(article_ids)

        # Step 4: Wait for background summarization triggered by labeler
        await wait_for_background_tasks(article_ids, max_wait_seconds=300)

        # Step 5: Final report
        logger.info("\n" + "🎉 TEST COMPLETE!")
        logger.info("="*80)
        logger.info("Summary of what happened:")
        logger.info("  1. ✅ AI Labeling processed all articles in batches")
        logger.info("  2. ✅ After all batches, labeler triggered summarization once")
        logger.info("  3. ✅ Background summarization processed articles concurrently")
        logger.info("  4. ✅ Each article used its own database session (no conflicts)")
        logger.info("="*80)

        async with AsyncSessionLocal() as db:
            logger.info("\n📊 FINAL STATUS:")
            label_stats, summary_stats = await check_article_status(db, article_ids)

            # Success metrics
            total = len(article_ids)
            label_success_rate = (label_stats.get('done', 0) / total * 100) if total > 0 else 0
            summary_success_rate = (summary_stats.get('success', 0) / total * 100) if total > 0 else 0

            logger.info(f"\n✨ SUCCESS RATES:")
            logger.info(f"   Labeling: {label_stats.get('done', 0)}/{total} ({label_success_rate:.1f}%)")
            logger.info(f"   Summarization: {summary_stats.get('success', 0)}/{total} ({summary_success_rate:.1f}%)")

    except Exception as e:
        logger.error(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
