import httpx
from typing import Optional
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger(__name__)


class FaviconFetcher:
    """Service to fetch favicon URLs from websites"""

    @staticmethod
    async def fetch_favicon_url(url: str) -> Optional[str]:
        """
        Extract favicon URL from a website URL (RSS feed URL)

        Tries multiple common favicon locations:
        1. /favicon.ico
        2. Parse HTML for <link rel="icon">
        3. /apple-touch-icon.png

        Args:
            url: The RSS feed URL or website URL

        Returns:
            Favicon URL if found, None otherwise
        """
        try:
            # Parse the URL to get the base domain
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            # Try common favicon locations
            favicon_paths = [
                "/favicon.ico",
                "/apple-touch-icon.png",
                "/apple-touch-icon-precomposed.png",
            ]

            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                # First try to fetch the main page and parse for favicon
                try:
                    response = await client.get(base_url)
                    if response.status_code == 200:
                        # Look for favicon in HTML
                        html = response.text.lower()

                        # Search for <link rel="icon" href="...">
                        favicon_patterns = [
                            'rel="icon"',
                            'rel="shortcut icon"',
                            'rel="apple-touch-icon"',
                        ]

                        for pattern in favicon_patterns:
                            if pattern in html:
                                # Extract href attribute
                                start_idx = html.find(pattern)
                                href_start = html.find('href="', start_idx)
                                if href_start != -1:
                                    href_start += 6  # len('href="')
                                    href_end = html.find('"', href_start)
                                    if href_end != -1:
                                        favicon_href = response.text[href_start:href_end]
                                        # Make absolute URL
                                        favicon_url = urljoin(base_url, favicon_href)

                                        # Verify the favicon URL is accessible
                                        if await FaviconFetcher._verify_url(client, favicon_url):
                                            logger.info(f"Found favicon from HTML: {favicon_url}")
                                            return favicon_url
                except Exception as e:
                    logger.debug(f"Could not parse HTML for favicon from {base_url}: {e}")

                # Try common favicon paths
                for path in favicon_paths:
                    favicon_url = urljoin(base_url, path)
                    if await FaviconFetcher._verify_url(client, favicon_url):
                        logger.info(f"Found favicon at: {favicon_url}")
                        return favicon_url

                # If all else fails, return a generic favicon.ico URL
                # Even if it doesn't exist, browsers will handle it
                favicon_ico = urljoin(base_url, "/favicon.ico")
                logger.info(f"Using default favicon.ico: {favicon_ico}")
                return favicon_ico

        except Exception as e:
            logger.error(f"Error fetching favicon for {url}: {e}")
            return None

    @staticmethod
    async def _verify_url(client: httpx.AsyncClient, url: str) -> bool:
        """
        Verify if a URL is accessible and returns an image

        Args:
            client: httpx client to use
            url: URL to verify

        Returns:
            True if URL is accessible and is an image, False otherwise
        """
        try:
            response = await client.head(url, timeout=5.0)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                # Check if it's an image or allow empty content-type for .ico files
                if 'image' in content_type or url.endswith('.ico'):
                    return True
            # Some servers don't support HEAD, try GET
            elif response.status_code == 405:
                response = await client.get(url, timeout=5.0)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    if 'image' in content_type or url.endswith('.ico'):
                        return True
        except Exception as e:
            logger.debug(f"Could not verify URL {url}: {e}")

        return False
