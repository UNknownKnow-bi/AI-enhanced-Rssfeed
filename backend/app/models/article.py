from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


def get_utc_now():
    """Return current UTC time with timezone info"""
    return datetime.now(timezone.utc)


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
    pub_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)

    # Article status fields
    is_read = Column(Boolean, default=False, nullable=False)
    is_favorite = Column(Boolean, default=False, nullable=False)
    is_trashed = Column(Boolean, default=False, nullable=False)
    trashed_at = Column(DateTime(timezone=True), nullable=True)

    # AI Labeling fields
    ai_labels = Column(JSONB, nullable=True)  # Stores AI-generated labels as JSON
    ai_label_status = Column(String, default='pending', nullable=False, index=True)  # pending|processing|done|error
    ai_label_error = Column(Text, nullable=True)  # Error message if labeling fails

    # AI Summary fields
    ai_summary = Column(Text, nullable=True)  # AI-generated markdown summary
    ai_summary_status = Column(String, default='pending', nullable=False, index=True)  # pending|success|error|ignored
    ai_summary_error = Column(Text, nullable=True)  # Error message if summary generation fails
    ai_summary_generated_at = Column(DateTime(timezone=True), nullable=True)  # Timestamp when summary was generated

    # Relationships
    source = relationship("RSSSource", back_populates="articles")
