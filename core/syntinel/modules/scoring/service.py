from datetime import datetime
from sqlalchemy.orm import Session
from shared.db import Article
from typing import List, Dict

def score_articles_batch(db: Session):
    """
    Score unprocessed articles in batch
    """
    # Get unprocessed articles
    articles = db.query(Article).filter(Article.processed == False).all()
    
    for article in articles:
        # Calculate individual scores
        panic_score = calculate_panic_score(article.content)
        recency_score = calculate_recency_score(article.timestamp)
        source_weight = calculate_source_weight(article.source)
        
        # Calculate total score
        total_score = calculate_total_score(panic_score, recency_score, source_weight)
        
        # Update article
        article.panic_score = panic_score
        article.recency_score = recency_score
        article.source_weight = source_weight
        article.total_score = total_score
        article.processed = True
    
    # Commit changes
    db.commit()

def calculate_panic_score(content: str) -> float:
    """
    Calculate panic score based on presence of "panic words"
    """
    panic_words = ["emergency", "crisis", "urgent", "breaking", "alert", "warning", 
                  "disaster", "danger", "threat", "critical", "severe", "catastrophic"]
    
    content_lower = content.lower()
    panic_count = sum(content_lower.count(word) for word in panic_words)
    article_length = len(content_lower.split())
    
    # Normalize score
    if article_length > 0:
        panic_score = min(1.0, panic_count / (article_length * 0.01))  # Cap at 1.0
    else:
        panic_score = 0
    
    return panic_score

def calculate_recency_score(timestamp: datetime) -> float:
    """
    Calculate recency score based on article age
    More recent articles get higher scores
    """
    now = datetime.utcnow()
    age_hours = (now - timestamp).total_seconds() / 3600
    recency_score = 1.0 / (1.0 + 0.1 * age_hours)  # Simple decay function
    return recency_score

def calculate_source_weight(source: str) -> float:
    """
    Calculate source weight based on source reputation
    """
    source_weights = {
        "trusted": 1.5,
        "verified": 1.3,
        "standard": 1.0,
        "questionable": 0.7,
        "unreliable": 0.5
    }
    
    return source_weights.get(source, 1.0)

def calculate_total_score(panic_score: float, recency_score: float, source_weight: float) -> float:
    """
    Calculate total article score based on individual components
    """
    # Weights for each component
    panic_weight = 0.5
    recency_weight = 0.3
    source_weight_factor = 0.2
    
    # Calculate total weighted score
    total_score = (panic_score * panic_weight) + \
                 (recency_score * recency_weight) + \
                 (source_weight * source_weight_factor)
    
    return total_score
