import feedparser
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from app.services.favicon_fetcher import FaviconFetcher

logger = logging.getLogger(__name__)


class RSSParser:
    """Service to parse and validate RSS feeds"""

    @staticmethod
    async def validate_feed(url: str) -> Dict[str, Any]:
        """
        Validate an RSS feed URL by fetching and parsing it

        Returns:
            dict with keys: valid (bool), title (str), description (str), icon (str), error (str)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse the feed
                feed = feedparser.parse(response.text)

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

                # Fetch favicon
                favicon_url = await FaviconFetcher.fetch_favicon_url(url)

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
        Fetch and parse an RSS feed, returning articles

        Returns:
            dict with keys: feed (dict), articles (list)
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse the feed
                feed = feedparser.parse(response.text)

                if feed.bozo and not feed.entries:
                    logger.error(f"Invalid feed: {url}")
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
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6])

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
