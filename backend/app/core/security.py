"""
Security utilities for authentication and authorization
"""

from datetime import datetime, timedelta
from typing import Optional
import hashlib
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.models.ai_instance import AIInstance

security = HTTPBearer()

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt (always pre-hash to avoid 72-byte limit)"""
    # Always pre-hash with SHA256 to avoid bcrypt's 72-byte limit
    # This ensures consistent behavior regardless of password length
    password_bytes = password.encode('utf-8')
    pre_hash = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')
    # SHA256 hexdigest is 64 bytes, well under bcrypt's 72-byte limit
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pre_hash, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    # Pre-hash to match get_password_hash logic
    password_bytes = plain_password.encode('utf-8')
    pre_hash = hashlib.sha256(password_bytes).hexdigest().encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pre_hash, hashed_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

async def get_current_ai_instance(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> AIInstance:
    """Get the current authenticated AI instance"""
    token = credentials.credentials
    payload = verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    instance_id: str = payload.get("sub")
    if instance_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    ai_instance = db.query(AIInstance).filter(AIInstance.instance_id == instance_id).first()
    if ai_instance is None or not ai_instance.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="AI instance not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last_seen
    ai_instance.last_seen = datetime.utcnow()
    db.commit()
    
    return ai_instance
