from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import httpx
from datetime import datetime
from typing import List

from ...shared.db import get_db, Draft, Article
from shared.models import GenerateDraftRequest, DraftResponse, ScheduleRequest
import os

# External service URLs
WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://writer-agent:8000")

router = APIRouter(prefix="/publishing", tags=["publishing"])

@router.post("/generate-draft", response_model=DraftResponse)
async def generate_draft(request: GenerateDraftRequest, db: Session = Depends(get_db)):
    """
    Generate a post draft using Writer-Agent
    """
    # Get article
    article = db.query(Article).filter(Article.id == request.article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")
    
    try:
        # Call Writer-Agent to generate content
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for generation
            response = await client.post(
                f"{WRITER_AGENT_URL}/generate",
                json={
                    "title": article.title,
                    "content": article.markdown_content or article.content,
                    "style": request.style
                }
            )
            
            if response.status_code != 200:
                # Fallback to template-based generation
                content = _generate_fallback_content(article, request.style)
            else:
                result = response.json()
                content = result.get("content", "Content generation failed.")
        
        # Create draft
        draft = Draft(
            article_id=article.id,
            content=content,
            style=request.style,
            timestamp=datetime.utcnow()
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        return DraftResponse(
            id=draft.id,
            article_id=article.id,
            content=draft.content,
            style=draft.style,
            timestamp=draft.timestamp
        )
    
    except Exception as e:
        # Fallback in case of exception
        content = _generate_fallback_content(article, request.style)
        
        # Create draft with fallback content
        draft = Draft(
            article_id=article.id,
            content=content,
            style=request.style,
            timestamp=datetime.utcnow()
        )
        db.add(draft)
        db.commit()
        db.refresh(draft)
        
        return DraftResponse(
            id=draft.id,
            article_id=article.id,
            content=draft.content,
            style=draft.style,
            timestamp=draft.timestamp
        )

@router.get("/drafts", response_model=List[DraftResponse])
async def get_drafts(db: Session = Depends(get_db)):
    """
    Get all unpublished drafts
    """
    drafts = db.query(Draft).filter(Draft.published == False).all()
    
    return [
        DraftResponse(
            id=draft.id,
            article_id=draft.article_id,
            content=draft.content,
            style=draft.style,
            timestamp=draft.timestamp
        )
        for draft in drafts
    ]

@router.post("/schedule")
async def schedule_post(request: ScheduleRequest, db: Session = Depends(get_db)):
    """
    Schedule a draft for publication
    """
    draft = db.query(Draft).filter(Draft.id == request.draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    draft.scheduled_for = request.publish_time
    db.commit()
    
    return {"status": "success", "message": f"Draft scheduled for {request.publish_time}"}

@router.post("/publish/{draft_id}")
async def publish_post(draft_id: int, db: Session = Depends(get_db)):
    """
    Publish a draft immediately
    """
    draft = db.query(Draft).filter(Draft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Logic to publish to social media would go here
    # For now, just mark as published
    draft.published = True
    db.commit()
    
    return {"status": "success", "message": "Draft published"}

# Fallback content generation helper
def _generate_fallback_content(article, style):
    title = article.title
    source = article.source
    
    if style == "serious":
        return f"Breaking News: {title} - More details available from {source}. This appears to be an important development."
    elif style == "sarcastic":
        return f"Oh great, another wonderful piece of news: '{title}' - straight from the ever-reliable {source}. Just what we needed today!"
    elif style == "troll":
        return f"YOU WON'T BELIEVE WHAT JUST HAPPENED!! {title.upper()}!!! This changes EVERYTHING! {source} strikes again!!!"
    else:
        return f"News Update: {title} - Source: {source}"
