# ======================================================
# 🔗 Supabase Client Configuration
# ======================================================
import os
from supabase import create_client, Client
from dotenv import load_dotenv
from logger import logger

# ======================================================
# 🧠 Load environment variables
# ======================================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# ======================================================
# ⚙️ Initialize Supabase Client
# ======================================================
def init_supabase() -> Client:
    """
    Initialize Supabase client with service role key for backend operations.
    - Uses service role key (never expose this to frontend)
    - Validates environment configuration
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("❌ Supabase credentials missing. Please verify .env configuration.")
        raise ValueError("Supabase URL or Service Role Key not set")

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("✅ Supabase client initialized successfully")
        return supabase
    except Exception as e:
        logger.exception(f"❌ Failed to initialize Supabase client: {e}")
        raise RuntimeError("Failed to connect to Supabase")

# ======================================================
# 🧩 Global Supabase Instance
# ======================================================
try:
    supabase: Client = init_supabase()
except Exception as e:
    logger.critical(f"🚨 Supabase initialization failed: {e}")
    raise
