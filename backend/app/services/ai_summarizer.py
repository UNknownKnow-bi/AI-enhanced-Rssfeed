import asyncio
import logging
import json
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from openai import OpenAI
from uuid import UUID

from app.models.article import Article
from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class AISummarizer:
    """Service for generating article summaries using DeepSeek AI API"""

    def __init__(self):
        """Initialize OpenAI client configured for DeepSeek API"""
        self.client = None
        self._initialized = False
        self._semaphore = asyncio.Semaphore(settings.AI_SUMMARY_MAX_CONCURRENT)

    def _get_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client"""
        if not self._initialized:
            self.client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
            self._initialized = True
        return self.client

    def should_skip_article(self, article: Article) -> bool:
        """
        Check if article should be skipped for summarization.

        Args:
            article: Article to check

        Returns:
            True if article should be skipped
        """
        # Skip if ai_labels indicates it's ignorable
        if article.ai_labels:
            identities = article.ai_labels.get('identities', [])
            if '#可忽略' in identities:
                logger.info(f"Skipping article {article.id}: marked as #可忽略")
                return True

        # Skip if content is too short or empty
        content = article.content or article.description or ""
        if len(content.strip()) < 100:
            logger.info(f"Skipping article {article.id}: content too short ({len(content)} chars)")
            return True

        return False

    def build_summary_prompt(self, article: Article) -> List[dict]:
        """
        Build messages array for DeepSeek API to generate summary.

        Args:
            article: Article to summarize

        Returns:
            List of message dicts with system and user messages
        """
        system_message = """# 角色
你是一位资深的AI技术分析师和内容策略师。你的任务是为我（一位AI应用独立开发者兼科技博主）阅读并深度解析一篇文章，然后以清晰、结构化的Markdown格式输出一份包含核心观点和价值分析的摘要。

# 我的核心需求
我需要快速理解文章的精髓，特别是其中的核心观点、关键论据和对我个人事业有价值的信息。我既需要技术层面的"干货"来启发我的开发工作，也需要有故事性、有传播潜力的"素材"来丰富我的博客内容。

# 摘要生成要求
请严格按照以下Markdown结构，生成文章的摘要：

## 主要观点和论据 (Key Arguments)
*以无序列表（bullet points）的形式，列出文章的3-5个主要观点或论点。*

- **观点一**：[简要描述第一个核心观点]
  - 针对**观点一**的论据：[例如：引用的研究数据、关键的技术规格、具体的实现方法等]
- **观点二**：[简要描述第二个核心观点]
  - 针对**观点二**的论据：[例如：某个成功的应用案例、市场规模预测、重要的事实等]
- **观点三**：[...依此类推]

## 对我的价值
*这是最重要的部分。请站在我的双重身份上，分析这篇文章对我的具体价值,用一句话简明表要核心利益点即可。*
---

**输出要求**：
1. 使用标准Markdown格式
2. 保持简洁，总字数控制在700字以内，言简意赅越好
3. 不要添加任何与摘要无关的内容（如免责声明、meta信息等）"""

        # Build user message with article data
        content = article.content or article.description or ""
        # Limit content length to avoid token limits (max ~8000 chars)
        if len(content) > 8000:
            content = content[:8000] + "..."

        user_message = f"""请为以下文章生成摘要：

**标题**：{article.title}

**来源**：{article.source.title if article.source else '未知'}

**链接**：{article.link}

**正文内容**：
{content}

