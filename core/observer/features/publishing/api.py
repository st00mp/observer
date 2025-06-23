from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from shared.db import get_db, Draft, Article
from shared.models import GenerateDraftRequest, DraftResponse, ScheduleRequest
from core.observer.features.publishing.service import generate_content, publish_draft_to_platforms

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
    
    # Generate content using the service
    content = await generate_content(article, request.style)
    
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
    
    # Use the service to publish the draft
    result = await publish_draft_to_platforms(draft)
    
    # Mark as published
    draft.published = True
    db.commit()
    
    return {"status": "success", "message": "Draft published", "platforms": result}
