"""JWT Authentication utilities for Annapurna"""
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
import secrets

# Secret key for JWT - In production, use environment variable
SECRET_KEY = secrets.token_hex(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 30

def create_access_token(user_id: int, email: str) -> str:
    """Create a short-lived access token"""
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "email": email,
        "type": "access",
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(user_id: int) -> str:
    """Create a long-lived refresh token"""
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "exp": expire
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != token_type:
            return None
        return payload
    except JWTError:
        return None

def get_user_id_from_token(token: str) -> Optional[int]:
    """Extract user_id from access token"""
    payload = verify_token(token, "access")
    if payload:
        return int(payload.get("sub"))
    return None

def verify_refresh_token(token: str) -> Optional[int]:
    """Verify refresh token and return user_id"""
    payload = verify_token(token, "refresh")
    if payload:
        return int(payload.get("sub"))
    return None
