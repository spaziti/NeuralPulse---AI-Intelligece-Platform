import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from backend.app.config import settings
from backend.app.auth.auth_utils import verify_password, get_password_hash, create_access_token, create_refresh_token
from backend.app.models import User, NewsArticle
from backend.app.schemas import UserCreate, NewsArticleCreate, NewsArticleResponse
from backend.app.repositories import UserRepository, NewsArticleRepository, RefreshSessionRepository
from backend.app.redis_client import redis_client

logger = logging.getLogger("neuralpulse.services")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.user_repo = UserRepository(db)
        self.session_repo = RefreshSessionRepository(db)

    async def register(self, user_in: UserCreate) -> User:
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists."
            )
        hashed_password = get_password_hash(user_in.password)
        return await self.user_repo.create(user_in, hashed_password)

    async def authenticate(self, email: str, password: str) -> dict:
        user = await self.user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )
        
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            subject=user.email, expires_delta=access_token_expires
        )
        
        refresh_token = create_refresh_token(subject=user.email)
        expires_at = datetime.utcnow() + timedelta(days=7)
        await self.session_repo.create_session(user.id, refresh_token, expires_at)
        
        return {
            "user": user,
            "access_token": access_token,
            "refresh_token": refresh_token
        }

    async def refresh_access_token(self, refresh_token: str) -> dict:
        try:
            payload = jwt.decode(
                refresh_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
            )
            email: str = payload.get("sub")
            token_type: str = payload.get("type")
            if email is None or token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token payload"
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

        session = await self.session_repo.get_by_token(refresh_token)
        if not session or session.expires_at < datetime.utcnow() or session.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is expired, revoked, or invalid"
            )

        user = await self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token is inactive or not found"
            )

        await self.session_repo.revoke_session(refresh_token)

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            subject=user.email, expires_delta=access_token_expires
        )
        new_refresh_token = create_refresh_token(subject=user.email)
        new_expires_at = datetime.utcnow() + timedelta(days=7)
        
        await self.session_repo.create_session(user.id, new_refresh_token, new_expires_at)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token
        }

    async def logout_session(self, refresh_token: str) -> None:
        await self.session_repo.revoke_session(refresh_token)


class NewsService:
    def __init__(self, db: AsyncSession):
        self.article_repo = NewsArticleRepository(db)

    async def list_articles(
        self,
        skip: int = 0,
        limit: int = 100,
        source: Optional[str] = None,
        sentiment: Optional[str] = None,
        search_query: Optional[str] = None,
    ) -> List[NewsArticle]:
        return await self.article_repo.get_articles(
            skip=skip,
            limit=limit,
            source=source,
            sentiment=sentiment,
            search_query=search_query,
        )

    async def get_article(self, article_id: uuid.UUID) -> Optional[NewsArticle]:
        return await self.article_repo.get(article_id)

    async def create_article(self, article_in: NewsArticleCreate) -> NewsArticle:
        existing = await self.article_repo.get_by_url(article_in.url)
        if existing:
            return existing

        article = await self.article_repo.create(article_in)
        await self.publish_realtime_article(article)
        return article

    async def publish_realtime_article(self, article: NewsArticle) -> None:
        try:
            schema_data = NewsArticleResponse.model_validate(article)
            message = {
                "type": "NEW_ARTICLE",
                "timestamp": schema_data.created_at.isoformat(),
                "payload": schema_data.model_dump(mode="json")
            }
            await redis_client.publish("live_news_feed", json.dumps(message))
        except Exception as e:
            logger.error(f"Error publishing news article to Redis: {e}")
            pass
