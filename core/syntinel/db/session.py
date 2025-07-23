"""
Database connection configuration.
This module handles database connection, session creation, and utility functions.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database connection configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:pswd@postgres:5432/syntineldb")

# Update port if using the updated docker-compose configuration
if "postgres:5432" in DATABASE_URL and os.environ.get("DB_PORT_UPDATE") == "true":
    DATABASE_URL = DATABASE_URL.replace("postgres:5432", "postgres:5400")

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all models
Base = declarative_base()

def create_tables():
    """Create all database tables if they don't exist."""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency for getting a database session.
    
    Yields:
        Session: A SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
