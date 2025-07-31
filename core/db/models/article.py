"""
Article model.
Represents articles collected from various sources.
"""

from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from ..session import Base

class Article(Base):
    """Article entity representing a collected content piece."""
    
    __tablename__ = "articles"
    
    # Identifiers and URLs
    id = Column(Integer, primary_key=True, index=True)  # Internal ID    
    article_id = Column(String, index=True)  # Article ID on CryptoPanic
    internal_url = Column(String, unique=True, index=True)  # URL on CryptoPanic
    canonical_url = Column(String)  # URL external (source original)
    
    # Content
    title = Column(String)
    content = Column(Text)  # Text description
    markdown_content = Column(Text)  # Markdown version if available
    
    # Metadata
    ingestion_timestamp = Column(DateTime, default=datetime.utcnow)  # Ingestion date
    published_at = Column(DateTime)  # Published date
    source = Column(String)  # Source domain
    
    # Scoring
    panic_score = Column(Float, default=0.0)
    recency_score = Column(Float, default=0.0)
    source_weight = Column(Float, default=1.0)
    total_score = Column(Float, default=0.0)
    processed = Column(Boolean, default=False, index=True)
    
    # Relationship with drafts
    drafts = relationship("Draft", back_populates="article")
    
    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:30]}...', source='{self.source}')>"
