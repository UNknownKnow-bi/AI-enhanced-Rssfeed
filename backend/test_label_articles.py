"""
Temporary test script to label today's 30 newest articles using AI.

This script can be deleted after testing - AI labels will remain in database.

Usage:
    cd backend
    source venv/bin/activate

    # Preview articles without API calls
    python test_label_articles.py --dry-run

    # Process 30 articles (default)
    python test_label_articles.py

    # Process custom number of articles
    python test_label_articles.py --limit 10

After testing, delete this script:
    rm test_label_articles.py

The AI-generated labels will persist in the database.
"""

import asyncio
import sys
import time
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

# Import existing services (NO code duplication)
from app.core.database import AsyncSessionLocal
from app.services.ai_labeler import get_ai_labeler
from app.models.article import Article


async def get_today_articles(db: AsyncSession, limit: int = 30):
    """
    Query today's articles, sorted newest first.

    Args:
        db: Database session
        limit: Maximum number of articles to return

    Returns:
        List of Article objects from today with pending/error status
    """
    # Get today's start (00:00 UTC)
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # Query articles from today, newest first
    # IMPORTANT: Eager load the 'source' relationship to avoid lazy loading errors
    result = await db.execute(
        select(Article)
        .options(selectinload(Article.source))  # Eager load source relationship
        .where(Article.pub_date >= today_start)
        .where(Article.ai_label_status.in_(['pending', 'error']))
        .order_by(Article.pub_date.desc(), Article.created_at.desc())
        .limit(limit)
    )

    return result.scalars().all()


async def process_batch(
    labeler,
    db: AsyncSession,
    articles: list,
    batch_num: int,
    total_batches: int
):
    """
    Process one batch of articles using existing AI labeler service.

    Args:
        labeler: AILabeler instance
        db: Database session
        articles: List of Article objects (up to 3)
        batch_num: Current batch number (1-indexed)
        total_batches: Total number of batches

    Returns:
        Number of successfully labeled articles in this batch
    """
    print(f"\n[Batch {batch_num}/{total_batches}] Processing articles {(batch_num-1)*3+1}-{min(batch_num*3, (total_batches-1)*3 + len(articles))}...")

    # Set status to 'processing'
    article_ids = [a.id for a in articles]
    await db.execute(
        update(Article)
        .where(Article.id.in_(article_ids))
        .values(ai_label_status='processing')
    )
    await db.commit()

    # Use existing service methods (NO duplication)
    try:
        messages = labeler.build_messages(articles)
        api_response = await labeler.call_deepseek_api(messages)

        if not api_response:
            print("  ❌ API call failed - marking articles as error")
            await db.execute(
                update(Article)
                .where(Article.id.in_(article_ids))
                .values(ai_label_status='error', ai_label_error='API call failed')
            )
            await db.commit()
            return 0

        # Parse response using existing logic
        labels_map = labeler.parse_response(api_response, articles)

        success_count = 0
        for article in articles:
            article_id_str = str(article.id)
            if article_id_str in labels_map:
                labels = labels_map[article_id_str]

                # Update database with labels
                await db.execute(
                    update(Article)
                    .where(Article.id == article.id)
                    .values(
                        ai_labels=labels,
                        ai_label_status='done',
                        ai_label_error=None
                    )
                )

                # Print result with color and formatting
                identities = ', '.join(labels.get('identities', []))
                themes = ', '.join(labels.get('themes', []))
                extra = ', '.join(labels.get('extra', [])) if labels.get('extra') else ''
                vibe = ' 🔥VibeCoding' if labels.get('vibe_coding') else ''

                title_display = article.title[:50] + "..." if len(article.title) > 50 else article.title
                tags_display = f"{identities}"
                if themes:
                    tags_display += f", {themes}"
                if extra:
                    tags_display += f", {extra}"

                print(f"  ✅ \"{title_display}\" → {tags_display}{vibe}")
                success_count += 1
            else:
                # No labels returned for this article
                await db.execute(
                    update(Article)
                    .where(Article.id == article.id)
                    .values(
                        ai_label_status='error',
                        ai_label_error='No labels in API response'
                    )
                )
                title_display = article.title[:50] + "..." if len(article.title) > 50 else article.title
                print(f"  ❌ \"{title_display}\" → No labels returned")

        await db.commit()
        return success_count

    except Exception as e:
        print(f"  ❌ Batch processing error: {e}")
        await db.execute(
            update(Article)
            .where(Article.id.in_(article_ids))
            .values(ai_label_status='error', ai_label_error=str(e))
        )
        await db.commit()
        return 0


