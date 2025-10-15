import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class FeedCache:
    """
    In-memory cache for RSS feed validation data.

    Caches parsed feed data (feed info + articles) to avoid duplicate
    network requests when validate_feed() is followed by create_rss_source().

    Features:
    - TTL-based expiration (default 180 seconds)
    - LRU eviction when cache is full (max 999 feeds)
    - Thread-safe for async operations
    - Automatic URL normalization for cache keys
    """

    def __init__(self, ttl: int = 180, max_size: int = 999):
        """
        Initialize the feed cache.

        Args:
            ttl: Time-to-live in seconds (default 180s = 3 minutes)
            max_size: Maximum number of feeds to cache (default 999)
        """
        self._cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl)
        self._lock = asyncio.Lock()
        self._ttl = ttl
        self._max_size = max_size
        logger.info(f"FeedCache initialized: TTL={ttl}s, max_size={max_size}")

    @staticmethod
    def _normalize_url(url: str) -> str:
        """
        Normalize URL for consistent cache key generation.

        - Converts to lowercase
        - Sorts query parameters alphabetically
        - Removes fragment identifiers
        - Preserves all query parameters including 'limit'

        Args:
            url: RSS feed URL to normalize

        Returns:
            Normalized URL string suitable for use as cache key
        """
        try:
            if not url or not isinstance(url, str):
                return url

            parsed = urlparse(url.lower())

            # Parse and sort query parameters
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            sorted_params = sorted(query_params.items())
            normalized_query = urlencode(sorted_params, doseq=True)

            # Rebuild URL without fragment, with sorted params
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                normalized_query,
                ''  # Remove fragment
            ))

            return normalized

        except Exception as e:
            logger.warning(f"Failed to normalize URL {url}: {e}")
            return url

    async def get(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached feed data by URL.

        Args:
            url: RSS feed URL (will be normalized internally)

        Returns:
            Cached feed data dict or None if not found/expired

        Cache data structure:
        {
            "feed_info": {"title": "...", "description": "...", "link": "..."},
            "articles": [{"guid": "...", "title": "...", ...}, ...],
            "favicon_url": "https://...",
            "timestamp": datetime(...)
        }
        """
        cache_key = self._normalize_url(url)

        async with self._lock:
            cached_data = self._cache.get(cache_key)

            if cached_data:
                age = (datetime.now(timezone.utc) - cached_data["timestamp"]).total_seconds()
                logger.info(
                    f"Cache HIT for {cache_key[:60]}... "
                    f"(age: {age:.1f}s, articles: {len(cached_data.get('articles', []))})"
                )
                return cached_data
            else:
                logger.info(f"Cache MISS for {cache_key[:60]}...")
                return None

    async def set(
        self,
        url: str,
        feed_info: Dict[str, Any],
        articles: list,
        favicon_url: Optional[str] = None
    ) -> None:
        """
        Store feed data in cache.

        Args:
            url: RSS feed URL (will be normalized internally)
            feed_info: Feed metadata (title, description, link)
            articles: List of parsed article dicts
            favicon_url: Optional favicon URL
        """
        cache_key = self._normalize_url(url)

        cache_data = {
            "feed_info": feed_info,
            "articles": articles,
            "favicon_url": favicon_url,
            "timestamp": datetime.now(timezone.utc)
        }

        async with self._lock:
            self._cache[cache_key] = cache_data
            logger.info(
                f"Cache SET for {cache_key[:60]}... "
                f"({len(articles)} articles, TTL={self._ttl}s)"
            )

    async def clear(self) -> int:
        """
        Clear all cached feed data.

        Returns:
            Number of items cleared from cache
        """
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cache cleared ({count} items removed)")
            return count

    async def size(self) -> int:
        """
        Get current cache size.

        Returns:
            Number of feeds currently cached
        """
        async with self._lock:
            return len(self._cache)

    async def stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache stats (size, max_size, ttl)
        """
        async with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
            }


# Global singleton instance
_feed_cache_instance: Optional[FeedCache] = None


def get_feed_cache(ttl: int = 180, max_size: int = 999) -> FeedCache:
    """
    Get or create the global FeedCache singleton instance.

    Args:
        ttl: Time-to-live in seconds (only used on first initialization)
        max_size: Maximum cache size (only used on first initialization)

    Returns:
        Global FeedCache instance
    """
    global _feed_cache_instance

    if _feed_cache_instance is None:
        _feed_cache_instance = FeedCache(ttl=ttl, max_size=max_size)

    return _feed_cache_instance
