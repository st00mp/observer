from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from core.syntinel.db import get_db, Article
from shared.models import ScoredArticle
from core.syntinel.modules.scoring.service import score_articles_batch

router = APIRouter(prefix="/score", tags=["scoring"])

@router.post("/")
async def score_articles(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Score and rank articles based on panic score, recency, and source weight
    """
    # Score articles in the background
    background_tasks.add_task(score_articles_batch, db)
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
