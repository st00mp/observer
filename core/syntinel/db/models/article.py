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
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    title = Column(String)
    content = Column(Text)
    markdown_content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    source = Column(String)
    panic_score = Column(Float, default=0.0)
    recency_score = Column(Float, default=0.0)
    source_weight = Column(Float, default=1.0)
    total_score = Column(Float, default=0.0)
    processed = Column(Boolean, default=False, index=True)
    
    # Relationship with drafts
    drafts = relationship("Draft", back_populates="article")
    
    def __repr__(self):
        return f"<Article(id={self.id}, title='{self.title[:30]}...', source='{self.source}')>"
