import asyncio
import logging
from typing import List
import requests
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.models import NewsArticle
from backend.app.schemas import NewsArticleCreate
from backend.app.repositories import NewsArticleRepository, IngestionLogRepository
from ingestion.rss_parser import RSSParser
from ingestion.scraper import Scraper

logger = logging.getLogger("neuralpulse.ingestion")


class NewsIngestionPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.article_repo = NewsArticleRepository(db)
        self.log_repo = IngestionLogRepository(db)
        self.scraper = Scraper()

    async def _fetch_xml(self, url: str) -> str:
        """Fetch raw XML payload of RSS feed in a non-blocking thread executor."""
        loop = asyncio.get_running_loop()
        headers = {"User-Agent": settings.INGESTION_USER_AGENT}
        
        def make_get():
            res = requests.get(url, headers=headers, timeout=settings.INGESTION_TIMEOUT)
            res.raise_for_status()
            return res.text
            
        return await loop.run_in_executor(None, make_get)

    async def _scrape_article_content(self, item: dict, sem: asyncio.Semaphore) -> dict:
        """Helper to scrape full body content for a single feed item under concurrency limit."""
        async with sem:
            full_text = await self.scraper.scrape_full_text(item["url"])
            item["content"] = full_text if full_text else item["summary"]
            return item

    async def run_pipeline(self, source: str) -> List[NewsArticle]:
        """Fetch news feeds, scrape full text, normalize sources, and save to Postgres."""
        logger.info(f"Initiating production news ingestion pipeline for: {source}")
        
        # Determine feed targets
        urls_to_crawl = []
        if source == "all":
            urls_to_crawl = settings.INGESTION_FEEDS
        elif source.startswith("http"):
            urls_to_crawl = [source]
        else:
            # Check if source is registered in settings feed list as substring
            matched_feeds = [f for f in settings.INGESTION_FEEDS if source.lower() in f.lower()]
            if matched_feeds:
                urls_to_crawl = matched_feeds
            else:
                logger.warning(f"Crawl source '{source}' unrecognized. Defaulting to settings list.")
                urls_to_crawl = settings.INGESTION_FEEDS

        status = "SUCCESS"
        error_msg = None
        created_articles = []

        try:
            # 1. Fetch XML and parse articles from all targets
            parsed_items = []
            for feed_url in urls_to_crawl:
                try:
                    logger.info(f"Crawling XML feed: {feed_url}")
                    xml_content = await self._fetch_xml(feed_url)
                    items = RSSParser.parse_xml_feed(xml_content)
                    logger.info(f"Parsed {len(items)} feed items from {feed_url}")
                    parsed_items.extend(items)
                except Exception as e:
                    logger.error(f"Failed to crawl XML feed from {feed_url}: {e}")
                    # Continue crawling other feeds even if one fails
                    continue

            # 2. Check duplicates (deduplicate against existing URLs)
            new_items = []
            for item in parsed_items:
                existing = await self.article_repo.get_by_url(item["url"])
                if existing:
                    logger.debug(f"Article deduplicated: {item['url']}")
                    continue
                new_items.append(item)

            logger.info(f"Identified {len(new_items)} new articles for full-text scraping.")

            # 3. Asynchronously scrape full body texts in parallel
            if new_items:
                # Limit concurrency to avoid overloading target servers
                sem = asyncio.Semaphore(5)
                tasks = [self._scrape_article_content(item, sem) for item in new_items]
                scraped_items = await asyncio.gather(*tasks)

                # 4. Normalize sources and save to database
                for item in scraped_items:
                    normalized_src = Scraper.normalize_source_name(item["url"])
                    
                    article_in = NewsArticleCreate(
                        title=item["title"],
                        url=item["url"],
                        source=normalized_src,
                        content=item["content"],
                        summary=None,
                        sentiment=None,
                        sentiment_score=None,
                        credibility_score=None,
                        key_entities=None,
                        published_at=item["published_at"]
                    )
                    
                    db_article = await self.article_repo.create(article_in)
                    created_articles.append(db_article)

                await self.db.flush()
                logger.info(f"Ingestion pipeline populated {len(created_articles)} records to PostgreSQL.")

        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            logger.error(f"Fatal error during ingestion pipeline execution: {e}")
            raise e
            
        finally:
            # 5. Save audit execution log
            try:
                log_source_name = source if len(source) < 50 else source[:47] + "..."
                await self.log_repo.create_log(
                    source=log_source_name,
                    status=status,
                    articles_count=len(created_articles),
                    error_message=error_msg
                )
                await self.db.commit()
            except Exception as log_error:
                logger.error(f"Failed to save ingestion log record: {log_error}")
                
        return created_articles
