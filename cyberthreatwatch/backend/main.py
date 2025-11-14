# ======================================================
# 🚀 CyberThreatWatch Backend (Async Version)
# ======================================================

import asyncio
import os
from typing import List, Dict

from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession

from database import Base, engine, get_db
from routers import auth, admin, status, fleet, siem
from auth import get_current_user, require_roles
from config import FRONTEND_ORIGIN
from logger import logger
from supabase_client import supabase
from models import Subscription, RoleEnum

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
allowed_origins = [FRONTEND_ORIGIN, "https://cyberthreatwatch.app"]
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
# 🗄️ Initialize Database Tables (async)
# ======================================================
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables initialized")

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Backend starting up...")
    await init_db()
    try:
        _ = supabase.table("siem_logs").select("id").limit(1).execute()
        logger.info("🔗 Supabase client ready")
    except Exception as e:
        logger.warning(f"Supabase ping failed: {e}")

# ======================================================
# 🧠 In-Memory WebSocket Connections
# ======================================================
active_admin_connections: List[WebSocket] = []
active_fleet_connections: Dict[str, List[WebSocket]] = {}

# ======================================================
# 🔔 Notification Helpers
# ======================================================
async def notify_admins(message: dict):
    disconnected = []
    for ws in list(active_admin_connections):
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.debug(f"Admin websocket send error: {e}")
            disconnected.append(ws)
    for ws in disconnected:
        active_admin_connections[:] = [w for w in active_admin_connections if w not in disconnected]

async def notify_fleet(fleet_id: str, message: dict):
    if fleet_id not in active_fleet_connections:
        return
    disconnected = []
    for ws in list(active_fleet_connections.get(fleet_id, [])):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    active_fleet_connections[fleet_id] = [w for w in active_fleet_connections[fleet_id] if w not in disconnected]

# ======================================================
# 🏠 Root Endpoint
# ======================================================
@app.get("/")
async def root():
    return {"message": "CyberThreatWatch API is online 🚀", "version": "1.1.0", "cloudflare_protected": True}

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
        await websocket.close()

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
        if websocket in active_fleet_connections.get(fleet_id, []):
            active_fleet_connections[fleet_id].remove(websocket)
        await websocket.close()

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
        if websocket in active_admin_connections:
            active_admin_connections.remove(websocket)
        await websocket.close()

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
    status.active_loader_connections[:] = [w for w in status.active_loader_connections if w not in disconnected]
    logger.info(f"Loader update: {step} ({progress}%)")

# ======================================================
# ⏱️ Subscription Enforcement (async)
# ======================================================
async def enforce_subscription(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role in [RoleEnum.BUSINESS, RoleEnum.ENTERPRISE]:
        result = await db.execute(
            Subscription.__table__.select().where(Subscription.user_id == current_user.id)
        )
        sub = result.fetchone()
        if not sub:
            raise HTTPException(status_code=403, detail="Subscription required.")
    return current_user

# ======================================================
# 🧭 Health Check
# ======================================================
@app.get("/health")
async def health_check():
    return JSONResponse({"status": "ok", "message": "Backend stable and connected ✅"})
