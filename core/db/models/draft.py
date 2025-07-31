"""
Draft model.
Represents content drafts generated from articles.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from ..session import Base

class Draft(Base):
    """Draft entity representing generated content from articles."""
    
    __tablename__ = "drafts"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    content = Column(Text)
    style = Column(String)
    version = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow)
    published = Column(Boolean, default=False)
    scheduled_for = Column(DateTime, nullable=True)
    
    # Relationship with parent article
    article = relationship("Article", back_populates="drafts")
    
    def __repr__(self):
        return f"<Draft(id={self.id}, article_id={self.article_id}, version={self.version})>"
