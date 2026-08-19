from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.api.db.session import Base


class SearchQuery(Base):
    __tablename__ = "searches"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String(255), nullable=False)
    platform = Column(String(50), default="reddit")
    total_comments = Column(Integer, default=0)
    positive_pct = Column(Float, default=0.0)
    negative_pct = Column(Float, default=0.0)
    neutral_pct = Column(Float, default=0.0)
    positive_summary = Column(Text, nullable=True)
    negative_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    comments = relationship("AnalyzedComment", back_populates="search", cascade="all, delete-orphan")


class AnalyzedComment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("searches.id"), nullable=False)
    external_id = Column(String(100), nullable=True)
    original_text = Column(Text, nullable=False)
    cleaned_text = Column(Text, nullable=False)
    sentiment_label = Column(String(20), nullable=False)
    sentiment_score = Column(Float, nullable=False)

    search = relationship("SearchQuery", back_populates="comments")