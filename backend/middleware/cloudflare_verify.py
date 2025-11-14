# backend/middleware/cloudflare_verify.py
import os
import time
import jwt
import requests
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from logger import logger

# ======================================================
# 🌐 Cloudflare Access Settings
# ======================================================
CLOUDFLARE_AUD = os.getenv("CLOUDFLARE_AUD")
CLOUDFLARE_TEAM = os.getenv("CLOUDFLARE_TEAM")  # e.g. "cyberthreatwatch"
CLOUDFLARE_JWKS_URL = f"https://{CLOUDFLARE_TEAM}.cloudflareaccess.com/cdn-cgi/access/certs"

# JWKS cache to avoid repeated requests
_jwks_cache = {"keys": None, "fetched_at": 0}
_JWKS_TTL = 3600  # seconds (1 hour)


class CloudflareAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ======================================================
        # 🧩 Skip Public Endpoints
        # ======================================================
        public_paths = ["/", "/health", "/docs", "/openapi.json"]
        if any(request.url.path.startswith(p) for p in public_paths):
            return await call_next(request)

        # ======================================================
        # 🔐 Extract Cloudflare JWT
        # ======================================================
        token = request.headers.get("Cf-Access-Jwt-Assertion")
        if not token:
            raise HTTPException(status_code=401, detail="Missing Cloudflare Access token")

        # ======================================================
        # 🔍 Fetch or Reuse JWKS (Public Keys)
        # ======================================================
        global _jwks_cache
        now = time.time()
        if not _jwks_cache["keys"] or now - _jwks_cache["fetched_at"] > _JWKS_TTL:
            try:
                res = requests.get(CLOUDFLARE_JWKS_URL, timeout=5)
                res.raise_for_status()
                _jwks_cache["keys"] = res.json()["keys"]
                _jwks_cache["fetched_at"] = now
                logger.info("🔑 Cloudflare JWKS cache refreshed")
            except Exception as e:
                logger.error(f"Failed to fetch Cloudflare JWKS: {e}")
                raise HTTPException(status_code=500, detail="Cloudflare JWKS fetch failed")

        try:
            unverified_header = jwt.get_unverified_header(token)
            key = next(
                (k for k in _jwks_cache["keys"] if k["kid"] == unverified_header["kid"]),
                None,
            )
            if not key:
                raise Exception("Matching key not found in Cloudflare JWKS")

            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=CLOUDFLARE_AUD,
            )

            # Attach Cloudflare user info
            request.state.user_email = payload.get("email")
            request.state.cloudflare_user_id = payload.get("sub")

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Cloudflare token expired")
        except jwt.InvalidAudienceError:
            raise HTTPException(status_code=401, detail="Invalid Cloudflare AUD claim")
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Cloudflare verification failed: {e}")

        # ======================================================
        # ✅ Continue Request
        # ======================================================
        return await call_next(request)
