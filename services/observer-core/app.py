from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import httpx
import redis
import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import List, Optional
import asyncio

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="Observer Core")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observer:observer_password@postgres:5432/observer")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# External service URLs
CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai:8000")
WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://writer-agent:8000")

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

# Create tables
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models for request/response
class CrawlRequest(BaseModel):
    url: HttpUrl
    source: str
    force_refresh: bool = False

class ScoredArticle(BaseModel):
    id: int
    url: str
    title: str
    source: str
    panic_score: float
    recency_score: float
    source_weight: float
    total_score: float

class GenerateDraftRequest(BaseModel):
    article_id: int
    style: str = "serious"  # serious, sarcastic, troll

class DraftResponse(BaseModel):
    id: int
    article_id: int
    content: str
    style: str
    timestamp: datetime

class ScheduleRequest(BaseModel):
    draft_id: int
    publish_time: datetime

@app.get("/")
async def read_root():
    return {"status": "Observer Core is running"}

@app.post("/crawl")
async def crawl_url(request: CrawlRequest, db: Session = Depends(get_db)):
    """Endpoint to crawl a URL and store the data"""
    
    # Check Redis cache first
    cache_key = f"crawl:{request.url}"
    if not request.force_refresh:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            # If cached, check if already in database
            cached_article = json.loads(cached_data)
            db_article = db.query(Article).filter(Article.url == str(request.url)).first()
            
            if not db_article:
                # Create new article from cache
                db_article = Article(
                    url=cached_article["url"],
                    title=cached_article["title"],
                    content=cached_article["content"],
                    markdown_content=cached_article["markdown_content"],
                    source=request.source,
                    timestamp=datetime.fromisoformat(cached_article["timestamp"])
                )
                db.add(db_article)
                db.commit()
                db.refresh(db_article)
            
            return {
                "article_id": db_article.id,
                "title": db_article.title,
                "source": db_article.source,
                "from_cache": True
            }
    
    # If not cached or force refresh, call Crawl4AI service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CRAWL4AI_URL}/crawl",
                json={
                    "url": str(request.url),
                    "force_refresh": request.force_refresh,
                    "extraction_strategy": "default",
                    "cache_ttl": 3600
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to fetch from Crawl4AI")
                
            crawl_data = response.json()
            
            # Check if article already exists in DB
            db_article = db.query(Article).filter(Article.url == str(request.url)).first()
            
            if db_article:
                # Update existing article
                db_article.title = crawl_data["title"]
                db_article.content = crawl_data["content"]
                db_article.markdown_content = crawl_data["markdown_content"]
                db_article.timestamp = datetime.fromisoformat(crawl_data["timestamp"])
                db_article.source = request.source
                db_article.processed = False
            else:
                # Create new article
                db_article = Article(
                    url=crawl_data["url"],
                    title=crawl_data["title"],
                    content=crawl_data["content"],
                    markdown_content=crawl_data["markdown_content"],
                    timestamp=datetime.fromisoformat(crawl_data["timestamp"]),
                    source=request.source
                )
                db.add(db_article)
                
            db.commit()
            db.refresh(db_article)
            
            return {
                "article_id": db_article.id,
                "title": db_article.title,
                "source": db_article.source,
                "from_cache": False
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to crawl URL: {str(e)}")

@app.post("/score", response_model=List[ScoredArticle])
async def score_articles(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Score and rank articles"""
    # Get unprocessed articles
    unprocessed = db.query(Article).filter(Article.processed == False).all()
    
    # Process each article (calculate scores)
    for article in unprocessed:
        # Basic scoring logic (can be enhanced)
        # 1. Recency score: More recent = higher score (0-1)
        now = datetime.utcnow()
        hours_ago = (now - article.timestamp).total_seconds() / 3600
        recency_score = max(0, 1 - (hours_ago / 24))  # 0-1 scale, 1 = most recent
        
        # 2. Panic score: Count occurrences of panic words (0-1)
        panic_words = ["crash", "collapse", "disaster", "critical", "emergency", "plummet", 
                       "breaking", "urgent", "failure", "crisis", "danger", "alert"]
        content_lower = article.content.lower()
        panic_count = sum(content_lower.count(word) for word in panic_words)
        panic_score = min(1.0, panic_count / 10)  # Normalize to 0-1
        
        # 3. Source weight (default = 1.0, can be customized per source)
        source_weights = {
            "twitter": 1.2,
            "reddit": 0.9,
            "cnn": 1.1,
            "bbc": 1.1,
            "bloomberg": 1.2,
        }
        source_weight = source_weights.get(article.source.lower(), 1.0)
        
        # Calculate total score
        total_score = (panic_score * 0.5) + (recency_score * 0.3) + (source_weight * 0.2)
        
        # Update article with scores
        article.panic_score = panic_score
        article.recency_score = recency_score
        article.source_weight = source_weight
        article.total_score = total_score
        article.processed = True
    
    db.commit()
    
    # Get top 5 articles by score
    top_articles = db.query(Article).order_by(Article.total_score.desc()).limit(5).all()
    
    result = []
    for article in top_articles:
        result.append(ScoredArticle(
            id=article.id,
            url=article.url,
            title=article.title,
            source=article.source,
            panic_score=article.panic_score,
            recency_score=article.recency_score,
            source_weight=article.source_weight,
            total_score=article.total_score
        ))
        
    return result

@app.post("/generate-draft", response_model=DraftResponse)
async def generate_draft(request: GenerateDraftRequest, db: Session = Depends(get_db)):
    """Generate a post draft using Writer-Agent"""
    # Get the article
    article = db.query(Article).filter(Article.id == request.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    try:
        # Call Writer-Agent service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{WRITER_AGENT_URL}/generate",
                json={
                    "title": article.title,
                    "content": article.markdown_content[:500],  # Limit content length
                    "style": request.style,
                    "max_length": 280  # Twitter character limit
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to generate draft")
                
            draft_data = response.json()
            
            # Create and save draft
            draft = Draft(
                article_id=article.id,
                content=draft_data["content"],
                style=request.style
            )
            db.add(draft)
            db.commit()
            db.refresh(draft)
            
            return DraftResponse(
                id=draft.id,
                article_id=draft.article_id,
                content=draft.content,
                style=draft.style,
                timestamp=draft.timestamp
            )
            
    except Exception as e:
        # Fallback if Writer-Agent fails
        fallback_content = f"Breaking: {article.title} 🤯"
        draft = Draft(
            article_id=article.id,
            content=fallback_content,
            style="fallback"
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        return DraftResponse(
            id=draft.id,
            article_id=draft.article_id,
            content=draft.content,
            style="fallback",
            timestamp=draft.timestamp
        )

@app.get("/drafts", response_model=List[DraftResponse])
async def get_drafts(db: Session = Depends(get_db)):
    """Get all unpublished drafts"""
    drafts = db.query(Draft).filter(Draft.published == False).all()
    
    result = []
    for draft in drafts:
        result.append(DraftResponse(
            id=draft.id,
            article_id=draft.article_id,
            content=draft.content,
            style=draft.style,
            timestamp=draft.timestamp
        ))
        
    return result

@app.post("/schedule")
async def schedule_post(request: ScheduleRequest, db: Session = Depends(get_db)):
    """Schedule a draft for publication"""
    draft = db.query(Draft).filter(Draft.id == request.draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft.scheduled_for = request.publish_time
    db.commit()
    
    return {"status": "Draft scheduled for publication", "scheduled_time": request.publish_time}

@app.post("/publish/{draft_id}")
async def publish_post(draft_id: int, db: Session = Depends(get_db)):
    """Publish a draft immediately"""
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Here we would call the X API to publish
    # For now, just mark as published
    draft.published = True
    db.commit()
    
    return {"status": "Draft published successfully", "draft_id": draft_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
