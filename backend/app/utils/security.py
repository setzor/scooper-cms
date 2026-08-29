"""Security utilities"""

from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import hashlib

# Simple password hashing using SHA256 with salt
# Note: For production, use bcrypt or Argon2

def hash_password(password: str) -> str:
    """Hash password with SHA256 and salt"""
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    try:
        salt, hashed = hashed_password.split('$')
        new_hash = hashlib.sha256((plain_password + salt).encode()).hexdigest()
        return secrets.compare_digest(new_hash, hashed)
    except:
        return False

# JWT
ALGORITHM = settings.ALGORITHM
SECRET_KEY = settings.SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

# HTTP Basic Auth
security = HTTPBasic()


def get_password_hash(password: str) -> str:
    """Hash password"""
    return hash_password(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_csrf_token() -> str:
    """Generate CSRF token"""
    return secrets.token_hex(32)


def validate_csrf_token(stored_token: str, provided_token: str) -> bool:
    """Validate CSRF token"""
    return secrets.compare_digest(stored_token, provided_token)


async def get_current_user(credentials: HTTPBasicCredentials = Depends(security)) -> dict:
    """Authenticate user with HTTP Basic Auth"""
    from app.database import User, SessionLocal
    
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(username=credentials.username).first()
        if not user or not verify_password(credentials.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User inactive",
            )
        return user
    finally:
        db.close()


async def get_current_user_or_none(request: Request) -> Optional[dict]:
    """Try to get current user, return None if not authenticated"""
    try:
        return await get_current_user()
    except HTTPException:
        return None


async def require_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Require admin user"""
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
