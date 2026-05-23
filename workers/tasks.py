import asyncio
import logging
import uuid
from typing import Any
from workers.celery_app import celery_app
from backend.app.database import SessionLocal
from backend.app.repositories import NewsArticleRepository
from ingestion.pipeline import NewsIngestionPipeline
from ai_agents.agent_manager import AIAgentManager
from vector_store.chroma_client import chroma_client

logger = logging.getLogger("neuralpulse.worker.tasks")


def run_async(coro: Any) -> Any:
    """Helper function to run async coroutines in synchronous Celery tasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # Celery running within an event loop environment (e.g. eventlet/gevent)
        return asyncio.run_coroutine_threadsafe(coro, loop).result()
    else:
        return loop.run_until_complete(coro)


@celery_app.task(name="workers.tasks.trigger_ingestion_task")
def trigger_ingestion_task(source: str) -> int:
    """Background task to fetch news articles from ingestion streams."""
    logger.info(f"Starting news feed ingestion for source: {source}")
    
    async def _run():
        async with SessionLocal() as db:
            pipeline = NewsIngestionPipeline(db)
            articles = await pipeline.run_pipeline(source)
            
            logger.info(f"Successfully ingested {len(articles)} articles. Triggering analysis tasks.")
            for article in articles:
                # Trigger analysis as a sub-task
                analyze_article_task.delay(str(article.id))
            return len(articles)
            
    return run_async(_run())


@celery_app.task(name="workers.tasks.analyze_article_task")
def analyze_article_task(article_id: str) -> str:
    """Background task to analyze news articles with LLM agents and index into Vector Store."""
    logger.info(f"Starting analysis for article: {article_id}")
    
    async def _run():
        async with SessionLocal() as db:
            repo = NewsArticleRepository(db)
            article = await repo.get(uuid.UUID(article_id))
            if not article:
                logger.error(f"Article not found: {article_id}")
                return f"Failed: Article {article_id} not found"

            # Execute AI agent analysis
            agent_manager = AIAgentManager()
            analysis = await agent_manager.analyze_content(
                title=article.title, 
                content=article.content or ""
            )

            # Update article database entity with agent results
            article.summary = analysis.get("summary")
            article.sentiment = analysis.get("sentiment")
            article.sentiment_score = analysis.get("sentiment_score")
            article.credibility_score = analysis.get("credibility_score")
            article.key_entities = analysis.get("key_entities")
            await db.commit()

            # Store / Update embedding in ChromaDB vector store
            await chroma_client.upsert_article(
                article_id=str(article.id),
                title=article.title,
                content=article.content or "",
                summary=article.summary or "",
                metadata={
                    "source": article.source,
                    "sentiment": article.sentiment or "NEUTRAL",
                    "credibility": float(article.credibility_score or 0.8),
                    "entities": article.key_entities or "",
                    "published_at": article.published_at.isoformat()
                }
            )

            
            logger.info(f"Successfully completed analysis & embedding for article: {article_id}")
            return f"Success: Article {article_id} processed"

    return run_async(_run())
