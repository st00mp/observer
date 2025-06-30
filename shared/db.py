import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:pswd@postgres:5432/syntineldb")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database models
class Article(Base):
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
    
    # Relation avec les drafts
    drafts = relationship("Draft", back_populates="article")

class Draft(Base):
    __tablename__ = "drafts"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    content = Column(Text)
    style = Column(String)
    version = Column(Integer, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow)
    published = Column(Boolean, default=False)
    scheduled_for = Column(DateTime, nullable=True)
    
    # Relation avec l'article parent
    article = relationship("Article", back_populates="drafts")

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
