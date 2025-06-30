import os
import json
import httpx
import redis
from sqlalchemy.orm import Session
from shared.db import Article
from typing import Dict, Optional, Any
import asyncio
from shared.db import SessionLocal
from .collector.CryptoPanicCollector import fetch_cryptopanic


# @todos: 
# Créer fonction filter_duplicates()
# Créer fonction normalize_article()
# Créer fonction save_article()
# Créer fonction notify_scoring()


def normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize raw article dict to Article fields."""
    return {
        "url": raw.get("canonical") or raw.get("internal"),
        "title": raw.get("title", ""),
        "content": raw.get("content", ""),
        "markdown_content": raw.get("markdown", ""),
        "source": raw.get("source", ""),
    }


def run_ingestion():
    """Scheduled ingestion pipeline placeholder."""
    # 1. Ouvrir une session DB
    db = SessionLocal()
    try:
        # 2. Liste des collectors à exécuter (ici un seul pour l’exemple)
        ALL_COLLECTORS = [fetch_cryptopanic]

        # 3. Pour chaque collector, récupérer les nouveaux articles
        for collector in ALL_COLLECTORS:
            new_articles = asyncio.run(collector())

            # 4. Traiter chaque article renvoyé
            for article in new_articles:
                # 4.1 Vérifier si l’URL existe déjà en base
                exists = db.query(Article).filter(Article.url == article["url"]).first()
                if exists:
                    continue  # Ignorer si déjà présent

                # 4.2 Normaliser les données (nettoyage, mapping vers Article)
                clean = normalize(article)

                # 4.3 Persister l’article normalisé
                article_obj = Article(**clean)
                db.add(article_obj)
                db.commit()
                db.refresh(article_obj)

                # @todo
                # 4.4 Publier un événement dans Redis pour le module scoring
                # Recommandation : pour consommer le stream Redis plus efficacement et de manière réactive, utilisez XREAD BLOCK ou son équivalent asynchrone (ex. aioredis + xread bloquant). Cela évite le polling intensif et réduit la charge CPU.
                redis_client.xadd("new_articles", {"id": str(article_obj.id)})

        # 5. Log de fin de pipeline
        print("Scheduled pipeline executed")
    finally:
        # 6. Toujours fermer la session DB
        db.close()