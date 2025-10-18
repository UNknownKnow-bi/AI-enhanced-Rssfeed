import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from openai import OpenAI

from app.models.article import Article
from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


def normalize_tag(tag: str) -> str:
    """
    Normalize a tag by ensuring it starts with '#'.

    Args:
        tag: Tag string to normalize

    Returns:
        Tag with '#' prefix
    """
    if not tag:
        return tag
    tag = tag.strip()
    if not tag.startswith('#'):
        tag = f'#{tag}'
    return tag


class AILabeler:
    """Service for labeling articles using DeepSeek AI API"""

    def __init__(self):
        """Initialize OpenAI client configured for DeepSeek API"""
        self.client = None
        self._initialized = False

    def _get_client(self) -> OpenAI:
        """Lazy initialization of OpenAI client"""
        if not self._initialized:
            self.client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
            self._initialized = True
        return self.client

    def build_messages(self, articles: List[Article]) -> List[Dict[str, str]]:
        """
        Build messages array for DeepSeek API.

        Args:
            articles: List of Article objects to label (max 3)

        Returns:
            List of message dicts with system and user messages
        """
        # System message with role definition and labels specification
        system_message = """你是一位专业的AI信息分析师，服务于一位身兼独立开发者和科技博主的客户。你的任务是根据他提供的资讯，精准地打上一组结构化的标签，以便他高效地进行信息分类和内容创作。

客户背景
1. 身份一：AI应用独立开发者。他使用 "vibe coding" 的敏捷开发风格，但实际的代码基础薄弱，关注AI模型进展、开发工具、应用架构设计、有深度的技术话题、实用的教程（尤其是Vibe coding相关）和宝贵的经验分享。
2. 身份二：AI博主。他需要寻找有趣、好玩、有延展性、贴近大众生活并有实际应用场景的AI信息，作为博客的创作素材。

标签体系
- 第一层：核心身份标签 (identities,必选其一或其二)
  - #独立开发必备
  - #博主素材
  - #双重价值 ：同时具备开发者价值和博主素材潜力的优质信息
  - #可忽略 ：广告推广、不明所以、或是不具备对用户有价值的信息，也无需再继续进行下面的逻辑判断，直接结束。
- 第二层：内容主题标签 (themes,根据内容选择最相关的1-2个)
  - #模型动态：关于新模型发布、更新、评测、技术突破的信息
  - #技术教程：step-by-step的开发指南、代码实现、工具用法等
  - #深度洞察：对AI行业、技术趋势、重要话题的深度分析和干货分享
  - #经验分享：个人或团队在开发、创业、学习过程中的心得与复盘
  - #AI应用 ：新的AI应用，AI应用的分析、评测或成功的商业案例
  - #趣味探索：有趣、好玩、有创意的AI应用或实验
第三层（extra）：其他未提及的内容主题，可综合生成，但不超过2个，每个不超6个字；
如果资讯内容涉及了AI vibe coding，AI开发产品，AI写代码，快速迭代、最小可行产品（MVP），必须加上 #VibeCoding 标签。

任务要求
1. 阅读并理解提供的资讯全文。
2. 严格遵循上述标签体系，输出最贴切的标签。
3. 输出格式:只返回Json格式，包含所有文章的标签数组。标签都加上#号,且至少返回可忽略标签"""

        # Build user message with article data
        articles_data = []
        for article in articles:
            article_dict = {
                "id": str(article.id),
                "title": article.title,
                "link": article.link,
                "description": article.description or "",
                "content": (article.content or article.description or "")[:3000],  # Limit content length
                "source_title": article.source.title if article.source else ""
            }
            articles_data.append(article_dict)

        user_message = f"""现在，请为以下 {len(articles)} 篇资讯打标：

{json.dumps(articles_data, ensure_ascii=False, indent=2)}

请返回JSON格式的数组，每个对象包含：
{{
  "id": "文章ID",
  "identities": ["标签数组"],
  "themes": ["主题标签数组"],
  "extra": ["其他标签数组"],
  "vibe_coding": true/false
}}"""

        return [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]

    async def call_deepseek_api(self, messages: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """
        Call DeepSeek API with retry logic.

        Args:
            messages: Messages array for the API

        Returns:
            Parsed JSON response or None on failure
        """
        client = self._get_client()
        retry_delays = [1, 2]  # Exponential backoff: 1s, 2s

        for attempt in range(settings.AI_MAX_RETRIES + 1):
            try:
                logger.info(f"Calling DeepSeek API (attempt {attempt + 1}/{settings.AI_MAX_RETRIES + 1})")

                # Call API using OpenAI SDK
                response = client.chat.completions.create(
                    model=settings.DEEPSEEK_MODEL,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    max_tokens=2000
                )

                # Extract content from response
                content = response.choices[0].message.content
                logger.info(f"DeepSeek API response received: {content[:200]}...")

                # Parse JSON response
                result = json.loads(content)
                return result

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                if attempt < settings.AI_MAX_RETRIES:
                    await asyncio.sleep(retry_delays[attempt])
                    continue
                return None

            except Exception as e:
                logger.error(f"DeepSeek API call failed (attempt {attempt + 1}): {e}")
                if attempt < settings.AI_MAX_RETRIES:
                    await asyncio.sleep(retry_delays[attempt])
                    continue
                return None

        logger.error("All retry attempts exhausted")
        return None

    def parse_response(self, api_response: Dict[str, Any], articles: List[Article]) -> Dict[str, Dict[str, Any]]:
        """
        Parse API response and map labels to articles.
        Normalizes all tags to ensure they start with '#'.

        Args:
            api_response: Response from DeepSeek API
            articles: Original articles list

        Returns:
            Dict mapping article_id to labels dict
        """
        labels_map = {}

        # Handle both array and single object responses
        if isinstance(api_response, list):
            labels_list = api_response
        elif isinstance(api_response, dict) and "articles" in api_response:
            labels_list = api_response["articles"]
        elif isinstance(api_response, dict) and "labels" in api_response:
            labels_list = api_response["labels"]
        elif isinstance(api_response, dict) and "results" in api_response:
            labels_list = api_response["results"]
        else:
            # Assume the response itself is the labels for all articles
            labels_list = [api_response]

        # Map labels by article ID
        for label_data in labels_list:
            if "id" in label_data:
                article_id = label_data["id"]
                # Normalize all tags to ensure they start with '#'
                labels_map[article_id] = {
                    "identities": [normalize_tag(tag) for tag in label_data.get("identities", [])],
                    "themes": [normalize_tag(tag) for tag in label_data.get("themes", [])],
                    "extra": [normalize_tag(tag) for tag in label_data.get("extra", [])],
                    "vibe_coding": label_data.get("vibe_coding", False)
                }

        # If mapping by ID failed, try to match by order
        if not labels_map and len(labels_list) == len(articles):
            for i, article in enumerate(articles):
                if i < len(labels_list):
                    label_data = labels_list[i]
                    # Normalize all tags to ensure they start with '#'
                    labels_map[str(article.id)] = {
                        "identities": [normalize_tag(tag) for tag in label_data.get("identities", [])],
                        "themes": [normalize_tag(tag) for tag in label_data.get("themes", [])],
                        "extra": [normalize_tag(tag) for tag in label_data.get("extra", [])],
                        "vibe_coding": label_data.get("vibe_coding", False)
                    }

        return labels_map

    async def _trigger_summarization(self, article_ids: List):
        """
        Trigger summarization for a list of article IDs in a background task.
        Each article gets its own database session for concurrency safety.

        Args:
            article_ids: List of article IDs to summarize
        """
        try:
            # Import here to avoid circular dependency
            from app.services.ai_summarizer import get_ai_summarizer

            if not article_ids:
                return

            logger.info(f"Triggering summarization for {len(article_ids)} articles")

            summarizer = get_ai_summarizer()

            # Process articles concurrently - each article uses its own session
            tasks = [summarizer._process_article_by_id(article_id) for article_id in article_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = sum(1 for r in results if r is True)
            logger.info(f"Summarization triggered: {success_count}/{len(article_ids)} successful")

        except Exception as e:
            logger.error(f"Error triggering summarization: {e}")

    async def process_pending_articles(self, db: AsyncSession, max_batches: int = None) -> int:
        """
        Process pending articles in batches.
        Collects all successfully labeled articles and triggers summarization once at the end.

        Args:
            db: Database session
            max_batches: Maximum number of batches to process (None = process all)

        Returns:
            Total number of articles processed
        """
        total_processed = 0
        batch_count = 0
        all_articles_to_summarize = []  # Collect all article IDs for final trigger

        while True:
            # Check if we've hit the max batch limit
            if max_batches is not None and batch_count >= max_batches:
                logger.info(f"Reached max batch limit ({max_batches}), stopping")
                break

            try:
                # Query pending articles (limit to batch size)
                # IMPORTANT: Eager load the 'source' relationship to avoid lazy loading errors
                result = await db.execute(
                    select(Article)
                    .options(selectinload(Article.source))
                    .where(Article.ai_label_status == 'pending')
                    .order_by(Article.created_at.asc())
                    .limit(settings.AI_BATCH_SIZE)
                )
                articles = result.scalars().all()

                if not articles:
                    logger.info(f"No more pending articles to process (total processed: {total_processed})")
                    break

                batch_count += 1
                logger.info(f"Processing batch {batch_count}: {len(articles)} articles for AI labeling")

                # Update status to 'processing' with conditional check
                article_ids = [article.id for article in articles]
                result = await db.execute(
                    update(Article)
                    .where(Article.id.in_(article_ids), Article.ai_label_status == 'pending')
                    .values(ai_label_status='processing')
                )
                await db.commit()

                # Check if any articles were actually updated
                if result.rowcount == 0:
                    logger.info(f"Batch {batch_count}: All articles already being processed, skipping")
                    continue
                elif result.rowcount < len(article_ids):
                    logger.info(f"Batch {batch_count}: Only {result.rowcount}/{len(article_ids)} articles updated to processing")

                # Build messages
                messages = self.build_messages(articles)

                # Call DeepSeek API
                api_response = await self.call_deepseek_api(messages)

                if not api_response:
                    # Mark as error
                    await db.execute(
                        update(Article)
                        .where(Article.id.in_(article_ids))
                        .values(
                            ai_label_status='error',
                            ai_label_error='Failed to get response from DeepSeek API after retries'
                        )
                    )
                    await db.commit()
                    logger.error(f"Batch {batch_count}: Failed to get API response")
                    continue  # Continue to next batch instead of stopping

                # Parse response
                labels_map = self.parse_response(api_response, articles)

                # Update articles with labels
                success_count = 0
                articles_to_summarize = []  # Track articles that need summarization

                for article in articles:
                    article_id_str = str(article.id)
                    if article_id_str in labels_map:
                        labels = labels_map[article_id_str]

                        # Check if article should be auto-trashed (labeled as 可忽略)
                        identities = labels.get('identities', [])
                        should_trash = '#可忽略' in identities

                        # Prepare update values
                        update_values = {
                            'ai_labels': labels,
                            'ai_label_status': 'done',
                            'ai_label_error': None
                        }

                        # Auto-trash articles labeled as 可忽略
                        if should_trash:
                            update_values['is_trashed'] = True
                            update_values['trashed_at'] = datetime.now(timezone.utc)
                            logger.info(f"Auto-trashing article {article.id} (labeled as #可忽略)")

                        # Update article with labels using conditional check
                        result = await db.execute(
                            update(Article)
                            .where(Article.id == article.id, Article.ai_label_status == 'processing')
                            .values(**update_values)
                        )
                        if result.rowcount > 0:
                            success_count += 1
                            logger.info(f"Successfully labeled article {article.id}: {labels}")

                            # Check if article should be summarized (not ignored)
                            if not should_trash:
                                articles_to_summarize.append(article.id)
                        else:
                            logger.warning(f"Article {article.id} status changed before labeling could complete")
                    else:
                        # No labels found for this article
                        await db.execute(
                            update(Article)
                            .where(Article.id == article.id, Article.ai_label_status == 'processing')
                            .values(
                                ai_label_status='error',
                                ai_label_error='No labels returned for this article'
                            )
                        )
                        logger.warning(f"No labels found for article {article.id}")

                await db.commit()
                total_processed += success_count
                logger.info(f"Batch {batch_count} complete: {success_count}/{len(articles)} labeled (total: {total_processed})")

                # Collect articles for summarization (will trigger once at end)
                if articles_to_summarize:
                    all_articles_to_summarize.extend(articles_to_summarize)
                    logger.info(f"Batch {batch_count}: Added {len(articles_to_summarize)} articles to summarization queue (total: {len(all_articles_to_summarize)})")

                # Small delay between batches to respect rate limits
                if articles and len(articles) == settings.AI_BATCH_SIZE:
                    await asyncio.sleep(settings.AI_LABEL_BATCH_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"Error in batch {batch_count}: {e}")
                await db.rollback()

                # Reset any articles stuck in 'processing' back to 'pending'
                if 'article_ids' in locals():
                    try:
                        await db.execute(
                            update(Article)
                            .where(Article.id.in_(article_ids))
                            .where(Article.ai_label_status == 'processing')
                            .values(ai_label_status='pending')
                        )
                        await db.commit()
                        logger.info(f"Reset {len(article_ids)} articles from 'processing' to 'pending' after error")
                    except Exception as reset_error:
                        logger.error(f"Failed to reset articles after error: {reset_error}")
                        await db.rollback()

                # Continue to next batch instead of stopping completely
                continue

        # All batches complete - trigger summarization once for all labeled articles
        if all_articles_to_summarize:
            logger.info(f"All labeling batches complete. Triggering summarization for {len(all_articles_to_summarize)} articles")
            asyncio.create_task(self._trigger_summarization(all_articles_to_summarize))
        else:
            logger.info("All labeling batches complete. No articles to summarize.")

        return total_processed

    async def process_error_articles(self, db: AsyncSession, max_batches: int = None) -> int:
        """
        Process articles with error status in batches (retry failed labeling).
        Collects all successfully labeled articles and triggers summarization once at the end.

        Args:
            db: Database session
            max_batches: Maximum number of batches to process (None = process all)

        Returns:
            Total number of articles successfully processed
        """
        total_processed = 0
        batch_count = 0
        all_articles_to_summarize = []  # Collect all article IDs for final trigger

        while True:
            # Check if we've hit the max batch limit
            if max_batches is not None and batch_count >= max_batches:
                logger.info(f"Reached max batch limit ({max_batches}), stopping retry process")
                break

            try:
                # Query error articles (limit to batch size)
                # IMPORTANT: Eager load the 'source' relationship to avoid lazy loading errors
                result = await db.execute(
                    select(Article)
                    .options(selectinload(Article.source))
                    .where(Article.ai_label_status == 'error')
                    .order_by(Article.created_at.asc())
                    .limit(settings.AI_BATCH_SIZE)
                )
                articles = result.scalars().all()

                if not articles:
                    logger.info(f"No error articles to retry (total processed: {total_processed})")
                    break

                batch_count += 1
                logger.info(f"Retrying batch {batch_count}: {len(articles)} error articles for AI labeling")

                # Update status to 'processing' with conditional check
                article_ids = [article.id for article in articles]
                result = await db.execute(
                    update(Article)
                    .where(Article.id.in_(article_ids), Article.ai_label_status == 'error')
                    .values(ai_label_status='processing')
                )
                await db.commit()

                # Check if any articles were actually updated
                if result.rowcount == 0:
                    logger.info(f"Retry batch {batch_count}: All articles already being processed, skipping")
                    continue
                elif result.rowcount < len(article_ids):
                    logger.info(f"Retry batch {batch_count}: Only {result.rowcount}/{len(article_ids)} articles updated to processing")

                # Build messages
                messages = self.build_messages(articles)

                # Call DeepSeek API
                api_response = await self.call_deepseek_api(messages)

                if not api_response:
                    # Mark as error again with updated error message
                    await db.execute(
                        update(Article)
                        .where(Article.id.in_(article_ids))
                        .values(
                            ai_label_status='error',
                            ai_label_error='Retry failed: No response from DeepSeek API after retries'
                        )
                    )
                    await db.commit()
                    logger.error(f"Retry batch {batch_count}: Failed to get API response")

                    # Wait before next batch
                    if articles and len(articles) == settings.AI_BATCH_SIZE:
                        await asyncio.sleep(settings.AI_RETRY_BATCH_DELAY_SECONDS)
                    continue

                # Parse response
                labels_map = self.parse_response(api_response, articles)

                # Update articles with labels (per-article handling for partial success)
                success_count = 0
                articles_to_summarize = []  # Track articles that need summarization in this batch

                for article in articles:
                    article_id_str = str(article.id)
                    if article_id_str in labels_map:
                        labels = labels_map[article_id_str]

                        # Check if article should be auto-trashed (labeled as 可忽略)
                        identities = labels.get('identities', [])
                        should_trash = '#可忽略' in identities

                        # Prepare update values
                        update_values = {
                            'ai_labels': labels,
                            'ai_label_status': 'done',
                            'ai_label_error': None
                        }

                        # Auto-trash articles labeled as 可忽略
                        if should_trash:
                            update_values['is_trashed'] = True
                            update_values['trashed_at'] = datetime.now(timezone.utc)
                            logger.info(f"Auto-trashing article {article.id} (retry, labeled as #可忽略)")

                        # Update article with labels using conditional check
                        result = await db.execute(
                            update(Article)
                            .where(Article.id == article.id, Article.ai_label_status == 'processing')
                            .values(**update_values)
                        )
                        if result.rowcount > 0:
                            success_count += 1
                            logger.info(f"Successfully retry-labeled article {article.id}: {labels}")

                            # Check if article should be summarized (not ignored)
                            if not should_trash:
                                articles_to_summarize.append(article.id)
                        else:
                            logger.warning(f"Retry: Article {article.id} status changed before labeling could complete")
                    else:
                        # No labels found for this article - mark as error with conditional check
                        await db.execute(
                            update(Article)
                            .where(Article.id == article.id, Article.ai_label_status == 'processing')
                            .values(
                                ai_label_status='error',
                                ai_label_error='Retry failed: No labels returned for this article'
                            )
                        )
                        logger.warning(f"Retry: No labels found for article {article.id}")

                await db.commit()
                total_processed += success_count
                logger.info(f"Retry batch {batch_count} complete: {success_count}/{len(articles)} labeled (total: {total_processed})")

                # Collect articles for summarization (will trigger once at end)
                if articles_to_summarize:
                    all_articles_to_summarize.extend(articles_to_summarize)
                    logger.info(f"Retry batch {batch_count}: Added {len(articles_to_summarize)} articles to summarization queue (total: {len(all_articles_to_summarize)})")

                # Wait between batches (configured delay)
                if articles and len(articles) == settings.AI_BATCH_SIZE:
                    logger.info(f"Waiting {settings.AI_RETRY_BATCH_DELAY_SECONDS} seconds before next retry batch...")
                    await asyncio.sleep(settings.AI_RETRY_BATCH_DELAY_SECONDS)

            except Exception as e:
                logger.error(f"Error in retry batch {batch_count}: {e}")
                await db.rollback()

                # Reset any articles stuck in 'processing' back to 'error'
                if 'article_ids' in locals():
                    try:
                        await db.execute(
                            update(Article)
                            .where(Article.id.in_(article_ids))
                            .where(Article.ai_label_status == 'processing')
                            .values(
                                ai_label_status='error',
                                ai_label_error=f'Retry failed with exception: {str(e)}'
                            )
                        )
                        await db.commit()
                        logger.info(f"Reset {len(article_ids)} articles from 'processing' to 'error' after exception")
                    except Exception as reset_error:
                        logger.error(f"Failed to reset articles after error: {reset_error}")
                        await db.rollback()

                # Continue to next batch instead of stopping completely
                continue

        # All retry batches complete - trigger summarization once for all labeled articles
        if all_articles_to_summarize:
            logger.info(f"All retry batches complete. Triggering summarization for {len(all_articles_to_summarize)} articles")
            asyncio.create_task(self._trigger_summarization(all_articles_to_summarize))
        else:
            logger.info("All retry batches complete. No articles to summarize.")

        return total_processed


# Global labeler instance
_labeler_instance = None


def get_ai_labeler() -> AILabeler:
    """Get or create the global AI labeler instance"""
    global _labeler_instance
    if _labeler_instance is None:
        _labeler_instance = AILabeler()
    return _labeler_instance
