import os
from datetime import datetime, timedelta
from typing import Optional, Set

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

from database import get_db
from models import User, RoleEnum, Subscription
from logger import logger
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from supabase_client import supabase
from services.cloudflare_auth import get_cloudflare_token

# ======================================================
# ⚙️ Router setup
# ======================================================
router = APIRouter(prefix="/auth", tags=["Authentication"])
load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory token blacklist (replace with Redis in production)
_token_blacklist: Set[str] = set()

CLOUDFLARE_CLIENT_ID = os.getenv("CLOUDFLARE_CLIENT_ID")
CLOUDFLARE_REDIRECT_URI = os.getenv("CLOUDFLARE_REDIRECT_URI")


# ==========================
# Password Utilities
# ==========================
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# ==========================
# JWT Utilities
# ==========================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ==========================
# Current User Dependency
# ==========================
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if token in _token_blacklist:
        logger.warning("Blacklisted token usage attempt")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except (JWTError, TypeError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ==========================
# Role Enforcement Dependency
# ==========================
def require_roles(*roles: str):
    def _checker(current_user: User = Depends(get_current_user)):
        if current_user.role.value not in roles:
            logger.warning(f"Access denied for user {current_user.email} (role: {current_user.role.value})")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: insufficient privileges")
        return current_user
    return _checker


# ==========================
# Subscription / Trial Enforcement
# ==========================
def enforce_subscription(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """
    Enforce trial/subscription rules:
    - Students: 4 hrs/day
    - Business / Enterprise: 7-day trial, then subscription required
    """
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()

    if current_user.role == RoleEnum.STUDENT:
        if sub and sub.daily_hours_used >= 4 and sub.last_active.date() == datetime.utcnow().date():
            raise HTTPException(
                status_code=403,
                detail="You have used your daily 4 hours. Subscribe for full access or wait until tomorrow."
            )

    elif current_user.role in [RoleEnum.BUSINESS, RoleEnum.ENTERPRISE]:
        if not sub:
            # Auto-create 7-day trial if none exists
            trial_end = datetime.utcnow() + timedelta(days=7)
            sub = Subscription(user_id=current_user.id, start_date=datetime.utcnow(), end_date=trial_end, active=True)
            db.add(sub)
            db.commit()
            db.refresh(sub)
        elif not sub.active or sub.end_date < datetime.utcnow():
            raise HTTPException(status_code=403, detail="Trial expired. Subscribe to continue full access.")

    return current_user


# ==========================
# Signup
# ==========================
@router.post("/signup")
def signup(email: str, full_name: str, password: str, role: RoleEnum = RoleEnum.STUDENT, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Enterprise must use business email
    if role == RoleEnum.ENTERPRISE and not email.endswith(".com"):
        raise HTTPException(status_code=400, detail="Enterprise must use business email")

    hashed_pw = get_password_hash(password)
    user = User(email=email, full_name=full_name, password=hashed_pw, role=role, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"New user created: {email} (role={role.value})")
    return {"message": "User created successfully", "user_id": user.id, "role": user.role.value}


# ==========================
# Login
# ==========================
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account inactive")

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"User logged in: {user.email}")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "role": user.role.value,
        "full_name": user.full_name
    }


# ==========================
# Cloudflare OAuth Login
# ==========================
@router.get("/cloudflare/login")
def cloudflare_login():
    if not CLOUDFLARE_CLIENT_ID or not CLOUDFLARE_REDIRECT_URI:
        raise HTTPException(status_code=500, detail="Cloudflare SSO not configured")

    auth_url = (
        f"https://oauth.cloudflareaccess.com/authorize"
        f"?response_type=code"
        f"&client_id={CLOUDFLARE_CLIENT_ID}"
        f"&redirect_uri={CLOUDFLARE_REDIRECT_URI}"
        f"&scope=openid email profile"
    )
    return {"auth_url": auth_url}


@router.get("/cloudflare/callback")
def cloudflare_callback(code: str = Query(...), db: Session = Depends(get_db)):
    token_data = get_cloudflare_token(code)

    # Fetch Cloudflare user info (replace with Supabase function or API call)
    user_info = {"email": token_data.get("email", "unknown@cloudflare.com"),
                 "name": token_data.get("name", "Cloudflare User")}

    email = user_info.get("email")
    name = user_info.get("name", email.split("@")[0])

    if not email:
        raise HTTPException(status_code=400, detail="Cloudflare account missing email")

    # Check DB for user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(email=email, full_name=name, role=RoleEnum.USER)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"🆕 New Cloudflare user created: {email}")

    access_token = create_access_token({"sub": str(user.id), "role": user.role.value})
    logger.info(f"✅ Cloudflare user logged in: {email}")

    # Check Supabase Fleet assignment
    fleet_user = supabase.table("fleet_users").select("*").eq("email", email).execute()
    if fleet_user.data:
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "redirect": f"/fleet/{fleet_user.data[0]['fleet_id']}/workstation"
        }

    return {"access_token": access_token, "token_type": "bearer"}


# ==========================
# Logout
# ==========================
@router.post("/logout")
def logout(token: str = Depends(oauth2_scheme)):
    _token_blacklist.add(token)
    logger.info("Token revoked via logout")
    return {"message": "Logged out (token revoked)"}


# ==========================
# Current User Profile
# ==========================
@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": getattr(current_user, "created_at", None)
    }
