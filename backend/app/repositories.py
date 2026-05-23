import uuid
from datetime import datetime
from typing import List, Optional, Type, TypeVar, Generic
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models import User, NewsArticle, IngestionLog, RefreshSession
from backend.app.schemas import UserCreate, NewsArticleCreate

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    async def get(self, id: uuid.UUID) -> Optional[ModelType]:
        query = select(self.model).where(self.model.id == id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        query = select(User).where(User.email == email)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, obj_in: UserCreate, hashed_password: str) -> User:
        db_obj = User(
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
        )
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj


class NewsArticleRepository(BaseRepository[NewsArticle]):
    def __init__(self, db: AsyncSession):
        super().__init__(NewsArticle, db)

    async def get_by_url(self, url: str) -> Optional[NewsArticle]:
        query = select(NewsArticle).where(NewsArticle.url == url)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, obj_in: NewsArticleCreate) -> NewsArticle:
        db_obj = NewsArticle(
            title=obj_in.title,
            url=obj_in.url,
            source=obj_in.source,
            content=obj_in.content,
            summary=obj_in.summary,
            sentiment=obj_in.sentiment,
            sentiment_score=obj_in.sentiment_score,
            credibility_score=obj_in.credibility_score,
            key_entities=obj_in.key_entities,
            published_at=obj_in.published_at,
        )
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_by_ids(self, ids: List[uuid.UUID]) -> List[NewsArticle]:
        if not ids:
            return []
        query = select(NewsArticle).where(NewsArticle.id.in_(ids))
        result = await self.db.execute(query)
        articles_map = {article.id: article for article in result.scalars().all()}
        return [articles_map[id] for id in ids if id in articles_map]

    async def search_by_keyword(self, query_str: str, limit: int = 50) -> List[NewsArticle]:
        """Fetch news articles matching keyword query via SQL ILIKE pattern matching."""
        if not query_str:
            return []
        query = select(NewsArticle).where(
            (NewsArticle.title.ilike(f"%{query_str}%")) |
            (NewsArticle.content.ilike(f"%{query_str}%"))
        ).order_by(desc(NewsArticle.published_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())


    async def get_articles(
        self,
        skip: int = 0,
        limit: int = 100,
        source: Optional[str] = None,
        sentiment: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[NewsArticle]:
        query = select(NewsArticle)

        if source:
            query = query.where(NewsArticle.source == source)
        if sentiment:
            query = query.where(NewsArticle.sentiment == sentiment)
        if search_query:
            query = query.where(
                (NewsArticle.title.ilike(f"%{search_query}%")) |
                (NewsArticle.content.ilike(f"%{search_query}%"))
            )

        query = query.order_by(desc(NewsArticle.published_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class IngestionLogRepository(BaseRepository[IngestionLog]):
    def __init__(self, db: AsyncSession):
        super().__init__(IngestionLog, db)

    async def create_log(
        self, source: str, status: str, articles_count: int, error_message: Optional[str] = None
    ) -> IngestionLog:
        db_obj = IngestionLog(
            source=source,
            status=status,
            articles_count=articles_count,
            error_message=error_message,
        )
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def get_latest_logs(self, limit: int = 10) -> List[IngestionLog]:
        query = select(IngestionLog).order_by(desc(IngestionLog.ran_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())


class RefreshSessionRepository(BaseRepository[RefreshSession]):
    def __init__(self, db: AsyncSession):
        super().__init__(RefreshSession, db)

    async def get_by_token(self, token: str) -> Optional[RefreshSession]:
        query = select(RefreshSession).where(
            RefreshSession.refresh_token == token,
            RefreshSession.is_revoked == False
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_session(
        self, user_id: uuid.UUID, token: str, expires_at: datetime
    ) -> RefreshSession:
        db_obj = RefreshSession(
            user_id=user_id,
            refresh_token=token,
            expires_at=expires_at
        )
        self.db.add(db_obj)
        await self.db.flush()
        return db_obj

    async def revoke_session(self, token: str) -> None:
        session = await self.get_by_token(token)
        if session:
            session.is_revoked = True
            await self.db.flush()

    async def revoke_all_user_sessions(self, user_id: uuid.UUID) -> None:
        query = select(RefreshSession).where(
            RefreshSession.user_id == user_id,
            RefreshSession.is_revoked == False
        )
        result = await self.db.execute(query)
        sessions = result.scalars().all()
        for session in sessions:
            session.is_revoked = True
        await self.db.flush()
