import os
import json
import httpx
import redis
from sqlalchemy.orm import Session
from shared.db import Article
from typing import Dict, Optional, Any

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# External service URL
CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai:11235")

def get_cached_article(url: str, db: Session) -> Optional[Article]:
    """
    Check if an article exists in the cache or database
    """
    cached_result = redis_client.get(f"crawl:{url}")
    if cached_result:
        cached_data = json.loads(cached_result)
        existing_article = db.query(Article).filter(Article.url == str(url)).first()
        if not existing_article:
            article = Article(
                url=str(url),
                title=cached_data.get("title", "No title"),
                content=cached_data.get("content", "No content"),
                markdown_content=cached_data.get("markdown", "No content"),
                source=cached_data.get("source", "unknown")
            )
            db.add(article)
            db.commit()
            db.refresh(article)
            return article
        return existing_article
    return db.query(Article).filter(Article.url == str(url)).first()

async def fetch_article_from_crawl4ai(url: str, source: str) -> Dict[str, Any]:
    """
    Fetch article content from the external Crawl4AI service
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{CRAWL4AI_URL}/ingest",
            json={"url": url, "mode": "article"}
        )
        if response.status_code != 200:
            return {"error": f"Crawl4AI service returned status code {response.status_code}"}
        data = response.json()
        return {
            "title": data.get("title", "No title"),
            "content": data.get("content", "No content"),
            "markdown": data.get("markdown", "No content"),
            "source": source
        }

def cache_article(url: str, article_data: Dict[str, Any], expire_seconds: int = 86400) -> None:
    """
    Cache article data in Redis
    """
    cache_key = f"crawl:{url}"
    redis_client.setex(cache_key, expire_seconds, json.dumps(article_data))
