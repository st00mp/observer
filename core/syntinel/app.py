from fastapi import FastAPI
import os

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import routers
from core.syntinel.modules.crawling.api import router as crawling_router
from core.syntinel.modules.scoring.api import router as scoring_router
from core.syntinel.modules.publishing.api import router as publishing_router

# Import database setup
from shared.db import create_tables

# Create FastAPI app
app = FastAPI(title="Syntinel Core")

# Register routers
app.include_router(crawling_router)
app.include_router(scoring_router)
app.include_router(publishing_router)

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    create_tables()

# Root endpoint
@app.get("/")
def read_root():
    return {"status": "online", "service": "Syntinel Core"}
