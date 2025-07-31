"""
Database connection configuration.
This module handles database connection, session creation, and utility functions.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Database connection configuration
# Détection de l'environnement : si DOCKER_ENV est défini, on utilise postgres comme hôte, sinon localhost
IS_DOCKER = os.environ.get("DOCKER_ENV", "").lower() == "true"
DEFAULT_HOST = "postgres" if IS_DOCKER else "localhost"
DEFAULT_PORT = "5432" if IS_DOCKER else "5400"

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"postgresql://admin:pswd@{DEFAULT_HOST}:{DEFAULT_PORT}/syntineldb"
)

# Affiche l'URL de connexion pour le débogage
print(f"Connexion à la base de données : {DATABASE_URL}")

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
