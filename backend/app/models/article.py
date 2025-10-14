from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("rss_sources.id"), nullable=False, index=True)
    guid = Column(String, nullable=False, unique=True, index=True)  # Unique identifier from RSS feed
    title = Column(String, nullable=False)
    link = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    cover_image = Column(String, nullable=True)
    pub_date = Column(DateTime, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    source = relationship("RSSSource", back_populates="articles")
