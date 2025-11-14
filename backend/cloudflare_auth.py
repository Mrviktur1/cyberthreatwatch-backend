import os
import requests
from fastapi import HTTPException
from dotenv import load_dotenv
from logger import logger

# ======================================================
# 🔧 Load environment variables
# ======================================================
load_dotenv()

CLOUDFLARE_CLIENT_ID = os.getenv("CLOUDFLARE_CLIENT_ID")
CLOUDFLARE_CLIENT_SECRET = os.getenv("CLOUDFLARE_CLIENT_SECRET")
CLOUDFLARE_REDIRECT_URI = os.getenv("CLOUDFLARE_REDIRECT_URI")
CLOUDFLARE_TOKEN_URL = "https://oauth.cloudflareaccess.com/token"

# ======================================================
# 🔐 Function: Exchange Cloudflare code for token
# ======================================================
def get_cloudflare_token(code: str):
    """
    Exchange an OAuth authorization code for a Cloudflare Access token.

    Args:
        code (str): The authorization code received from Cloudflare redirect.

    Returns:
        dict: Token data containing 'access_token', 'id_token', etc.
    """
    if not CLOUDFLARE_CLIENT_ID or not CLOUDFLARE_CLIENT_SECRET or not CLOUDFLARE_REDIRECT_URI:
        logger.error("❌ Cloudflare credentials missing in environment variables.")
        raise HTTPException(status_code=500, detail="Cloudflare configuration missing")

    try:
        payload = {
            "grant_type": "authorization_code",
            "client_id": CLOUDFLARE_CLIENT_ID,
            "client_secret": CLOUDFLARE_CLIENT_SECRET,
            "redirect_uri": CLOUDFLARE_REDIRECT_URI,
            "code": code,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        response = requests.post(CLOUDFLARE_TOKEN_URL, data=payload, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.error(f"❌ Cloudflare token exchange failed: {response.text}")
            raise HTTPException(status_code=400, detail="Invalid Cloudflare authorization code")

        token_data = response.json()

        if "access_token" not in token_data:
            logger.error(f"⚠️ Cloudflare token response missing access_token: {token_data}")
            raise HTTPException(status_code=400, detail="Invalid token data from Cloudflare")

        logger.info("✅ Cloudflare Access Token successfully retrieved.")
        return token_data

    except requests.Timeout:
        logger.exception("⏰ Cloudflare token request timed out.")
        raise HTTPException(status_code=504, detail="Cloudflare request timed out")

    except Exception as e:
        logger.exception(f"💥 Cloudflare token retrieval error: {e}")
        raise HTTPException(status_code=500, detail="Failed to authenticate with Cloudflare")
