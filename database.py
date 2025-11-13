# backend/database.py
import os
import urllib.parse   # <-- Add this import here
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# =========================
# Load environment variables from .env
# =========================
load_dotenv()  # Reads .env file automatically

# =========================
# Database credentials
# =========================
user = os.getenv("DB_USER", "postgres")
password = os.getenv("DB_PASSWORD", "Chukwulotanna25.")  # can have special chars
host = os.getenv("DB_HOST", "db.bkspfwvntblonkohssdr.supabase.co")
port = os.getenv("DB_PORT", "5432")
database = os.getenv("DB_NAME", "postgres")

# URL-encode the password to safely handle special characters
encoded_password = urllib.parse.quote_plus(password)

# Construct the DATABASE_URL
DATABASE_URL = f"postgresql://{user}:{encoded_password}@{host}:{port}/{database}"

# =========================
# SQLAlchemy Engine & Session
# =========================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args={}  # for Postgres no special args needed
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
