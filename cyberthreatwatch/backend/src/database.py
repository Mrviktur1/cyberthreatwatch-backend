import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# === Load environment variables ===
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", 5432)
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

# === Construct PostgreSQL connection string ===
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# === Create engine and session ===
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# === Dependency to get DB session for FastAPI routes ===
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
