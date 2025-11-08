# backend/database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# =========================
# Load environment variables from .env
# =========================
load_dotenv()  # Reads .env file automatically

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost/cyberwatch"  # fallback
)

# =========================
# SQLAlchemy Engine & Session
# =========================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True  # Avoid stale connections
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# =========================
# Base class for models
# =========================
Base = declarative_base()

# =========================
# Dependency for FastAPI routes
# =========================
def get_db():
    """
    Provides a SQLAlchemy session to FastAPI endpoints.
    Usage: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
