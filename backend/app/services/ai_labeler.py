import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from openai import OpenAI

from app.models.article import Article
from app.core.config import settings

logger = logging.getLogger(__name__)


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
3. 输出格式:只返回Json格式，包含所有文章的标签数组。
4. 标签都加上#号"""

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
                labels_map[article_id] = {
                    "identities": label_data.get("identities", []),
                    "themes": label_data.get("themes", []),
                    "extra": label_data.get("extra", []),
                    "vibe_coding": label_data.get("vibe_coding", False)
                }

        # If mapping by ID failed, try to match by order
        if not labels_map and len(labels_list) == len(articles):
            for i, article in enumerate(articles):
                if i < len(labels_list):
                    label_data = labels_list[i]
                    labels_map[str(article.id)] = {
                        "identities": label_data.get("identities", []),
                        "themes": label_data.get("themes", []),
                        "extra": label_data.get("extra", []),
                        "vibe_coding": label_data.get("vibe_coding", False)
                    }

        return labels_map

    async def process_pending_articles(self, db: AsyncSession) -> int:
        """
        Process pending articles in batches.

        Args:
            db: Database session

        Returns:
            Number of articles processed
        """
        try:
            # Query pending articles (limit to batch size)
            result = await db.execute(
                select(Article)
                .where(Article.ai_label_status == 'pending')
                .order_by(Article.created_at.asc())
                .limit(settings.AI_BATCH_SIZE)
            )
            articles = result.scalars().all()

            if not articles:
                logger.info("No pending articles to process")
                return 0

            # Only process if we have exactly the batch size (or this is the final batch)
            if len(articles) < settings.AI_BATCH_SIZE:
                logger.info(f"Only {len(articles)} pending articles found, waiting for more...")
                return 0

            logger.info(f"Processing {len(articles)} articles for AI labeling")

            # Update status to 'processing'
            article_ids = [article.id for article in articles]
            await db.execute(
                update(Article)
                .where(Article.id.in_(article_ids))
                .values(ai_label_status='processing')
            )
            await db.commit()

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
                logger.error("Failed to label articles - API returned no response")
                return 0

            # Parse response
            labels_map = self.parse_response(api_response, articles)

            # Update articles with labels
            success_count = 0
            for article in articles:
                article_id_str = str(article.id)
                if article_id_str in labels_map:
                    labels = labels_map[article_id_str]

                    # Check if article should be ignored
                    if "#可忽略" in labels.get("identities", []):
                        await db.execute(
                            update(Article)
                            .where(Article.id == article.id)
                            .values(
                                ai_labels=labels,
                                ai_label_status='done',
                                ai_label_error=None
                            )
                        )
                    else:
                        await db.execute(
                            update(Article)
                            .where(Article.id == article.id)
                            .values(
                                ai_labels=labels,
                                ai_label_status='done',
                                ai_label_error=None
                            )
                        )
                    success_count += 1
                    logger.info(f"Successfully labeled article {article.id}: {labels}")
                else:
                    # No labels found for this article
                    await db.execute(
                        update(Article)
                        .where(Article.id == article.id)
                        .values(
                            ai_label_status='error',
                            ai_label_error='No labels returned for this article'
                        )
                    )
                    logger.warning(f"No labels found for article {article.id}")

            await db.commit()
            logger.info(f"Successfully labeled {success_count}/{len(articles)} articles")
            return success_count

        except Exception as e:
            logger.error(f"Error in process_pending_articles: {e}")
            await db.rollback()
            return 0


# Global labeler instance
_labeler_instance = None


def get_ai_labeler() -> AILabeler:
    """Get or create the global AI labeler instance"""
    global _labeler_instance
    if _labeler_instance is None:
        _labeler_instance = AILabeler()
    return _labeler_instance
