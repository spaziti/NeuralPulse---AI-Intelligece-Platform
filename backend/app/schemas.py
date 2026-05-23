import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool
    created_at: datetime


class NewsArticleBase(BaseModel):
    title: str
    url: str
    source: str
    content: Optional[str] = None
    summary: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None
    credibility_score: Optional[float] = None
    key_entities: Optional[str] = None
    briefing: Optional[str] = None
    published_at: datetime


class NewsArticleCreate(NewsArticleBase):
    pass


class NewsArticleResponse(NewsArticleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class IngestionLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    status: str
    articles_count: int
    error_message: Optional[str] = None
    ran_at: datetime


class WSNewsMessage(BaseModel):
    type: str
    timestamp: datetime = datetime.utcnow()
    payload: NewsArticleResponse


from typing import List, Dict, Any

class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[Dict[str, Any]]] = []


class ChatResponse(BaseModel):
    answer: str
    sources: List[NewsArticleResponse]


class AnalyticsStatsResponse(BaseModel):
    total_articles: int
    positivity_ratio: float
    sentiment_breakdown: Dict[str, int]
    sources_breakdown: Dict[str, int]
    timeline_data: List[Dict[str, Any]]