请严格按照上述Markdown结构输出摘要。"""

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

    async def call_deepseek_api(self, messages: List[dict]) -> Optional[str]:
        """
        Call DeepSeek API with retry logic and timeout.
        Uses asyncio.to_thread to prevent blocking the event loop.

        Args:
            messages: Messages array for the API

        Returns:
            Generated markdown summary or None on failure
        """
        client = self._get_client()
        retry_delays = [1, 2]  # Exponential backoff: 1s, 2s

        for attempt in range(settings.AI_MAX_RETRIES + 1):
            try:
                logger.info(f"Calling DeepSeek API for summary (attempt {attempt + 1}/{settings.AI_MAX_RETRIES + 1})")

                # Call API in thread pool to avoid blocking event loop
                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=settings.DEEPSEEK_MODEL,
                    messages=messages,
                    temperature=0.5,  # Slightly higher for more creative summaries
                    max_tokens=2000,
                    timeout=settings.AI_SUMMARY_TIMEOUT_SECONDS
                )

                # Extract content from response
                summary = response.choices[0].message.content
                logger.info(f"DeepSeek API summary received: {len(summary)} chars")

                return summary

            except Exception as e:
                logger.error(f"DeepSeek API call failed (attempt {attempt + 1}): {e}")
                if attempt < settings.AI_MAX_RETRIES:
                    await asyncio.sleep(retry_delays[attempt])
                    continue
                return None

        logger.error("All retry attempts exhausted for summary generation")
        return None

    def validate_summary(self, summary: str) -> bool:
        """
        Validate that the summary is in valid markdown format.

        Args:
            summary: Generated summary text

        Returns:
            True if valid, False otherwise
        """
        if not summary or len(summary.strip()) < 50:
            return False

        # Basic markdown validation: should contain headers
        if '##' not in summary:
            logger.warning("Summary validation failed: no markdown headers found")
            return False

        return True

    async def process_single_article(self, db: AsyncSession, article: Article) -> bool:
        """
        Process a single article for summarization with concurrency control.

        DEPRECATED: Use _process_article_by_id() instead for better session management.

        Args:
            db: Database session
            article: Article to summarize

        Returns:
            True if successful, False otherwise
        """
        async with self._semaphore:
            try:
                # Check if should skip
                if self.should_skip_article(article):
                    result = await db.execute(
                        update(Article)
                        .where(Article.id == article.id, Article.ai_summary_status.in_(['pending', 'error']))
                        .values(
                            ai_summary_status='ignored',
                            ai_summary_error='Content too short or marked as ignorable'
                        )
                    )
                    await db.commit()
                    return False

                # Update status to processing with conditional check
                result = await db.execute(
                    update(Article)
                    .where(Article.id == article.id, Article.ai_summary_status.in_(['pending', 'error']))
                    .values(ai_summary_status='processing')
                )
                await db.commit()

                # Check if update succeeded (article might have been processed by another task)
                if result.rowcount == 0:
                    logger.info(f"Article {article.id} already being processed, skipping")
                    return False

                # Build prompt
                messages = self.build_summary_prompt(article)

                # Call API
                summary = await self.call_deepseek_api(messages)

                if not summary:
                    await db.execute(
                        update(Article)
                        .where(Article.id == article.id)
                        .values(
                            ai_summary_status='error',
                            ai_summary_error='Failed to get response from DeepSeek API after retries'
                        )
                    )
                    await db.commit()
                    return False

                # Validate summary
                if not self.validate_summary(summary):
                    await db.execute(
                        update(Article)
                        .where(Article.id == article.id)
                        .values(
                            ai_summary_status='error',
                            ai_summary_error='Invalid summary format returned by API'
                        )
                    )
                    await db.commit()
                    return False

                # Save successful summary
                await db.execute(
                    update(Article)
                    .where(Article.id == article.id)
                    .values(
                        ai_summary=summary,
                        ai_summary_status='success',
                        ai_summary_error=None,
                        ai_summary_generated_at=datetime.now(timezone.utc)
                    )
                )
                await db.commit()
                logger.info(f"Successfully generated summary for article {article.id}")
                return True

            except Exception as e:
                logger.error(f"Error processing article {article.id}: {e}")
                await db.rollback()

                try:
                    await db.execute(
                        update(Article)
                        .where(Article.id == article.id)
                        .values(
                            ai_summary_status='error',
                            ai_summary_error=f'Processing error: {str(e)}'
                        )
                    )
                    await db.commit()
                except Exception as update_error:
                    logger.error(f"Failed to update error status: {update_error}")
                    await db.rollback()

                return False

    async def _process_article_by_id(self, article_id: UUID) -> bool:
        """
        Process a single article by ID, creating its own database session.
        This method is concurrency-safe and should be used for parallel processing.

        Args:
            article_id: UUID of the article to process

        Returns:
            True if successful, False otherwise
        """
        async with self._semaphore:
            async with AsyncSessionLocal() as db:
                try:
                    # Query article with source relationship
                    result = await db.execute(
                        select(Article)
                        .options(selectinload(Article.source))
                        .where(Article.id == article_id)
                    )
                    article = result.scalar_one_or_none()

                    if not article:
                        logger.warning(f"Article {article_id} not found")
                        return False

                    # Check if should skip
                    if self.should_skip_article(article):
                        result = await db.execute(
                            update(Article)
                            .where(Article.id == article_id, Article.ai_summary_status.in_(['pending', 'error']))
                            .values(
                                ai_summary_status='ignored',
                                ai_summary_error='Content too short or marked as ignorable'
                            )
                        )
                        await db.commit()
                        return False

                    # Update status to processing with conditional check
                    result = await db.execute(
                        update(Article)
                        .where(Article.id == article_id, Article.ai_summary_status.in_(['pending', 'error']))
                        .values(ai_summary_status='processing')
                    )
                    await db.commit()

                    # Check if update succeeded (article might have been processed by another task)
                    if result.rowcount == 0:
                        logger.info(f"Article {article_id} already being processed, skipping")
                        return False

                    # Build prompt
                    messages = self.build_summary_prompt(article)

                    # Call API
                    summary = await self.call_deepseek_api(messages)

                    if not summary:
                        await db.execute(
                            update(Article)
                            .where(Article.id == article_id)
                            .values(
                                ai_summary_status='error',
                                ai_summary_error='Failed to get response from DeepSeek API after retries'
                            )
                        )
                        await db.commit()
                        return False

                    # Validate summary
                    if not self.validate_summary(summary):
                        await db.execute(
                            update(Article)
                            .where(Article.id == article_id)
                            .values(
                                ai_summary_status='error',
                                ai_summary_error='Invalid summary format returned by API'
                            )
                        )
                        await db.commit()
                        return False

                    # Save successful summary
                    await db.execute(
                        update(Article)
                        .where(Article.id == article_id)
                        .values(
                            ai_summary=summary,
                            ai_summary_status='success',
                            ai_summary_error=None,
                            ai_summary_generated_at=datetime.now(timezone.utc)
                        )
                    )
                    await db.commit()
                    logger.info(f"Successfully generated summary for article {article_id}")
                    return True

                except Exception as e:
                    logger.error(f"Error processing article {article_id}: {e}")
                    await db.rollback()

                    try:
                        await db.execute(
                            update(Article)
                            .where(Article.id == article_id)
                            .values(
                                ai_summary_status='error',
                                ai_summary_error=f'Processing error: {str(e)}'
                            )
                        )
                        await db.commit()
                    except Exception as update_error:
                        logger.error(f"Failed to update error status: {update_error}")
                        await db.rollback()

                    return False

    async def process_pending_summaries(self, db: AsyncSession, max_articles: int = None) -> int:
        """
        Process pending articles for summarization in batches.
        Uses per-article sessions to avoid concurrency issues.

        Args:
            db: Database session (used only for querying article IDs)
            max_articles: Maximum number of articles to process (None = process all)

        Returns:
            Total number of articles successfully processed
        """
        total_processed = 0
        batch_count = 0

        while True:
            # Check if we've hit the max limit
            if max_articles is not None and total_processed >= max_articles:
                logger.info(f"Reached max article limit ({max_articles}), stopping")
                break

            try:
                # Query pending article IDs only (no eager loading needed)
                limit = settings.AI_SUMMARY_BATCH_SIZE
                if max_articles is not None:
                    limit = min(limit, max_articles - total_processed)

                result = await db.execute(
                    select(Article.id)
                    .where(
                        Article.ai_summary_status == 'pending',
                        Article.ai_label_status == 'done'  # Only process labeled articles
                    )
                    .order_by(Article.created_at.asc())
                    .limit(limit)
                )
                article_ids = [row[0] for row in result.fetchall()]

                if not article_ids:
                    logger.info(f"No more pending summaries to process (total processed: {total_processed})")
                    break

                batch_count += 1
                logger.info(f"Processing summary batch {batch_count}: {len(article_ids)} articles")

                # Process articles concurrently - each creates its own session
                tasks = [self._process_article_by_id(article_id) for article_id in article_ids]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successes
                success_count = sum(1 for r in results if r is True)
                total_processed += success_count

                logger.info(f"Summary batch {batch_count} complete: {success_count}/{len(article_ids)} successful (total: {total_processed})")

                # Small delay between batches
                if article_ids and len(article_ids) == settings.AI_SUMMARY_BATCH_SIZE:
                    await asyncio.sleep(2)

            except Exception as e:
                logger.error(f"Error in summary batch {batch_count}: {e}")
                continue

        return total_processed

    async def process_error_summaries(self, db: AsyncSession, max_articles: int = None) -> int:
        """
        Retry articles with error status for summarization.
        Uses per-article sessions to avoid concurrency issues.

        Args:
            db: Database session (used only for querying article IDs)
            max_articles: Maximum number of articles to retry (None = process all)

        Returns:
            Total number of articles successfully processed
        """
        total_processed = 0
        batch_count = 0

        while True:
            # Check if we've hit the max limit
            if max_articles is not None and total_processed >= max_articles:
                logger.info(f"Reached max retry limit ({max_articles}), stopping")
                break

            try:
                # Query error article IDs only (no eager loading needed)
                limit = settings.AI_SUMMARY_BATCH_SIZE
                if max_articles is not None:
                    limit = min(limit, max_articles - total_processed)

                result = await db.execute(
                    select(Article.id)
                    .where(
                        Article.ai_summary_status == 'error',
                        Article.ai_label_status == 'done'  # Only retry labeled articles
                    )
                    .order_by(Article.created_at.asc())
                    .limit(limit)
                )
                article_ids = [row[0] for row in result.fetchall()]

                if not article_ids:
                    logger.info(f"No error summaries to retry (total processed: {total_processed})")
                    break

                batch_count += 1
                logger.info(f"Retrying summary batch {batch_count}: {len(article_ids)} articles")

                # Process articles concurrently - each creates its own session
                tasks = [self._process_article_by_id(article_id) for article_id in article_ids]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successes
                success_count = sum(1 for r in results if r is True)
                total_processed += success_count

                logger.info(f"Summary retry batch {batch_count} complete: {success_count}/{len(article_ids)} successful (total: {total_processed})")

                # Delay between retry batches (use same delay as labeling)
                if article_ids and len(article_ids) == settings.AI_SUMMARY_BATCH_SIZE:
                    await asyncio.sleep(settings.AI_RETRY_BATCH_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"Error in summary retry batch {batch_count}: {e}")
                continue

        return total_processed


# Global summarizer instance
_summarizer_instance = None


def get_ai_summarizer() -> AISummarizer:
    """Get or create the global AI summarizer instance"""
    global _summarizer_instance
    if _summarizer_instance is None:
        _summarizer_instance = AISummarizer()
    return _summarizer_instance
