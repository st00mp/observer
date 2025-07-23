import os
import json
import httpx
import redis
import asyncio
from sqlalchemy.orm import Session
from typing import Dict, Optional, Any, List
from core.syntinel.db import Article, SessionLocal
from .collector.CryptoPanicCollector import fetch_cryptopanic

# @todos: 
# Créer fonction filter_duplicates()
# Créer fonction normalize_article()
# Créer fonction save_article()
# Créer fonction notify_scoring()

# Initialize Redis client at the top level for reuse
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)


def normalize(article: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw article dict to Article fields.
    
    This function maps the fields from the crawler's output format
    to the format expected by our Article model.
    
    Args:
        article: Raw article data from the collector
        
    Returns:
        Dict with normalized fields matching the Article model
    """
    return {
        "url": article.get("canonical") or article.get("internal"),
        "title": article.get("title", ""),
        "content": article.get("description", ""),  # Changed from content to description as per user request
        "markdown_content": "",  # Set to empty string as per user request
        "source": article.get("source", ""),
    }


def run_ingestion():
    """Run the complete ingestion pipeline.
    
    This function orchestrates the entire ingestion process:
    1. Collect new articles from sources
    2. Filter out duplicates
    3. Normalize and save new articles
    4. Notify the scoring module via Redis
    
    The design follows a simple batch-processing approach that can be called
    from a scheduler, cron job, or manually.
    """
    # 1. Open a DB session
    db = SessionLocal()
    try:
        # 2. List of collectors to execute (just one for now, can be expanded later)
        ALL_COLLECTORS = [fetch_cryptopanic]
        articles_processed = 0
        articles_saved = 0
        
        # 3. For each collector, fetch new articles
        for collector in ALL_COLLECTORS:
            print(f"Running collector: {collector.__name__}")
            new_articles = asyncio.run(collector())
            print(f"Found {len(new_articles)} articles from {collector.__name__}")

            # 4. Process each article
            for article in new_articles:
                articles_processed += 1
                
                # 4.1 Check if article already exists in database
                exists = db.query(Article).filter(Article.url == article["url"]).first()
                if exists:
                    print(f"Skipping duplicate article: {article['url']}")
                    continue  # Skip if already present

                # 4.2 Normalize article data (map fields to Article model)
                clean = normalize(article)

                # 4.3 Save normalized article to database
                article_obj = Article(**clean)
                db.add(article_obj)
                db.commit()  # Commit to get the ID
                db.refresh(article_obj)
                articles_saved += 1
                
                # 4.4 Publish event to Redis for scoring module
                # This notifies other modules that a new article is ready for processing
                redis_client.xadd("new_articles", {"id": str(article_obj.id)})
                print(f"Article saved and notified: {article_obj.id} - {article_obj.title[:50]}")

        # 5. Log pipeline completion
        print(f"Ingestion pipeline completed: {articles_processed} processed, {articles_saved} saved")
    finally:
        # 6. Always close the DB session
        db.close()