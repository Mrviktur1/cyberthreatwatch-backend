# backend/auth.py
from datetime import datetime, timedelta
from typing import Optional, Callable, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
from models import User, RoleEnum

# OAuth2 token URL used by routers (keep consistent with routers/auth.py)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# -------------------------
# Utility: password helpers
# -------------------------
def hash_password(plain_password: str) -> str:
    """Hash a plaintext password."""
    return bcrypt.hash(plain_password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against the hashed value."""
    return bcrypt.verify(plain_password, hashed_password)

# -------------------------
# Authenticate user helper
# -------------------------
def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    Return User if credentials are valid, otherwise None.
    Note: callers should check for user.is_active.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

# -------------------------
# JWT helpers
# -------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT.
    The 'data' should contain at least a 'sub' field (user id or identifier).
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

# -------------------------
# Dependency: get current user
# -------------------------
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Decode JWT and return the current active user from DB.
    Raises 401 if token invalid or user not found / inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        # Accept either int or string id in token
        try:
            user_id = int(sub)
        except (TypeError, ValueError):
            # keep as string if your app uses string IDs
            user_id = sub
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user

# -------------------------
# Role based dependency
# -------------------------
def require_roles(*roles: str) -> Callable[..., User]:
    """
    Dependency generator for role-based access.
    Usage in route: current_user = Depends(require_roles("admin","enterprise"))
    'roles' are strings matching RoleEnum values (e.g. "admin", "enterprise").
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # If current_user.role is an Enum, compare its value
        user_role_value = getattr(current_user.role, "value", current_user.role)
        if user_role_value not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient privileges")
        return current_user

    return role_checker

# -------------------------
# Optional convenience helpers
# -------------------------
def create_token_for_user(user: User, expires_minutes: Optional[int] = None) -> str:
    """
    Convenience wrapper to create token for a user object.
    Stores user.id as 'sub' and role as 'role' in token payload.
    """
    payload = {"sub": str(user.id), "role": getattr(user.role, "value", user.role)}
    expires = timedelta(minutes=expires_minutes) if expires_minutes else None
    return create_access_token(payload, expires)

# -------------------------
# Notes:
# - Make sure SECRET_KEY & others are loaded securely from config/environment.
# - If you use string UUIDs for user id, the decode converts to int only if possible.
# - For refresh tokens, token revocation, or rotating keys add a token store (Redis / DB).
# -------------------------
