import asyncio
from typing import List

from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, SessionLocal
from routers import auth, admin, status  # ✅ Added status router (for loader WebSocket)
from auth import get_current_user, require_roles
from config import FRONTEND_ORIGIN  # Loaded from .env
from logger import logger  # ✅ Integrated backend logger

# ======================================================
# ⚙️ Initialize FastAPI App
# ======================================================
app = FastAPI(
    title="CyberThreatWatch Backend",
    description="Next-gen SOC platform with AI, role-based control, and real-time visibility",
    version="1.0.0",
)

# ======================================================
# 🌐 Enable CORS for Frontend Access
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🧩 Include Routers
# ======================================================
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(status.router)  # ✅ for /ws/loader connections

# ======================================================
# 🗄️ Initialize Database Tables
# ======================================================
Base.metadata.create_all(bind=engine)

# ======================================================
# 🧠 In-Memory WebSocket Connections
# ======================================================
active_admin_connections: List[WebSocket] = []


async def notify_admins(message: dict):
    """Send real-time notifications to connected admins."""
    disconnected = []
    for ws in active_admin_connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        if ws in active_admin_connections:
            active_admin_connections.remove(ws)


# ======================================================
# 🏠 Root Endpoint
# ======================================================
@app.get("/")
async def root():
    logger.info("Root endpoint accessed.")
    return {"message": "CyberThreatWatch API is online now 🚀"}


# ======================================================
# ⚡ WebSocket: Real-Time Threat Alerts
# ======================================================
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await websocket.accept()
    logger.info("New WebSocket connection established for alerts.")
    try:
        for i in range(5):  # Example: Simulated alert stream
            await websocket.send_json({"alert": f"Threat alert {i + 1}"})
            await asyncio.sleep(2)
    except Exception as e:
        logger.error(f"Alert WebSocket error: {e}")
    finally:
        await websocket.close()
        logger.info("Alert WebSocket closed.")


# ======================================================
# 💬 WebSocket: Admin ↔ User Chat
# ======================================================
@app.websocket("/ws/chat/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: str):
    await websocket.accept()
    logger.info(f"Chat WebSocket connected for room: {room_id}")
    try:
        await websocket.send_json({"message": f"Connected to chat room {room_id}"})
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"echo": data})
    except Exception as e:
        logger.error(f"Chat WebSocket error in room {room_id}: {e}")
    finally:
        await websocket.close()
        logger.info(f"Chat WebSocket closed for room {room_id}")


# ======================================================
# 🧑‍💼 WebSocket: Admin Dashboard Channel
# ======================================================
@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket, current_user=Depends(require_roles("admin"))):
    await websocket.accept()
    active_admin_connections.append(websocket)
    logger.info(f"Admin {current_user.email} connected to dashboard WebSocket.")

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
        logger.info("Admin dashboard WebSocket closed.")


# ======================================================
# 🌀 Loader Progress Notifications
# ======================================================
async def notify_loader_progress(step: str, progress: int):
    """
    Send loader progress updates to all connected loader clients.
    Example: asyncio.create_task(notify_loader_progress("Loading logs...", 40))
    """
    disconnected = []
    for ws in status.active_loader_connections:
        try:
            await ws.send_json({"step": step, "progress": progress})
        except Exception:
            disconnected.append(ws)

    for ws in disconnected:
        if ws in status.active_loader_connections:
            status.active_loader_connections.remove(ws)

    logger.info(f"Loader progress update: {step} ({progress}%)")


# ======================================================
# ⏱️ Subscription & Trial Enforcement Hook
# ======================================================
def enforce_subscription(current_user=Depends(get_current_user)):
    """
    Restrict access based on subscription and trial limits.
    - Students: free 4 hours daily
    - Business / Enterprise: require active subscription
    """
    from models import Subscription, RoleEnum

    if current_user.role in [RoleEnum.BUSINESS, RoleEnum.ENTERPRISE]:
        db = SessionLocal()
        try:
            sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
            if not sub:
                raise HTTPException(
                    status_code=403,
                    detail="Subscription required. Start a trial or activate plan.",
                )
        finally:
            db.close()
    return current_user


# ======================================================
# 🧭 Health Check Endpoint
# ======================================================
@app.get("/health")
async def health_check():
    logger.info("Health check performed.")
    return {"status": "ok", "message": "Backend stable and connected ✅"}


# ======================================================
# 🚀 Feature Roadmap (Reference)
# ======================================================
"""
Roles:
    - Student: Free 4 hrs/day
    - Business: Subscription-based (team limited)
    - Enterprise: Subscription-based (unlimited teams, SOC dashboards)

Features:
    - Clock-in/out tracking
    - Sensitive action monitoring (screenshots, downloads)
    - Admin audit dashboard (with notifications)
    - Role-Based Access Control (RBAC)
    - Internal Chat System via WebSocket
    - AI Assistant for instant threat Q&A
    - Fleet management for orgs
    - PDF Report Generation (charts, graphs, SOC analytics)
    - Subscription + Billing management
    - Auto daily backups (handled server-side)
    - 5D Logo-based fullscreen loading animation (frontend)
    - Real-time SOC alert streaming via /ws/alerts
    - Cloud Auto-Sync (Render + Supabase)
"""
