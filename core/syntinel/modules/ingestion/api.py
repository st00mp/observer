from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import httpx

from core.syntinel.db import get_db, Article
from shared.models import CrawlRequest
from core.syntinel.modules.ingestion.pipeline import get_cached_article, fetch_article_from_crawl4ai, cache_article

router = APIRouter(prefix="/ingest", tags=["ingestion"])

@router.post("/")
async def crawl_url(request: CrawlRequest, db: Session = Depends(get_db)):
    """
    Crawl a URL and store the extracted content
    """
    try:
        # Check Redis cache first if not forcing refresh
        if not request.force_refresh:
            existing_article = get_cached_article(request.url, db)
            if existing_article:
                return {"status": "success", "message": "Article already exists", "id": existing_article.id}
        
        # If not in cache or force refresh, fetch from crawl4ai
        article_data = await fetch_article_from_crawl4ai(request.url, request.source)
        if article_data.get("error"):
            raise HTTPException(status_code=400, detail=article_data["error"])
        
        # Store article in database
        article = Article(
            url=str(request.url),
            title=article_data.get("title", "No title"),
            content=article_data.get("content", "No content"),
            markdown_content=article_data.get("markdown", "No content"),
            source=request.source
        )
        db.add(article)
        db.commit()
        db.refresh(article)
        
        # Cache for future use
        cache_article(request.url, article_data)
        
        return {"status": "success", "message": "Article crawled successfully", "id": article.id}
    
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Error communicating with crawling service: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Crawling error: {str(e)}")

@router.get("/{article_id}")
async def get_article(article_id: int, db: Session = Depends(get_db)):
    """
    Get article by ID
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    return article
