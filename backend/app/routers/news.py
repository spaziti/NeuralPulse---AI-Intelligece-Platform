import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.config import settings
from backend.app.models import User, NewsArticle
from backend.app.schemas import (
    NewsArticleResponse, 
    NewsArticleCreate, 
    ChatRequest, 
    ChatResponse, 
    AnalyticsStatsResponse
)
from backend.app.services import NewsService
from backend.app.repositories import NewsArticleRepository
from backend.app.dependencies import get_db, get_current_active_user

router = APIRouter(prefix="/news", tags=["News Intelligence"])


@router.get("/analytics/stats", response_model=AnalyticsStatsResponse)
async def get_analytics_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Aggregate databases stats for dynamic sentiment, source, and timeline analytics."""
    query = select(NewsArticle)
    result = await db.execute(query)
    articles = result.scalars().all()
    
    total = len(articles)
    if total == 0:
        return AnalyticsStatsResponse(
            total_articles=0,
            positivity_ratio=0.0,
            sentiment_breakdown={"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0},
            sources_breakdown={},
            timeline_data=[]
        )
        
    pos_count = sum(1 for a in articles if a.sentiment == "POSITIVE")
    neg_count = sum(1 for a in articles if a.sentiment == "NEGATIVE")
    neu_count = sum(1 for a in articles if a.sentiment == "NEUTRAL")
    
    sentiment_breakdown = {
        "POSITIVE": pos_count,
        "NEGATIVE": neg_count,
        "NEUTRAL": neu_count
    }
    
    sources_breakdown = {}
    for a in articles:
        sources_breakdown[a.source] = sources_breakdown.get(a.source, 0) + 1
        
    timeline_map = {}
    for a in articles:
        date_str = a.published_at.strftime("%Y-%m-%d")
        timeline_map[date_str] = timeline_map.get(date_str, 0) + 1
        
    sorted_timeline = sorted(timeline_map.items())
    timeline_data = [{"date": k, "count": v} for k, v in sorted_timeline]
    
    positivity_ratio = pos_count / total
    
    return AnalyticsStatsResponse(
        total_articles=total,
        positivity_ratio=positivity_ratio,
        sentiment_breakdown=sentiment_breakdown,
        sources_breakdown=sources_breakdown,
        timeline_data=timeline_data
    )


@router.get("/search/semantic", response_model=List[NewsArticleResponse])
async def semantic_search(
    query: str,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Hybrid search combining PostgreSQL keyword matches and ChromaDB vector search via RRF."""
    news_service = NewsService(db)
    return await news_service.hybrid_search(query, limit=limit)


@router.post("/chat", response_model=ChatResponse)
async def news_rag_chat(
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieval-Augmented Generation (RAG) agent Chat over news archives."""
    from ai_agents.agent_manager import AIAgentManager
    agent = AIAgentManager()

    # 1. Optimize query using AgentManager by resolving coreferences in chat history
    search_query = await agent.optimize_query(payload.question, payload.chat_history or [])

    # 2. Perform hybrid search to retrieve context articles
    news_service = NewsService(db)
    sources = await news_service.hybrid_search(search_query, limit=4)
    
    # 3. Formulate references context text block
    context_texts = []
    for idx, article in enumerate(sources):
        context_texts.append(
            f"Source [{idx+1}]: {article.title} (Source: {article.source})\n"
            f"Summary: {article.summary or ''}\n"
            f"Content: {article.content or ''}\n"
        )
    context_str = "\n---\n".join(context_texts)

    # 4. Format conversation history (last 5 messages) for contextual synthesis
    history_str = ""
    if payload.chat_history:
        for msg in payload.chat_history[-5:]:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            history_str += f"{role}: {content}\n"
    
    # 5. Formulate Agent chat parameters
    system_prompt = (
        "You are the NeuralPulse AI News RAG Assistant. Answer the user's question using the provided context articles. "
        "Integrate the news details accurately. Cite the source using brackets like [1] or [2] matching the source indices. "
        "Keep the conversation history context in mind. "
        "If the context does not contain the answer, answer based on general knowledge but clearly state that the provided sources do not mention it. "
        "Respond ONLY with a JSON object in this format: "
        '{"answer": "Your detailed answer citing sources [1]..."}'
    )
    
    user_content = (
        f"Context News Articles:\n{context_str}\n\n"
        f"Conversation History:\n{history_str}\n"
        f"Latest Question: {payload.question}"
    )
    
    if settings.OPENAI_API_KEY:
        try:
            res = await agent._call_llm(system_prompt, user_content)
            answer = res.get("answer", "No answer could be generated.")
        except Exception as e:
            answer = f"Error calling AI chat: {e}. Fallback: Retrieval fetched {len(sources)} sources."
    else:
        # Heuristic Local Mock response if API key is missing
        if sources:
            answer = f"RAG Local Mode: Based on {len(sources)} parsed articles (specifically '{sources[0].title}'), here is the aggregated report. [1]"
        else:
            answer = "No matching context news sources found to resolve the query locally."
            
    return ChatResponse(answer=answer, sources=sources)


@router.get("/", response_model=List[NewsArticleResponse])
async def read_articles(
    skip: int = 0,
    limit: int = 50,
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    news_service = NewsService(db)
    return await news_service.list_articles(
        skip=skip, limit=limit, source=source, sentiment=sentiment, search_query=search
    )


@router.get("/{article_id}", response_model=NewsArticleResponse)
async def read_article(
    article_id: uuid.UUID, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    news_service = NewsService(db)
    article = await news_service.get_article(article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Article not found"
        )
    return article


@router.post("/", response_model=NewsArticleResponse, status_code=status.HTTP_201_CREATED)
async def create_article(
    article_in: NewsArticleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    news_service = NewsService(db)
    return await news_service.create_article(article_in)


@router.post("/sync", status_code=status.HTTP_202_ACCEPTED)
async def trigger_sync(
    source: str = "all",
    current_user: User = Depends(get_current_active_user),
):
    # Import worker task inside endpoint to avoid circular dependencies
    from workers.tasks import trigger_ingestion_task
    
    # Delay Celery task execution
    task = trigger_ingestion_task.delay(source)
    return {
        "status": "Sync process triggered in background",
        "task_id": task.id,
        "source": source
    }
