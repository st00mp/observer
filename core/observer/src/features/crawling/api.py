from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import httpx
import json

from ...shared.db import get_db, Article
from shared.models import CrawlRequest
import os
import redis
import json

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# External service URLs
CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai:8000")

router = APIRouter(prefix="/crawl", tags=["crawling"])

@router.post("/")
async def crawl_url(request: CrawlRequest, db: Session = Depends(get_db)):
    """
    Crawl a URL and store the extracted content
    """
    try:
        # Check Redis cache first if not forcing refresh
        if not request.force_refresh:
            cached_result = redis_client.get(f"crawl:{request.url}")
            if cached_result:
                cached_data = json.loads(cached_result)
                
                # Check if article exists in database
                existing_article = db.query(Article).filter(Article.url == str(request.url)).first()
                if not existing_article:
                    # Create new article from cache
                    article = Article(
                        url=str(request.url),
                        title=cached_data.get("title", "No title"),
                        content=cached_data.get("content", "No content"),
                        markdown_content=cached_data.get("markdown", "No content"),
                        source=request.source
                    )
                    db.add(article)
                    db.commit()
                    db.refresh(article)
                    return {"status": "success", "message": "Article fetched from cache", "id": article.id}
                else:
                    return {"status": "success", "message": "Article already exists", "id": existing_article.id}
        
        # No cache hit or forcing refresh - call Crawl4AI
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CRAWL4AI_URL}/crawl",
                json={"url": str(request.url), "render_js": True}
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Failed to crawl URL")
            
            crawl_result = response.json()
            
            # Cache the result
            redis_client.set(
                f"crawl:{request.url}", 
                json.dumps({
                    "title": crawl_result.get("title", "No title"),
                    "content": crawl_result.get("text_content", "No content"),
                    "markdown": crawl_result.get("markdown_content", "No content")
                }),
                ex=3600  # 1 hour expiry
            )
            
            # Check if article exists in database
            existing_article = db.query(Article).filter(Article.url == str(request.url)).first()
            
            if existing_article:
                # Update existing article
                existing_article.title = crawl_result.get("title", "No title")
                existing_article.content = crawl_result.get("text_content", "No content")
                existing_article.markdown_content = crawl_result.get("markdown_content", "No content")
                existing_article.source = request.source
                db.commit()
                db.refresh(existing_article)
                return {"status": "success", "message": "Article updated", "id": existing_article.id}
            else:
                # Create new article
                article = Article(
                    url=str(request.url),
                    title=crawl_result.get("title", "No title"),
                    content=crawl_result.get("text_content", "No content"),
                    markdown_content=crawl_result.get("markdown_content", "No content"),
                    source=request.source
                )
                db.add(article)
                db.commit()
                db.refresh(article)
                return {"status": "success", "message": "Article created", "id": article.id}
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
