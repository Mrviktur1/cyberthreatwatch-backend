# ==========================================================
# 🚀 FLEET MANAGEMENT ROUTER
# ==========================================================
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.database import get_db
from supabase_client import supabase
from auth import get_password_hash, require_roles
from models import User, RoleEnum
from logger import logger

router = APIRouter(prefix="/fleet", tags=["Fleet Management"])

# ==========================================================
# Pydantic Models
# ==========================================================
class FleetUserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    workstation: str
    role: RoleEnum = RoleEnum.STUDENT


class FleetUserUpdate(BaseModel):
    full_name: Optional[str] = None
    workstation: Optional[str] = None
    role: Optional[RoleEnum] = None


class FleetUserOut(BaseModel):
    id: Optional[int]
    email: EmailStr
    full_name: str
    workstation: str
    role: RoleEnum


# ==========================================================
# List all users in a fleet
# ==========================================================
@router.get("/{fleet_id}/users", response_model=List[FleetUserOut])
def list_fleet_users(
    fleet_id: int,
    current_user: User = Depends(require_roles("admin", "business", "enterprise"))
):
    try:
        response = supabase.table("fleet_users").select("*").eq("fleet_id", fleet_id).execute()
        if hasattr(response, "error") and response.error:
            logger.error(f"Supabase error while listing fleet users: {response.error.message}")
            raise HTTPException(status_code=500, detail=f"Supabase error: {response.error.message}")
        logger.info(f"✅ Fleet {fleet_id} users listed by {current_user.email}")
        return response.data or []
    except Exception as e:
        logger.exception(f"💥 Error listing fleet users for fleet {fleet_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==========================================================
# Add user to fleet
# ==========================================================
@router.post("/{fleet_id}/users", response_model=FleetUserOut)
def add_fleet_user(
    fleet_id: int,
    user_data: FleetUserCreate,
    current_user: User = Depends(require_roles("admin", "business", "enterprise"))
):
    try:
        if current_user.role == RoleEnum.BUSINESS:
            response = supabase.table("fleet_users").select("*").eq("fleet_id", fleet_id).execute()
            if len(response.data or []) >= 5:
                raise HTTPException(status_code=403, detail="Business fleet limit reached (max 5 users)")

        existing = supabase.table("fleet_users").select("*").eq("email", user_data.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="User email already exists")

        hashed_pw = get_password_hash(user_data.password)
        insert_response = supabase.table("fleet_users").insert({
            "fleet_id": fleet_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "password": hashed_pw,
            "workstation": user_data.workstation,
            "role": user_data.role.value
        }).execute()

        new_user = insert_response.data[0] if insert_response.data else None
        logger.info(f"✅ Fleet user {user_data.email} added to fleet {fleet_id}")

        return FleetUserOut(
            id=new_user.get("id"),
            email=user_data.email,
            full_name=user_data.full_name,
            workstation=user_data.workstation,
            role=user_data.role
        )

    except Exception as e:
        logger.exception(f"💥 Error adding user {user_data.email}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ==========================================================
# Update, Delete, Summary functions (same as before)
# ==========================================================
# ... (keep your existing update_fleet_user, remove_fleet_user, get_fleet_summary unchanged)
# ==========================================================


# ==========================================================
# 🧠 NEW SECTION: Fetch from Local DB (Render PostgreSQL)
# ==========================================================
@router.get("/all")
def get_all_fleets(db: Session = Depends(get_db)):
    """
    Retrieve all fleets directly from PostgreSQL (Render-hosted DB).
    This complements Supabase and allows hybrid sync.
    """
    try:
        fleets = db.execute("SELECT * FROM fleet").fetchall()
        return {"fleets": [dict(row._mapping) for row in fleets]}
    except Exception as e:
        logger.exception(f"💥 Error fetching fleets from DB: {e}")
        raise HTTPException(status_code=500, detail="Database fetch failed")

