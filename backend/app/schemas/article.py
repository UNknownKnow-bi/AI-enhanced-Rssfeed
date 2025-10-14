from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional


class ArticleBase(BaseModel):
    title: str
    link: str
    description: Optional[str] = None
    content: Optional[str] = None
    cover_image: Optional[str] = None
    pub_date: Optional[datetime] = None


class ArticleResponse(ArticleBase):
    id: UUID
    source_id: UUID
    guid: str
    is_read: bool
    created_at: datetime

    # Include source info
    source_name: Optional[str] = None
    source_icon: Optional[str] = None

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    id: UUID
    source_id: UUID
    title: str
    description: Optional[str] = None
    cover_image: Optional[str] = None
    pub_date: Optional[datetime] = None
    is_read: bool
    created_at: datetime

    # Source info
    source_name: str
    source_icon: str

    class Config:
        from_attributes = True
