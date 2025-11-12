# backend/routers/fleet.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from supabase_client import supabase

from auth import get_password_hash, require_roles
from models import User, RoleEnum
from logger import logger

router = APIRouter(prefix="/fleet", tags=["Fleet Management"])

# ==========================================================
# Pydantic Models
# ==========================================================
class FleetCreate(BaseModel):
    name: str
    plan: str = "business"  # 'student', 'business', 'enterprise'

class FleetOut(BaseModel):
    id: Optional[int]
    name: str
    plan: str
    admin_email: str
    created_at: Optional[str]

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
# Fleet Management Routes
# ==========================================================
@router.post("/", response_model=FleetOut)
def create_fleet(
    fleet_data: FleetCreate,
    current_user: User = Depends(require_roles("admin", "business", "enterprise"))
):
    """
    Create a new fleet and assign current user as admin.
    """
    try:
        insert_resp = supabase.table("fleets").insert({
            "name": fleet_data.name,
            "plan": fleet_data.plan,
            "admin_email": current_user.email
        }).execute()

        if hasattr(insert_resp, "error") and insert_resp.error:
            logger.error(f"❌ Supabase fleet insert error: {insert_resp.error.message}")
            raise HTTPException(status_code=500, detail=f"Supabase error: {insert_resp.error.message}")

        new_fleet = insert_resp.data[0] if insert_resp.data else None
        logger.info(f"✅ Fleet '{fleet_data.name}' created by {current_user.email}")

        return FleetOut(
            id=new_fleet.get("id"),
            name=new_fleet.get("name"),
            plan=new_fleet.get("plan"),
            admin_email=new_fleet.get("admin_email"),
            created_at=new_fleet.get("created_at")
        )

    except Exception as e:
        logger.exception(f"💥 Error creating fleet: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/", response_model=List[FleetOut])
