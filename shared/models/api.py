from pydantic import BaseModel, HttpUrl
from datetime import datetime

class CrawlRequest(BaseModel):
    url: HttpUrl
    source: str
    force_refresh: bool = False

class ScoredArticle(BaseModel):
    id: int
    url: str
    title: str
    source: str
    panic_score: float
    recency_score: float
    source_weight: float
    total_score: float

class GenerateDraftRequest(BaseModel):
    article_id: int
    style: str = "serious"  # serious, sarcastic, troll

class DraftResponse(BaseModel):
    id: int
    article_id: int
    content: str
    style: str
    timestamp: datetime

class ScheduleRequest(BaseModel):
    draft_id: int
    publish_time: datetime
