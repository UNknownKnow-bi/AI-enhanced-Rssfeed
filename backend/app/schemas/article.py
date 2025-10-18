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
    created_at: datetime

    # Article status fields
    is_read: bool
    is_favorite: bool
    is_trashed: bool
    trashed_at: Optional[datetime] = None

    # Include source info
    source_name: Optional[str] = None
    source_icon: Optional[str] = None

    # AI Labeling fields
    ai_labels: Optional[dict] = None
    ai_label_status: Optional[str] = None
    vibe_coding: Optional[bool] = None  # Extracted from ai_labels for convenience

    # AI Summary fields
    ai_summary: Optional[str] = None
    ai_summary_status: Optional[str] = None
    ai_summary_generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    id: UUID
    source_id: UUID
    title: str
    description: Optional[str] = None
    cover_image: Optional[str] = None
    pub_date: Optional[datetime] = None
    created_at: datetime

    # Article status fields
    is_read: bool
    is_favorite: bool
    is_trashed: bool
    trashed_at: Optional[datetime] = None

    # Source info
    source_name: str
    source_icon: str

    # AI Labeling fields
    ai_labels: Optional[dict] = None
    ai_label_status: Optional[str] = None

    # AI Summary fields
    ai_summary: Optional[str] = None
    ai_summary_status: Optional[str] = None
    ai_summary_generated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Request schemas for status updates
class ArticleReadUpdate(BaseModel):
    is_read: bool


class ArticleFavoriteUpdate(BaseModel):
    is_favorite: bool


class EmptyTrashRequest(BaseModel):
    confirm: bool = False
