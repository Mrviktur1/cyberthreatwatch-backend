# ======================================================
# backend/database.py
# Async Database Setup for CyberThreatWatch
# ======================================================

import os
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# ======================================================
# 🔐 Load environment variables
# ======================================================
load_dotenv()  # Automatically loads .env file

# ======================================================
# 🗄️ Database credentials
# ======================================================
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Chukwulotanna25.")  # Supports special characters
DB_HOST = os.getenv("DB_HOST", "db.bkspfwvntblonkohssdr.supabase.co")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")

# URL-encode the password to safely handle special characters
ENCODED_PASSWORD = urllib.parse.quote_plus(DB_PASSWORD)

# ======================================================
# Construct async DATABASE_URL
# ======================================================
DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{ENCODED_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ======================================================
# Async SQLAlchemy Engine & Session
# ======================================================
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Optional: logs all SQL queries for debugging
    future=True
)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ======================================================
# Base class for models
# ======================================================
Base = declarative_base()

# ======================================================
# Dependency for FastAPI routes
# Usage:
# async def some_route(db: AsyncSession = Depends(get_db))
# ======================================================
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
