import asyncio
import logging
import re
import time
from urllib.parse import urlparse
import requests

logger = logging.getLogger("neuralpulse.ingestion.scraper")


class Scraper:
    # Pre-compile regex patterns at the class level to avoid compilation overhead on every scrape
    RE_SCRIPT_STYLE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", flags=re.DOTALL | re.IGNORECASE)
    RE_COMMENTS = re.compile(r"<!--.*?-->", flags=re.DOTALL)
    RE_BLOCKS = re.compile(r"</?(p|div|h1|h2|h3|h4|h5|h6|li|tr|br)[^>]*>", flags=re.IGNORECASE)
    RE_TAGS = re.compile(r"<[^>]+>")
    RE_NEWLINES = re.compile(r"\n\s*\n+")
    RE_SPACES = re.compile(r"[ \t]+")

    def __init__(self) -> None:
        self.headers: dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }

    @staticmethod
    def normalize_source_name(url: str) -> str:
        """Extract domain from URL and convert to a clean capitalized publisher name."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith("www."):
                domain = domain[4:]
                
            # Common maps
            mapping: dict[str, str] = {
                "techcrunch.com": "TechCrunch",
                "wired.com": "Wired",
                "reuters.com": "Reuters",
                "bloomberg.com": "Bloomberg",
                "nasa.gov": "NASA News",
                "nytimes.com": "New York Times",
                "reddit.com": "Reddit News"
            }
            
            if domain in mapping:
                return mapping[domain]
            
            # Default fallback: return capitalized main subdomain name
            parts = domain.split(".")
            if len(parts) >= 2:
                # E.g. "news.google.com" -> Google
                return parts[-2].capitalize()
            return domain.capitalize()
            
        except Exception:
            return "Web News"

    @classmethod
    def clean_html_content(cls, html: str) -> str:
        """Strip tags, stylesheets, javascript, and decode entities to yield clean text."""
        if not html:
            return ""
            
        # 1. Remove script and style elements
        html = cls.RE_SCRIPT_STYLE.sub("", html)
        
        # 2. Remove HTML comments
        html = cls.RE_COMMENTS.sub("", html)
        
        # 3. Replace common block elements with newlines to preserve readability
        html = cls.RE_BLOCKS.sub("\n", html)
        
        # 4. Strip all remaining HTML tags
        text = cls.RE_TAGS.sub("", html)
        
        # 5. Decode basic HTML entities
        replacements: dict[str, str] = {
            "&nbsp;": " ",
            "&amp;": "&",
            "&quot;": '"',
            "&apos;": "'",
            "&lt;": "<",
            "&gt;": ">",
            "&ldquo;": '"',
            "&rdquo;": '"',
            "&lsquo;": "'",
            "&rsquo;": "'",
            "&ndash;": "-",
            "&mdash;": "-",
        }
        for entity, char in replacements.items():
            text = text.replace(entity, char)
            
        # 6. Normalize spacing/newlines
        text = cls.RE_NEWLINES.sub("\n\n", text)
        text = cls.RE_SPACES.sub(" ", text)
        return text.strip()

    async def scrape_full_text(self, url: str, max_retries: int = 3) -> str:
        """Scrape raw web page text asynchronously with exponential backoff retries."""
        loop = asyncio.get_running_loop()
        
        # Define blocking network request wrapper
        def fetch_html():
            return requests.get(url, headers=self.headers, timeout=5)

        for attempt in range(max_retries):
            try:
                # Execute blocking requests.get in threadpool to avoid lockups
                response = await loop.run_in_executor(None, fetch_html)
                response.raise_for_status()
                
                # Clean and parse text content
                return self.clean_html_content(response.text)
                
            except (requests.RequestException, Exception) as e:
                wait_time = 2 ** attempt
                logger.warning(
                    f"Scraping failed for {url} on attempt {attempt+1}/{max_retries}. "
                    f"Error: {e}. Retrying in {wait_time}s..."
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Scraper max retries exceeded for article link: {url}")
                    
        return ""
