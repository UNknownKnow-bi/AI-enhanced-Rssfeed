from pydantic import BaseModel, HttpUrl
from datetime import datetime
from uuid import UUID
from typing import Optional


class RSSSourceBase(BaseModel):
    url: str
    title: str
    description: Optional[str] = None
    icon: Optional[str] = "📰"
    category: str = "未分类"


class RSSSourceCreate(BaseModel):
    url: str
    title: str
    category: str = "未分类"


class RSSSourceResponse(RSSSourceBase):
    id: UUID
    user_id: UUID
    unread_count: int
    created_at: datetime
    last_fetched: Optional[datetime] = None

    class Config:
        from_attributes = True


class RSSValidateRequest(BaseModel):
    url: str


class RSSValidateResponse(BaseModel):
    valid: bool
    title: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    error: Optional[str] = None
