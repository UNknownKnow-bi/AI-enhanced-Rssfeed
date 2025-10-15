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


class RSSSourceUpdate(BaseModel):
    """
    Schema for updating RSS source fields.

    All fields are optional - provide only the fields you want to update.
    At least one field must be provided.
    """
    title: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "title": "Hacker News - Tech Stories",
                    "description": "Update only the title"
                },
                {
                    "icon": "🚀",
                    "description": "Update only the icon with an emoji"
                },
                {
                    "icon": "https://example.com/icon.png",
                    "description": "Update only the icon with an image URL"
                },
                {
                    "category": "Technology",
                    "description": "Update only the category"
                },
                {
                    "title": "My Favorite Blog",
                    "icon": "📰",
                    "category": "Blogs",
                    "description": "Update multiple fields at once"
                }
            ]
        }


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
