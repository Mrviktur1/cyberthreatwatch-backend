# backend/config.py
import os
from dotenv import load_dotenv

# =========================
# Load environment variables
# =========================
load_dotenv()  # Reads .env file

# =========================
# Database
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

# =========================
# JWT / Authentication
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in .env")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

# =========================
# Frontend / CORS
# =========================
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")
if not FRONTEND_ORIGIN:
    raise ValueError("FRONTEND_ORIGIN is not set in .env")

# =========================
# Debug / Logging
# =========================
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
