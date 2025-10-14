from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class RSSSource(Base):
    __tablename__ = "rss_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    icon = Column(String, nullable=True, default="📰")
    category = Column(String, nullable=False, default="未分类")
    unread_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_fetched = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="rss_sources")
    articles = relationship("Article", back_populates="source", cascade="all, delete-orphan")
