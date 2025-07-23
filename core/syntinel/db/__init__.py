"""
Database module for Syntinel.
This package centralizes all database-related functionality.
"""

# Re-export important components for convenience
from .session import engine, SessionLocal, get_db, create_tables
from .models.article import Article
from .models.draft import Draft
from .session import DATABASE_URL, Base
