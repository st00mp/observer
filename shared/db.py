import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observer:observer_password@postgres:5432/observer")
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
    processed = Column(Boolean, default=False)

class Draft(Base):
    __tablename__ = "drafts"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer)
    content = Column(Text)
    style = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    published = Column(Boolean, default=False)
    scheduled_for = Column(DateTime, nullable=True)

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
