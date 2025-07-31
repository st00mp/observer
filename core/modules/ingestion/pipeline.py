import os
import json
import httpx
import redis
import asyncio
from typing import Dict, Optional, Any, List
from core.db import Article, SessionLocal
from .collector.cryptopanic_collector import fetch_cryptopanic

# Initialize Redis client at the top level for reuse
# Using environment variables with defaults for local development
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}")
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def normalize(article: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw article dict to Article fields.
    
    This function maps the fields from the crawler's output format
    to the format expected by our Article model.
    
    Args:
        article: Raw article data from the collector
        
    Returns:
        Dict with normalized fields matching the Article model
    """
    # Convert time_ago to datetime for published_at
    published_at = None
    time_ago = article.get("time_ago", "")
    if time_ago:
        try:
            # Analyze time_ago (format "10min", "1h", etc.)
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            
            if "min" in time_ago:
                minutes = int(time_ago.replace("min", "").strip())
                published_at = now - timedelta(minutes=minutes)
            elif "h" in time_ago:
                hours = int(time_ago.replace("h", "").strip())
                published_at = now - timedelta(hours=hours)
            elif "d" in time_ago:
                days = int(time_ago.replace("d", "").strip())
                published_at = now - timedelta(days=days)
        except Exception as e:
            print(f"Warning: Unable to parse time_ago '{time_ago}': {e}")
    
    return {
        # Identifiers and URLs
        "article_id": article.get("article_id", ""),
        "internal_url": article.get("internal", ""),
        "canonical_url": article.get("canonical", ""),
        
        # Content
        "title": article.get("title", ""),
        "content": article.get("description", ""),
        "markdown_content": "",  # Empty by default, to be enriched later
        
        # Metadata
        "source": article.get("source", ""),
        "published_at": published_at,
        
        # Scores are initialized by default in the model
    }


def run_ingestion(export_json=False, export_path=None):
    """Run the complete ingestion pipeline.
    
    This function orchestrates the entire ingestion process:
    1. Collect new articles from sources
    2. Filter out duplicates
    3. Normalize and save new articles
    4. Notify the scoring module via Redis
    
    The design follows a simple batch-processing approach that can be called
    from a scheduler, cron job, or manually.
    
    Args:
        export_json (bool): If True, exports collected articles to JSON format
        export_path (str): Path to the JSON export file. If None, uses a default name
    """
    # 1. Open a DB session
    db = SessionLocal()
    try:
        # For JSON export if enabled
        collected_articles = []
        
        # 2. List of collectors to execute (just one for now, can be expanded later)
        ALL_COLLECTORS = [fetch_cryptopanic]
        articles_processed = 0
        articles_saved = 0
        
        duplicates_skipped = 0
        missing_url_skipped = 0
        
        # 3. For each collector, fetch new articles
        for collector in ALL_COLLECTORS:
            print(f"Running collector: {collector.__name__}")
            new_articles = asyncio.run(collector())
            print(f"Found {len(new_articles)} articles from {collector.__name__}")

            # 4. Process each article
            for article in new_articles:
                articles_processed += 1
                
                # 4.1 Check if article already exists in database
                internal_url = article.get("internal", "")
                if not internal_url:
                    missing_url_skipped += 1
                    continue
                
                # 4.2 Verify if article already exists in database
                exists = db.query(Article).filter(Article.internal_url == internal_url).first()
                if exists:
                    duplicates_skipped += 1
                    continue  # Skip if already present

                # 4.3 Normalize article data (map fields to Article model)
                clean = normalize(article)
                
                # 4.4 Add to list of articles collected for JSON export if enabled
                if export_json:
                    collected_articles.append({
                        # Raw article data
                        "raw": article,
                        # Normalized article data
                        "normalized": clean
                    })

                # 4.5 Save normalized article to database
                article_obj = Article(**clean)
                db.add(article_obj)
                db.commit()  # Commit to get the ID
                # 4.6 Publish article ID to Redis for further processing
                # This notifies other modules that a new article is ready for processing
                try:
                    stream_add_result = redis_client.xadd(
                        "new_articles",  # Stream name
                        {"id": str(article_obj.id)},  # Message content
                        id="*"  # Auto-generated by Redis
                    )
                    articles_saved += 1
                except Exception as e:
                    print(f"Error publishing to Redis: {e}")
        
        # 5. Export JSON if requested
        if export_json and collected_articles:
            from datetime import datetime
            
            # Generate default file name if not specified
            if not export_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                export_path = f"syntinel_articles_{timestamp}.json"
            
            # Create a custom JSON encoder to handle datetime objects
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    return super().default(obj)
            
            # Generate JSON file
            try:
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(collected_articles, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                print(f"\n💾 Articles exportés dans {export_path}")
            except Exception as e:
                print(f"Erreur lors de l'export JSON: {e}")
        
        # 6. Report results
        print("\n" + "="*50)
        print("INGESTION REPORT")
        print("="*50)
        print(f"Articles processed:   {articles_processed}")
        print(f"Articles saved: {articles_saved}")
        if duplicates_skipped > 0:
            print(f"Duplicates skipped:  {duplicates_skipped}")
        if missing_url_skipped > 0:
            print(f"Missing URL skipped: {missing_url_skipped}")
        if export_json and collected_articles:
            print(f"Export JSON: {export_path}")
        print("="*50)
    finally:
        # 6. Always close the DB session
        db.close()