async def main(dry_run: bool = False, limit: int = 30):
    """
    Main orchestration function.

    Args:
        dry_run: If True, preview articles without making API calls
        limit: Maximum number of articles to process
    """
    print(f"🔍 Querying today's {limit} newest articles...\n")

    async with AsyncSessionLocal() as db:
        # Get articles
        articles = await get_today_articles(db, limit)

        if not articles:
            print("❌ No articles found from today with pending/error status")
            print("\nTo check available articles, run:")
            print("  psql postgresql://postgres:postgres@localhost:5432/rss_feed -c \"")
            print("    SELECT COUNT(*) FROM articles WHERE DATE(pub_date AT TIME ZONE 'UTC') = CURRENT_DATE;\"")
            return

        print(f"Found {len(articles)} articles to process:\n")

        # Show first 5 articles as preview
        for i, article in enumerate(articles[:min(5, len(articles))], 1):
            pub_date = article.pub_date.strftime('%Y-%m-%d %H:%M:%S UTC') if article.pub_date else 'Unknown date'
            title_display = article.title[:60] + "..." if len(article.title) > 60 else article.title
            print(f"  {i}. {title_display}")
            print(f"     📅 {pub_date}")

        if len(articles) > 5:
            print(f"  ... and {len(articles) - 5} more articles")

        if dry_run:
            print("\n✋ Dry run mode - no API calls made")
            print("\nTo process these articles, run:")
            print(f"  python test_label_articles.py --limit {len(articles)}")
            return

        # Confirm before processing
        print(f"\n🏷️ Starting AI labeling process...")
        print(f"This will make ~{(len(articles) + 2) // 3} API calls to DeepSeek")
        print(f"Estimated cost: ~$0.{((len(articles) + 2) // 3):02d} USD\n")

        # Process in batches of 3 using existing service
        labeler = get_ai_labeler()
        batch_size = 3
        total_batches = (len(articles) + batch_size - 1) // batch_size
        total_success = 0
        total_failed = 0

        start_time = time.time()

        for i in range(0, len(articles), batch_size):
            batch = articles[i:i+batch_size]
            batch_num = (i // batch_size) + 1

            success = await process_batch(labeler, db, batch, batch_num, total_batches)
            total_success += success
            total_failed += (len(batch) - success)

            # Small delay between batches to respect rate limits
            if i + batch_size < len(articles):
                await asyncio.sleep(1.5)

        elapsed_time = time.time() - start_time

        # Print summary
        print(f"\n{'='*60}")
        print(f"✨ Processing Complete!")
        print(f"{'='*60}")
        print(f"\n📈 Summary:")
        print(f"  Total articles: {len(articles)}")
        print(f"  Successfully labeled: {total_success} ✅")
        print(f"  Failed: {total_failed} ❌")
        print(f"  Processing time: {elapsed_time:.1f} seconds")
        print(f"  Average time per batch: {elapsed_time/total_batches:.1f}s")

        print(f"\n💾 Data Persistence:")
        print(f"  ✅ AI labels saved to database")
        print(f"  ✅ Labels will persist after script deletion")
        print(f"  ✅ Check frontend at http://localhost:5174")

        print(f"\n🧹 Cleanup:")
        print(f"  After verifying labels in frontend, you can safely delete this script:")
        print(f"  rm test_label_articles.py")

        print(f"\n🎉 Done!\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Label today\'s articles with AI tags using existing service',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview articles without processing
  python test_label_articles.py --dry-run

  # Process 30 articles (default)
  python test_label_articles.py

  # Process 10 articles
  python test_label_articles.py --limit 10

After testing, delete this script:
  rm test_label_articles.py

The AI-generated labels will remain in the database.
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview articles without making API calls'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=30,
        help='Number of articles to process (default: 30)'
    )

    args = parser.parse_args()

    try:
        asyncio.run(main(dry_run=args.dry_run, limit=args.limit))
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
