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
    
    # Identifiants et URLs
    id = Column(Integer, primary_key=True, index=True)  # ID interne
    article_id = Column(String, index=True)  # ID de l'article sur CryptoPanic
    internal_url = Column(String, unique=True, index=True)  # URL sur CryptoPanic
    canonical_url = Column(String)  # URL externe (source originale)
    
    # Contenu
    title = Column(String)
    content = Column(Text)  # Description textuelle
    markdown_content = Column(Text)  # Version markdown si disponible
    
    # Métadonnées
    ingestion_timestamp = Column(DateTime, default=datetime.utcnow)  # Date d'ingestion
    published_at = Column(DateTime)  # Date de publication estimée
    source = Column(String)  # Source de l'article (domaine)
    
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
