from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import math

from ...shared.db import get_db, Article
from shared.models import ScoredArticle

router = APIRouter(prefix="/score", tags=["scoring"])

@router.post("/")
async def score_articles(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Score and rank articles based on panic score, recency, and source weight
    """
    # Score articles in the background
    background_tasks.add_task(_score_articles, db)
    return {"status": "success", "message": "Scoring started in background"}

@router.get("/top")
async def get_top_articles(limit: int = 10, db: Session = Depends(get_db)):
    """
    Get the top scored articles
    """
    articles = db.query(Article).filter(Article.processed == True).order_by(Article.total_score.desc()).limit(limit).all()
    
    return [
        ScoredArticle(
            id=article.id,
            url=article.url,
            title=article.title,
            source=article.source,
            panic_score=article.panic_score,
            recency_score=article.recency_score,
            source_weight=article.source_weight,
            total_score=article.total_score
        )
        for article in articles
    ]

# Background task for scoring
async def _score_articles(db: Session):
    # Get unprocessed articles
    articles = db.query(Article).filter(Article.processed == False).all()
    
    for article in articles:
        # Calculate panic score (example algorithm)
        # This is a simple algorithm to detect "panic" words
        panic_words = ["emergency", "crisis", "urgent", "breaking", "alert", "warning", 
                       "disaster", "danger", "threat", "critical", "severe", "catastrophic"]
        
        content_lower = article.content.lower()
        panic_count = sum(content_lower.count(word) for word in panic_words)
        article_length = len(content_lower.split())
        
        # Normalize score
        if article_length > 0:
            panic_score = min(1.0, panic_count / (article_length * 0.01))  # Cap at 1.0
        else:
            panic_score = 0
            
        # Calculate recency score
        # More recent articles get higher scores
        now = datetime.utcnow()
        age_hours = (now - article.timestamp).total_seconds() / 3600
        recency_score = 1.0 / (1.0 + 0.1 * age_hours)  # Simple decay function
        
        # Source weight (could be configured per source)
        source_weight = {
            "trusted": 1.5,
            "verified": 1.3,
            "standard": 1.0,
            "questionable": 0.7,
            "unreliable": 0.5
        }.get(article.source, 1.0)
        
        # Calculate total score
        total_score = (panic_score * 0.5) + (recency_score * 0.3) + (source_weight * 0.2)
        
        # Update article
        article.panic_score = panic_score
        article.recency_score = recency_score
        article.source_weight = source_weight
        article.total_score = total_score
        article.processed = True
        
    # Commit changes
    db.commit()
