import os
import json
import httpx
import redis
import asyncio
from typing import Dict, Optional, Any, List
from core.syntinel.db import Article, SessionLocal
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
    # Conversion time_ago en datetime pour published_at
    published_at = None
    time_ago = article.get("time_ago", "")
    if time_ago:
        try:
            # Analyser time_ago (format "10min", "1h", etc.)
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
            print(f"Avertissement: Impossible d'analyser time_ago '{time_ago}': {e}")
    
    return {
        # Identifiants et URLs
        "article_id": article.get("article_id", ""),
        "internal_url": article.get("internal", ""),
        "canonical_url": article.get("canonical", ""),
        
        # Contenu
        "title": article.get("title", ""),
        "content": article.get("description", ""),
        "markdown_content": "",  # Vide par défaut, à enrichir plus tard
        
        # Métadonnées
        "source": article.get("source", ""),
        "published_at": published_at,
        
        # Les scores sont initialisés par défaut dans le modèle
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
        export_json (bool): Si True, exporte les articles collectés au format JSON
        export_path (str): Chemin du fichier d'export JSON. Si None, utilise un nom par défaut
    """
    # 1. Open a DB session
    db = SessionLocal()
    try:
        # Pour l'export JSON si activé
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
                # Déterminer l'URL interne pour la recherche de duplicats
                internal_url = article.get("internal", "")
                if not internal_url:
                    missing_url_skipped += 1
                    continue
                
                # Vérifier si l'article existe déjà par son URL interne (CryptoPanic)
                exists = db.query(Article).filter(Article.internal_url == internal_url).first()
                if exists:
                    duplicates_skipped += 1
                    continue  # Skip if already present

                # 4.2 Normalize article data (map fields to Article model)
                clean = normalize(article)
                
                # Ajouter à la liste d'articles collectés pour export JSON si activé
                if export_json:
                    collected_articles.append({
                        # Données brutes de l'article
                        "raw": article,
                        # Données normalisées
                        "normalized": clean
                    })

                # 4.3 Save normalized article to database
                article_obj = Article(**clean)
                db.add(article_obj)
                db.commit()  # Commit to get the ID
                # 4.4 Publish article ID to Redis for further processing
                # This notifies other modules that a new article is ready for processing
                try:
                    stream_add_result = redis_client.xadd(
                        "new_articles",  # Nom du stream
                        {"id": str(article_obj.id)},  # Contenu du message
                        id="*"  # Auto-généré par Redis
                    )
                    articles_saved += 1
                except Exception as e:
                    print(f"Error publishing to Redis: {e}")
        
        # 5. Export JSON si demandé
        if export_json and collected_articles:
            from datetime import datetime
            
            # Générer un nom de fichier par défaut si non spécifié
            if not export_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                export_path = f"syntinel_articles_{timestamp}.json"
            
            # Créer un encodeur JSON personnalisé pour gérer les objets datetime
            class DateTimeEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, datetime):
                        return obj.isoformat()
                    return super().default(obj)
            
            # Générer le fichier JSON
            try:
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(collected_articles, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
                print(f"\n💾 Articles exportés dans {export_path}")
            except Exception as e:
                print(f"Erreur lors de l'export JSON: {e}")
        
        # 6. Report results
        print("\n" + "="*50)
        print("RAPPORT D'INGESTION")
        print("="*50)
        print(f"Articles traités:   {articles_processed}")
        print(f"Articles sauvegardés: {articles_saved}")
        if duplicates_skipped > 0:
            print(f"Doublons ignorés:  {duplicates_skipped}")
        if missing_url_skipped > 0:
            print(f"Sans URL ignorés: {missing_url_skipped}")
        if export_json and collected_articles:
            print(f"Export JSON: {export_path}")
        print("="*50)
    finally:
        # 6. Always close the DB session
        db.close()