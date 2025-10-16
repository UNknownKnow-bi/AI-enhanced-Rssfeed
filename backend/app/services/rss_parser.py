import feedparser
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from app.services.favicon_fetcher import FaviconFetcher
from app.services.feed_cache import get_feed_cache
from app.core.config import settings

logger = logging.getLogger(__name__)


class RSSParser:
    """Service to parse and validate RSS feeds"""

    @staticmethod
    def _apply_limit_param(url: str, limit: int = 999) -> str:
        """
        Apply limit parameter to RSS feed URL to maximize article retrieval.

        Args:
            url: Original RSS feed URL
            limit: Maximum number of articles to request (default: 999)

        Returns:
            Modified URL with limit parameter added or updated

        Note:
            - Preserves all existing query parameters
            - Overwrites existing 'limit' parameter if present
            - Returns original URL unchanged if parsing fails or URL is invalid
        """
        try:
            # Handle empty or None URLs
            if not url or not isinstance(url, str):
                return url

            # Parse the URL
            parsed = urlparse(url)

            # Only process HTTP/HTTPS URLs
            if parsed.scheme not in ('http', 'https'):
                return url

            # Parse existing query parameters
            query_params = parse_qs(parsed.query, keep_blank_values=True)

            # Add or override the limit parameter
            query_params['limit'] = [str(limit)]

            # Rebuild query string
            new_query = urlencode(query_params, doseq=True)

            # Reconstruct the URL with new query string
            new_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))

            logger.info(f"Applied limit={limit} parameter: {url} -> {new_url}")
            return new_url

        except Exception as e:
            logger.warning(f"Failed to apply limit parameter to URL {url}: {e}. Using original URL.")
            return url

    @staticmethod
    async def _fetch_and_parse_with_fallback(
        url: str,
        client: httpx.AsyncClient
    ) -> tuple[Optional[Any], str, bool, Optional[str]]:
        """
        Fetch and parse RSS feed with automatic fallback to URL without limit parameter.

        This method implements a two-attempt strategy:
        1. First attempt: Fetch with limit=999 parameter to maximize article retrieval
        2. Fallback attempt: If first fails, retry with original URL (no limit parameter)

        Args:
            url: Original RSS feed URL (without limit parameter)
            client: Configured httpx AsyncClient for making requests

        Returns:
            Tuple of (parsed_feed, url_used, fallback_was_used, error_message):
            - parsed_feed: feedparser.FeedParserDict or None if both attempts failed
            - url_used: The URL that successfully fetched the feed
            - fallback_was_used: Boolean indicating if fallback was triggered
            - error_message: Detailed error message if both attempts failed, None on success

        Note:
            Fallback is triggered on:
            - HTTP status errors (4xx, 5xx)
            - Network/connection errors
            - Feed parsing errors (bozo=True with no entries)
        """
        # Track errors from both attempts
        first_attempt_error = None
        fallback_error = None

        # First attempt: with limit=999 parameter
        fetch_url_with_limit = RSSParser._apply_limit_param(url)

        try:
            response = await client.get(fetch_url_with_limit)
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            # Check if parsing succeeded (valid feed with entries or acceptable bozo)
            if not (feed.bozo and not feed.entries):
                logger.info(f"Successfully fetched with limit parameter: {url[:60]}... ({len(feed.entries)} entries)")
                return (feed, fetch_url_with_limit, False, None)

            # Parsing failed with bozo flag and no entries - trigger fallback
            bozo_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else "Invalid feed format"
            first_attempt_error = f"Feed parsing error: {bozo_msg}"
            logger.warning(
                f"Parsing failed with limit parameter (bozo={feed.bozo}, entries={len(feed.entries)}), "
                f"trying without: {url[:60]}..."
            )

        except httpx.HTTPStatusError as e:
            # Extract status code and reason
            status_code = e.response.status_code
            reason = e.response.reason_phrase if hasattr(e.response, 'reason_phrase') else str(status_code)
            first_attempt_error = f"HTTP {status_code}: {reason}"
            logger.warning(
                f"HTTP error with limit parameter (status {status_code}), "
                f"trying without: {url[:60]}..."
            )
        except httpx.RequestError as e:
            first_attempt_error = f"Network error: {str(e)}"
            logger.warning(
                f"Request error with limit parameter ({type(e).__name__}), "
                f"trying without: {url[:60]}..."
            )

        # Second attempt: without limit parameter (fallback)
        try:
            logger.info(f"Fallback attempt: fetching without limit parameter: {url[:60]}...")
            response = await client.get(url)  # Original URL without modification
            response.raise_for_status()
            feed = feedparser.parse(response.text)

            if not (feed.bozo and not feed.entries):
                logger.info(
                    f"✓ Fallback successful - fetched WITHOUT limit parameter: {url[:60]}... "
                    f"({len(feed.entries)} entries)"
                )
                return (feed, url, True, None)

            # Both attempts produced invalid feeds
            bozo_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else "Invalid feed format"
            fallback_error = f"Feed parsing error: {bozo_msg}"
            logger.error(
                f"Both attempts failed - feed invalid even without limit parameter: {url[:60]}... "
                f"(bozo={feed.bozo}, entries={len(feed.entries)})"
            )

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            reason = e.response.reason_phrase if hasattr(e.response, 'reason_phrase') else str(status_code)
            fallback_error = f"HTTP {status_code}: {reason}"
            logger.error(f"Fallback HTTP error (status {status_code}): {url[:60]}...")

        except httpx.RequestError as e:
            fallback_error = f"Network error: {str(e)}"
            logger.error(f"Fallback request error ({type(e).__name__}): {url[:60]}...")

        except Exception as e:
            fallback_error = f"Unexpected error: {str(e)}"
            logger.error(f"Fallback unexpected error: {e}")

        # Both attempts failed - return the most informative error message
        # Prefer fallback error since it's the simpler URL (more likely to be the real issue)
        if fallback_error:
            final_error = fallback_error
        elif first_attempt_error:
            final_error = first_attempt_error
        else:
            final_error = "Failed to fetch feed"

        return (None, url, True, final_error)

    @staticmethod
    async def validate_feed(url: str) -> Dict[str, Any]:
        """
        Validate an RSS feed URL by fetching and parsing it.

        Also caches the full feed data (feed info + articles) for later reuse
        in create_rss_source to avoid duplicate network requests.

        Implements automatic fallback: if fetching with limit=999 fails, retries
        with the original URL (no limit parameter).

        Returns:
            dict with keys: valid (bool), title (str), description (str), icon (str), error (str)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch and parse with automatic fallback logic
                feed, url_used, fallback_triggered, error_message = await RSSParser._fetch_and_parse_with_fallback(url, client)

                # Check if fetch failed completely (both attempts)
                if not feed:
                    return {
                        "valid": False,
                        "title": None,
                        "description": None,
                        "icon": None,
                        "error": error_message or "Failed to fetch feed"
                    }

                # Check if feed is valid
                if feed.bozo and not feed.entries:
                    error_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else "Invalid feed format"
                    return {
                        "valid": False,
                        "title": None,
                        "description": None,
                        "icon": None,
                        "error": error_msg
                    }

                # Extract feed metadata
                feed_title = feed.feed.get('title', 'Untitled Feed')
                feed_description = feed.feed.get('description', '')
                feed_link = feed.feed.get('link', '')

                # Fetch favicon
                favicon_url = await FaviconFetcher.fetch_favicon_url(url)

                # Parse all articles from the feed
                articles = []
                for entry in feed.entries:
                    article = RSSParser._parse_entry(entry)
                    if article:
                        articles.append(article)

                # Cache the full feed data for later reuse
                # This avoids duplicate network requests when create_rss_source is called
                cache = get_feed_cache(
                    ttl=settings.FEED_CACHE_TTL_SECONDS,
                    max_size=settings.FEED_CACHE_MAX_SIZE
                )

                feed_info = {
                    "title": feed_title,
                    "description": feed_description,
                    "link": feed_link,
                }

                # Cache using the URL that actually worked (might be with or without limit)
                await cache.set(
                    url=url_used,
                    feed_info=feed_info,
                    articles=articles,
                    favicon_url=favicon_url
                )

                # Log success with fallback status
                if fallback_triggered:
                    logger.info(
                        f"Validated and cached feed (using fallback): {feed_title} "
                        f"({len(articles)} articles, TTL={settings.FEED_CACHE_TTL_SECONDS}s)"
                    )
                else:
                    logger.info(
                        f"Validated and cached feed: {feed_title} "
                        f"({len(articles)} articles, TTL={settings.FEED_CACHE_TTL_SECONDS}s)"
                    )

                return {
                    "valid": True,
                    "title": feed_title,
                    "description": feed_description,
                    "icon": favicon_url,
                    "error": None
                }

        except httpx.RequestError as e:
            logger.error(f"Request error validating RSS feed {url}: {e}")
            return {
                "valid": False,
                "title": None,
                "description": None,
                "icon": None,
                "error": f"Failed to fetch feed: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error validating RSS feed {url}: {e}")
            return {
                "valid": False,
                "title": None,
                "description": None,
                "icon": None,
                "error": f"Unexpected error: {str(e)}"
            }

    @staticmethod
    async def fetch_feed(url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse an RSS feed, returning articles.

        Checks cache first to avoid duplicate network requests.
        If cache miss, fetches from network with automatic fallback logic.

        Implements automatic fallback: if fetching with limit=999 fails, retries
        with the original URL (no limit parameter).

        Returns:
            dict with keys: feed (dict), articles (list)
        """
        try:
            # Apply limit parameter to maximize article retrieval
            fetch_url_with_limit = RSSParser._apply_limit_param(url)

            # Check cache first - try both URL variants
            # This ensures we hit cache regardless of which URL variant worked previously
            cache = get_feed_cache(
                ttl=settings.FEED_CACHE_TTL_SECONDS,
                max_size=settings.FEED_CACHE_MAX_SIZE
            )

            # Try cache with limit parameter first
            cached_data = await cache.get(fetch_url_with_limit)

            if cached_data:
                # Cache hit with limit parameter
                logger.info(
                    f"Cache HIT (with limit): {fetch_url_with_limit[:60]}... "
                    f"({len(cached_data['articles'])} articles)"
                )
                return {
                    "feed": cached_data["feed_info"],
                    "articles": cached_data["articles"]
                }

            # Try cache with original URL (without limit) as fallback
            cached_data = await cache.get(url)

            if cached_data:
                # Cache hit with original URL (fallback variant)
                logger.info(
                    f"Cache HIT (without limit): {url[:60]}... "
                    f"({len(cached_data['articles'])} articles)"
                )
                return {
                    "feed": cached_data["feed_info"],
                    "articles": cached_data["articles"]
                }

            # Cache miss - fetch from network with fallback logic
            logger.info(f"Cache MISS - fetching from network: {url[:60]}...")

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch and parse with automatic fallback logic
                feed, url_used, fallback_triggered, error_message = await RSSParser._fetch_and_parse_with_fallback(url, client)

                # Check if fetch failed completely (both attempts)
                if not feed:
                    logger.error(f"Failed to fetch feed after fallback attempts: {url} - {error_message}")
                    return None

                if feed.bozo and not feed.entries:
                    logger.error(f"Invalid feed (no entries): {url}")
                    return None

                # Extract feed info
                feed_info = {
                    "title": feed.feed.get('title', 'Untitled Feed'),
                    "description": feed.feed.get('description', ''),
                    "link": feed.feed.get('link', ''),
                }

                # Extract articles
                articles = []
                for entry in feed.entries:
                    article = RSSParser._parse_entry(entry)
                    if article:
                        articles.append(article)

                # Cache the fetched data for future requests using the URL that worked
                # (Note: favicon_url not available here, set to None)
                await cache.set(
                    url=url_used,
                    feed_info=feed_info,
                    articles=articles,
                    favicon_url=None
                )

                # Log success with fallback status
                if fallback_triggered:
                    logger.info(
                        f"Fetched and cached feed (using fallback): {feed_info['title']} "
                        f"({len(articles)} articles)"
                    )
                else:
                    logger.info(
                        f"Fetched and cached feed: {feed_info['title']} "
                        f"({len(articles)} articles)"
                    )

                return {
                    "feed": feed_info,
                    "articles": articles
                }

        except Exception as e:
            logger.error(f"Error fetching RSS feed {url}: {e}")
            return None

    @staticmethod
    def _parse_entry(entry: Any) -> Optional[Dict[str, Any]]:
        """Parse a single RSS entry into an article dict"""
        try:
            # Get GUID (unique identifier)
            guid = entry.get('id') or entry.get('guid') or entry.get('link', '')
            if not guid:
                return None

            # Get title
            title = entry.get('title', 'Untitled')

            # Get link
            link = entry.get('link', '')

            # Get description/summary
            description = entry.get('summary', '') or entry.get('description', '')

            # Get content
            content = ''
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].get('value', '')
            elif description:
                content = description

            # Get published date
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

            # Try to extract cover image
            cover_image = None
            if hasattr(entry, 'media_content') and entry.media_content:
                cover_image = entry.media_content[0].get('url')
            elif hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                cover_image = entry.media_thumbnail[0].get('url')
            elif hasattr(entry, 'enclosures') and entry.enclosures:
                for enclosure in entry.enclosures:
                    if enclosure.get('type', '').startswith('image/'):
                        cover_image = enclosure.get('href')
                        break

            return {
                "guid": guid,
                "title": title,
                "link": link,
                "description": description[:500] if description else None,  # Limit description length
                "content": content,
                "pub_date": pub_date,
                "cover_image": cover_image,
            }

        except Exception as e:
            logger.error(f"Error parsing RSS entry: {e}")
            return None
