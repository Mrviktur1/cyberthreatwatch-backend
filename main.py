# ======================================================
# 🚀 CyberThreatWatch Backend (with Cloudflare Access)
# ======================================================

import asyncio
import os
from typing import List, Dict

from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from database import Base, engine, SessionLocal
from routers import auth, admin, status, fleet, siem
from auth import get_current_user, require_roles
from config import FRONTEND_ORIGIN, DEBUG
from logger import logger
from supabase_client import supabase

# ======================================================
# 🔐 Load environment variables
# ======================================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.warning("⚠️ Missing Supabase credentials in environment variables")

# ======================================================
# ⚙️ Initialize FastAPI App
# ======================================================
app = FastAPI(
    title="CyberThreatWatch Backend",
    description="Next-gen SOC platform with AI, role-based control, and fleet management.",
    version="1.1.0",
)

# ======================================================
# 🧩 Cloudflare Zero Trust Middleware (JWT verification)
# ======================================================
from middleware.cloudflare_verify import CloudflareAccessMiddleware
app.add_middleware(CloudflareAccessMiddleware)

# ======================================================
# 🌐 CORS configuration
# ======================================================
allowed_origins = [
    FRONTEND_ORIGIN,
    "https://cyberthreatwatch.app",
]
allow_origin_regex = r"^https:\/\/([\w-]+\.)*cyberthreatwatch\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🧩 Include Routers
# ======================================================
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(status.router)
app.include_router(fleet.router)
app.include_router(siem.router)

# ======================================================
# 🗄️ Initialize Database Tables
# ======================================================
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables initialized")

# ======================================================
# 🧠 In-Memory WebSocket Connections
# ======================================================
active_admin_connections: List[WebSocket] = []
active_fleet_connections: Dict[str, List[WebSocket]] = {}

# ======================================================
# 🔔 Notification Helpers
# ======================================================
async def notify_admins(message: dict):
    """Send real-time notifications to all connected admins."""
    disconnected = []
    for ws in list(active_admin_connections):
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.debug(f"Admin websocket send error: {e}")
            disconnected.append(ws)
    for ws in disconnected:
        try:
            active_admin_connections.remove(ws)
        except ValueError:
            pass


async def notify_fleet(fleet_id: str, message: dict):
    """Send messages to all connected fleet users."""
    if fleet_id not in active_fleet_connections:
        return
    disconnected = []
    for ws in list(active_fleet_connections.get(fleet_id, [])):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        try:
            active_fleet_connections[fleet_id].remove(ws)
        except ValueError:
            pass

# ======================================================
# 🏠 Root Endpoint
# ======================================================
@app.get("/")
async def root():
    return {
        "message": "CyberThreatWatch API is online 🚀",
        "version": "1.1.0",
        "cloudflare_protected": True,
    }

# ======================================================
# ⚡ WebSocket: Real-Time Threat Alerts
# ======================================================
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    try:
        for i in range(3):
            await websocket.send_json({"alert": f"⚠️ Threat alert {i + 1}"})
            await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Alert WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

# ======================================================
# 💬 WebSocket: Fleet Chat
# ======================================================
@app.websocket("/ws/fleet/{fleet_id}/{user_email}")
async def websocket_fleet(websocket: WebSocket, fleet_id: str, user_email: str):
    await websocket.accept()
    if fleet_id not in active_fleet_connections:
        active_fleet_connections[fleet_id] = []
    active_fleet_connections[fleet_id].append(websocket)
    logger.info(f"{user_email} connected to fleet {fleet_id}")

    try:
        await websocket.send_json({"message": f"Connected to fleet {fleet_id} chat"})
        while True:
            data = await websocket.receive_text()
            await notify_fleet(fleet_id, {"user": user_email, "message": data})
    except Exception as e:
        logger.error(f"Fleet chat error ({fleet_id}): {e}")
    finally:
        try:
            if websocket in active_fleet_connections.get(fleet_id, []):
                active_fleet_connections[fleet_id].remove(websocket)
            await websocket.close()
        except Exception:
            pass

# ======================================================
# 🧑💼 WebSocket: Admin Dashboard
# ======================================================
@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket, current_user=Depends(require_roles("admin"))):
    await websocket.accept()
    active_admin_connections.append(websocket)
    try:
        await websocket.send_json({"message": "Admin dashboard connected ✅"})
        while True:
            await asyncio.sleep(10)
    except Exception as e:
        logger.error(f"Admin WebSocket error: {e}")
    finally:
        try:
            if websocket in active_admin_connections:
                active_admin_connections.remove(websocket)
            await websocket.close()
        except Exception:
            pass

# ======================================================
# 🌀 Loader Progress Notifications
# ======================================================
async def notify_loader_progress(step: str, progress: int):
    disconnected = []
    for ws in list(status.active_loader_connections):
        try:
            await ws.send_json({"step": step, "progress": progress})
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        try:
            status.active_loader_connections.remove(ws)
        except ValueError:
            pass
    logger.info(f"Loader update: {step} ({progress}%)")

# ======================================================
# ⏱️ Subscription Enforcement
# ======================================================
def enforce_subscription(current_user=Depends(get_current_user)):
    from models import Subscription, RoleEnum
    db = SessionLocal()
    try:
        if current_user.role in [RoleEnum.BUSINESS, RoleEnum.ENTERPRISE]:
            sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
            if not sub:
                raise HTTPException(status_code=403, detail="Subscription required.")
    finally:
        db.close()
    return current_user

# ======================================================
# 🧭 Health Check
# ======================================================
@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok", "message": "Backend stable and connected ✅"})

# ======================================================
# 🚀 Startup
# ======================================================
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Backend starting up...")
    try:
        _ = supabase.table("siem_logs").select("id").limit(1).execute()
        logger.info("🔗 Supabase client ready")
    except Exception as e:
        logger.warning(f"Supabase ping failed: {e}")

# ======================================================
# 🗺️ Developer Summary
# ======================================================
"""
FEATURE SUMMARY:
- Cloudflare Zero Trust JWT validation middleware
- Supabase for fleet, users, and security data
- WebSockets for real-time fleet and admin comms
- Role-based auth and subscription enforcement
- Deployed via Render with environment-based config
"""
