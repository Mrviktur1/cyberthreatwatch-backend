# backend/routers/auth.py

import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.hash import bcrypt
from database import get_db
from models import User, RoleEnum
from typing import Optional
from dotenv import load_dotenv
from logger import logger

# =========================
# Load environment variables
# =========================
load_dotenv()  # Reads .env file in project root
SECRET_KEY = os.getenv("SECRET_KEY", "SUPER_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

# =========================
# Initialize router
# =========================
router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# =========================
# Helper: Create Access Token
# =========================
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# =========================
# Helper: Get Current User
# =========================
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = int(payload.get("sub"))
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user

# =========================
# Role-Based Access Dependency
# =========================
def require_roles(*roles: str):
    """Ensure the current user has one of the allowed roles."""
    def wrapper(current_user: User = Depends(get_current_user)):
        if current_user.role.value not in roles:
            logger.warning(f"Access denied for user {current_user.email} (role: {current_user.role.value})")
            raise HTTPException(status_code=403, detail="Access denied: insufficient privileges")
        return current_user
    return wrapper

# =========================
# 🧾 Signup
# =========================
@router.post("/signup")
def signup(email: str, full_name: str, password: str, db: Session = Depends(get_db)):
    try:
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            logger.warning(f"Signup attempt with already registered email: {email}")
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_pw = bcrypt.hash(password)
        user = User(email=email, full_name=full_name, password=hashed_pw, role=RoleEnum.STUDENT)
        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info(f"New user registered: {email} (role: {user.role.value})")
        return {"message": "User created successfully", "user_id": user.id, "role": user.role.value}

    except Exception as e:
        logger.error(f"Error during signup for {email}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# =========================
# 🔑 Login
# =========================
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == form_data.username).first()
        if not user or not bcrypt.verify(form_data.password, user.password):
            logger.warning(f"Failed login attempt for {form_data.username}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user {user.email}")
            raise HTTPException(status_code=403, detail="User account is inactive")

        access_token = create_access_token(
            data={"sub": str(user.id), "role": user.role.value},
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        logger.info(f"User logged in successfully: {user.email}")
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role.value,
            "user_id": user.id,
            "full_name": user.full_name
        }

    except Exception as e:
        logger.error(f"Database error during login for {form_data.username}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# =========================
# 👤 Profile Info
# =========================
@router.get("/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    logger.info(f"User profile accessed: {current_user.email}")
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }
