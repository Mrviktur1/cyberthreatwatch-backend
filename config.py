# backend/config.py
import os
from dotenv import load_dotenv

# =========================
# Load environment variables from .env
# =========================
load_dotenv()  # Automatically reads .env in project root

# =========================
# Database Configuration
# =========================
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env. Example: postgresql://user:password@host:port/dbname")

# =========================
# JWT / Authentication
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY is not set in .env. Generate securely using: openssl rand -hex 32")

ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))  # Default: 24 hours

# =========================
# Frontend / CORS
# =========================
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN")
if not FRONTEND_ORIGIN:
    raise ValueError("FRONTEND_ORIGIN is not set in .env. Example: https://cyberthreatwatch.app")

# =========================
# Optional: Debug / Logging
# =========================
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info").upper()

# =========================
# Optional: Additional Security / Performance
# =========================
# You can add other config variables here for:
# - SSL verification
# - Redis URL
# - Celery broker URL
# - Rate limiting
# - Sentry / error logging DSNx
