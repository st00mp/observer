from fastapi import FastAPI
import redis
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import routers
from .features.crawling.api import router as crawling_router
from .features.scoring.api import router as scoring_router
from .features.publishing.api import router as publishing_router

# Import database setup
from .shared.db import create_tables

# Redis setup
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# External service URLs
CRAWL4AI_URL = os.getenv("CRAWL4AI_URL", "http://crawl4ai:8000")
WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://writer-agent:8000")

# Create FastAPI app
app = FastAPI(title="Observer Core")

# Include routers
app.include_router(crawling_router)
app.include_router(scoring_router)
app.include_router(publishing_router)

# Create tables on startup
create_tables()

@app.get("/")
def read_root():
    return {"status": "Observer Core is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
