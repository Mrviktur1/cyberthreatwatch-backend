# backend/routers/admin.py
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from sqlalchemy.orm import Session
from database import SessionLocal, get_db
from models import User, RoleEnum, WorkLog, SensitiveAction, Subscription
from passlib.hash import bcrypt
from datetime import datetime
from typing import List
from auth import get_current_user, require_roles
import asyncio

router = APIRouter(prefix="/admin", tags=["Admin"])

# =====================================
# 🔧 Dependency
# =====================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================
# 🌐 WebSocket Admin Connections
# =====================================
active_admin_connections: List[WebSocket] = []

async def notify_admins(message: dict):
    """Notify all active admin dashboard connections in real time."""
    disconnected = []
    for ws in active_admin_connections:
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        active_admin_connections.remove(ws)

# =====================================
# 👥 User Management
# =====================================
@router.post("/user/create")
def create_user(
    email: str,
    full_name: str,
    password: str,
    role: RoleEnum = RoleEnum.STUDENT,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    hashed_password = bcrypt.hash(password)
    user = User(email=email, full_name=full_name, password=hashed_password, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)

    asyncio.create_task(notify_admins({
        "type": "new_user",
        "email": user.email,
        "role": user.role.value,
        "created_at": str(user.created_at)
    }))

    return {"message": "User created successfully", "user_id": user.id}

@router.put("/user/{user_id}/role")
def update_user_role(
    user_id: int,
    role: RoleEnum,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = role
    db.commit()
    asyncio.create_task(notify_admins({
        "type": "role_update",
        "user_id": user.id,
        "new_role": role.value
    }))
    return {"message": f"User role updated to {role.value}"}

@router.put("/user/{user_id}/status")
def set_user_status(
    user_id: int,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = is_active
    db.commit()
    asyncio.create_task(notify_admins({
        "type": "status_update",
        "user_id": user.id,
        "is_active": is_active
    }))
    return {"message": f"User status set to {'active' if is_active else 'inactive'}"}

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "active": u.is_active,
            "created_at": u.created_at
        }
        for u in users
    ]

# =====================================
# 🕒 Work Logs (Clock-In/Out)
# =====================================
@router.get("/worklogs")
def view_worklogs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    logs = db.query(WorkLog).all()
    return [
        {
            "user_id": l.user_id,
            "clock_in": l.clock_in,
            "clock_out": l.clock_out,
            "summary": l.summary
        }
        for l in logs
    ]

@router.post("/worklogs/clock-in")
def clock_in(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Limit for students
    if current_user.role == RoleEnum.STUDENT:
        today = datetime.utcnow().date()
        logs = db.query(WorkLog).filter(
            WorkLog.user_id == current_user.id,
            WorkLog.clock_in >= datetime(today.year, today.month, today.day)
        ).all()
        total_seconds = sum(
            ((l.clock_out or datetime.utcnow()) - l.clock_in).total_seconds()
            for l in logs
        )
        if total_seconds >= 4 * 3600:
            raise HTTPException(status_code=403, detail="Daily limit exceeded (4 hours)")

    log = WorkLog(user_id=current_user.id, clock_in=datetime.utcnow())
    db.add(log)
    db.commit()
    db.refresh(log)

    asyncio.create_task(notify_admins({
        "type": "clock_in",
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "clock_in": str(log.clock_in)
    }))

    return {"message": "Clock-in recorded", "clock_in": log.clock_in}

@router.post("/worklogs/clock-out")
def clock_out(
    summary: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    log = db.query(WorkLog).filter(
        WorkLog.user_id == current_user.id,
        WorkLog.clock_out.is_(None)
    ).order_by(WorkLog.clock_in.desc()).first()

    if not log:
        raise HTTPException(status_code=400, detail="No active clock-in found")

    log.clock_out = datetime.utcnow()
    log.summary = summary
    db.commit()
    db.refresh(log)

    asyncio.create_task(notify_admins({
        "type": "clock_out",
        "user_id": current_user.id,
        "full_name": current_user.full_name,
        "clock_out": str(log.clock_out),
        "summary": log.summary
    }))

    return {
        "message": "Clock-out recorded",
        "clock_in": log.clock_in,
        "clock_out": log.clock_out,
        "summary": log.summary
    }

# =====================================
# 🔐 Sensitive Actions
# =====================================
@router.get("/sensitive")
def view_sensitive_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    actions = db.query(SensitiveAction).order_by(SensitiveAction.timestamp.desc()).all()
    return [
        {
            "user_id": a.user_id,
            "action_type": a.action_type,
            "file_name": a.file_name,
            "file_path": a.file_path,
            "timestamp": a.timestamp,
            "alert_sent": a.alert_sent
        }
        for a in actions
    ]

# =====================================
# 💼 Subscriptions
# =====================================
@router.get("/subscriptions")
def view_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin"))
):
    subs = db.query(Subscription).all()
    return [
        {
            "user_id": s.user_id,
            "plan_type": s.plan_type,
            "start_date": s.start_date,
            "end_date": s.end_date
        }
        for s in subs
    ]

# =====================================
# 📡 WebSocket Admin Dashboard
# =====================================
@router.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    await websocket.accept()
    active_admin_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(10)
    except Exception:
        pass
    finally:
        if websocket in active_admin_connections:
            active_admin_connections.remove(websocket)

# =====================================
# 🛰️ Fleet Management (Placeholder)
# =====================================
@router.get("/fleets")
def list_fleets(current_user: User = Depends(require_roles("admin"))):
    return {"message": "Fleet management placeholder"}

@router.post("/fleets/assign")
def assign_user_to_fleet(
    user_id: int,
    fleet_name: str,
    current_user: User = Depends(require_roles("admin"))
):
    return {"message": f"User {user_id} assigned to fleet '{fleet_name}' (placeholder)"}

# =====================================
# 📊 Threat Reports / Charts
# =====================================
@router.get("/charts/threats")
def threat_charts(current_user: User = Depends(require_roles("admin"))):
    return {
        "pie_chart": {"malware": 10, "phishing": 5, "ransomware": 2},
        "bar_chart": {"malware": 10, "phishing": 5, "ransomware": 2}
    }

@router.post("/reports/generate")
def generate_report(user_id: int, current_user: User = Depends(require_roles("admin"))):
    return {"message": f"PDF report for user {user_id} generated (placeholder)"}. 
