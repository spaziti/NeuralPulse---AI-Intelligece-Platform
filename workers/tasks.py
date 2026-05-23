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

            # 1. Fetch similar historical articles from ChromaDB to support contradiction detection
            similar_articles_data = []
            try:
                hits = await chroma_client.query_articles(query_text=article.title, n_results=4)
                similar_uuids = []
                for hit in hits:
                    # Ensure we don't query comparison against the current article itself
                    if hit["id"] != article_id:
                        try:
                            similar_uuids.append(uuid.UUID(hit["id"]))
                        except ValueError:
                            pass
                if similar_uuids:
                    resolved = await repo.get_by_ids(similar_uuids)
                    for item in resolved:
                        similar_articles_data.append({
                            "title": item.title,
                            "content": item.content or ""
                        })
            except Exception as e:
                logger.warning(f"Could not retrieve comparison articles for contradiction checking: {e}")

            # 2. Execute multi-agent state graph workflow
            from ai_agents.intelligence_workflow import intelligence_workflow
            workflow_state = {
                "title": article.title,
                "content": article.content or "",
                "similar_articles": similar_articles_data,
                "summary": "",
                "sentiment": "NEUTRAL",
                "sentiment_score": 0.0,
                "credibility_score": 0.8,
                "credibility_explanation": "",
                "trends": [],
                "key_entities": [],
                "contradictions": [],
                "briefing": ""
            }

            result_state = await intelligence_workflow.ainvoke(workflow_state)

            # 3. Update database model attributes
            article.summary = result_state.get("summary")
            article.sentiment = result_state.get("sentiment")
            article.sentiment_score = result_state.get("sentiment_score")
            article.credibility_score = result_state.get("credibility_score")
            
            entities = result_state.get("key_entities")
            if isinstance(entities, list):
                article.key_entities = ", ".join(entities)
            else:
                article.key_entities = str(entities)
                
            article.briefing = result_state.get("briefing")
            await db.commit()

            # 4. Store / Update embedding in ChromaDB vector store
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

            logger.info(f"Successfully completed multi-agent analysis & embedding for article: {article_id}")
            return f"Success: Article {article_id} processed"

    return run_async(_run())