def list_fleets(current_user: User = Depends(require_roles("admin", "business", "enterprise"))):
    """
    List all fleets where current user is admin.
    """
    try:
        resp = supabase.table("fleets").select("*").eq("admin_email", current_user.email).execute()
        return [
            FleetOut(
                id=f.get("id"),
                name=f.get("name"),
                plan=f.get("plan"),
                admin_email=f.get("admin_email"),
                created_at=f.get("created_at")
            ) for f in resp.data or []
        ]
    except Exception as e:
        logger.exception(f"💥 Error listing fleets for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==========================================================
# Fleet User Routes
# ==========================================================
@router.get("/{fleet_id}/users", response_model=List[FleetUserOut])
def list_fleet_users(
    fleet_id: int,
    current_user: User = Depends(require_roles("admin", "business", "enterprise"))
):
    """
    Retrieve all users assigned to a specific fleet.
    """
    try:
        response = supabase.table("fleet_users").select("*").eq("fleet_id", fleet_id).execute()
        if hasattr(response, "error") and response.error:
            logger.error(f"❌ Supabase error while listing fleet users: {response.error.message}")
            raise HTTPException(status_code=500, detail=f"Supabase error: {response.error.message}")

        logger.info(f"✅ Fleet {fleet_id} users listed by {current_user.email}")
        return response.data or []

    except Exception as e:
        logger.exception(f"💥 Error listing fleet users for fleet {fleet_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{fleet_id}/users", response_model=FleetUserOut)
def add_fleet_user(
    fleet_id: int,
    user_data: FleetUserCreate,
    current_user: User = Depends(require_roles("admin", "business", "enterprise"))
):
    """
    Add a new employee/operator to a fleet.
    """
    try:
        # Business user limit check
        if current_user.role == RoleEnum.BUSINESS:
            response = supabase.table("fleet_users").select("*").eq("fleet_id", fleet_id).execute()
            if len(response.data or []) >= 5:
                logger.warning(f"⚠️ Fleet {fleet_id} limit reached (Business max 5 users)")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Business fleet user limit reached (max 5)")

        # Check if user already exists
        existing = supabase.table("fleet_users").select("*").eq("email", user_data.email).execute()
        if existing.data:
            logger.info(f"⚠️ Attempt to re-add existing fleet user: {user_data.email}")
            raise HTTPException(status_code=400, detail="User email already exists in fleet")

        hashed_pw = get_password_hash(user_data.password)

        insert_response = supabase.table("fleet_users").insert({
            "fleet_id": fleet_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "password": hashed_pw,
            "workstation": user_data.workstation,
            "role": user_data.role.value
        }).execute()

        if hasattr(insert_response, "error") and insert_response.error:
            logger.error(f"❌ Supabase insert error: {insert_response.error.message}")
            raise HTTPException(status_code=500, detail=f"Supabase error: {insert_response.error.message}")

        new_user = insert_response.data[0] if insert_response.data else None
        logger.info(f"✅ Fleet user {user_data.email} added to fleet {fleet_id} by {current_user.email}")

        return FleetUserOut(
            id=new_user.get("id") if new_user else None,
            email=user_data.email,
            full_name=user_data.full_name,
            workstation=user_data.workstation,
            role=user_data.role
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"💥 Error adding user {user_data.email} to fleet {fleet_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{fleet_id}/users/{user_email}", response_model=FleetUserOut)
def update_fleet_user(
    fleet_id: int,
    user_email: str,
    user_update: FleetUserUpdate,
    current_user: User = Depends(require_roles("admin", "business", "enterprise"))
):
    """
    Update fleet user details (name, workstation, role).
    """
    try:
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        response = supabase.table("fleet_users").update(update_data).eq("fleet_id", fleet_id).eq("email", user_email).execute()
        if hasattr(response, "error") and response.error:
            logger.error(f"❌ Supabase update error: {response.error.message}")
            raise HTTPException(status_code=500, detail=f"Supabase error: {response.error.message}")

        updated_user = response.data[0] if response.data else None
        logger.info(f"✅ Fleet user {user_email} updated by {current_user.email}")

        return FleetUserOut(
            id=updated_user.get("id") if updated_user else None,
            email=updated_user.get("email"),
            full_name=updated_user.get("full_name"),
            workstation=updated_user.get("workstation"),
            role=RoleEnum(updated_user.get("role"))
        )

    except Exception as e:
        logger.exception(f"💥 Error updating user {user_email} in fleet {fleet_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{fleet_id}/users/{user_email}")
def remove_fleet_user(
    fleet_id: int,
    user_email: str,
    current_user: User = Depends(require_roles("admin", "business", "enterprise"))
):
    """
    Remove a fleet user (employee resigned or reassigned).
    """
    try:
        response = supabase.table("fleet_users").delete().eq("fleet_id", fleet_id).eq("email", user_email).execute()
        if hasattr(response, "error") and response.error:
            logger.error(f"❌ Supabase deletion error: {response.error.message}")
            raise HTTPException(status_code=500, detail=f"Supabase error: {response.error.message}")

        logger.info(f"🗑️ Fleet user {user_email} removed from fleet {fleet_id} by {current_user.email}")
        return {"message": f"User {user_email} removed from fleet {fleet_id}"}

    except Exception as e:
        logger.exception(f"💥 Error removing fleet user {user_email} from fleet {fleet_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{fleet_id}/summary")
def get_fleet_summary(
    fleet_id: int,
    current_user: User = Depends(require_roles("admin", "business", "enterprise"))
):
    """
    Returns fleet summary:
    - Total users
    - Active workstations
    - Last update time
    """
    try:
        users = supabase.table("fleet_users").select("*").eq("fleet_id", fleet_id).execute()
        total_users = len(users.data or [])
        active_workstations = {u.get("workstation") for u in (users.data or [])}
        last_updated = users.data[-1].get("created_at") if users.data else None

        logger.info(f"📊 Fleet {fleet_id} summary retrieved by {current_user.email}")
        return {
            "fleet_id": fleet_id,
            "total_users": total_users,
            "active_workstations": list(active_workstations),
            "last_updated": last_updated
        }

    except Exception as e:
        logger.exception(f"💥 Error retrieving fleet summary for {fleet_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
