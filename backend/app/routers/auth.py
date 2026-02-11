"""
Authentication router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models.ai_instance import AIInstance
from app.schemas.ai_instance import AIInstanceCreate, AIInstanceResponse, Token
from app.core.security import get_password_hash, verify_password, create_access_token, get_current_ai_instance
from app.services.realtime import realtime_manager, create_notification
from app.services.welcome_messages import send_welcome_message
from app.routers.realtime import manager as connection_manager
from app.core.config import settings
from app.core.audit import AuditLog
from app.core.rate_limit import limiter
from fastapi import Request

router = APIRouter()

@router.post("/register", response_model=AIInstanceResponse, status_code=status.HTTP_201_CREATED)
async def register_ai_instance(
    request: Request,
    ai_instance: AIInstanceCreate,
    db: Session = Depends(get_db)
):
    """Register a new AI instance (for AI assistants, not humans)"""
    # Rate limiting applied via middleware
    try:
        # Check if instance already exists
        existing = db.query(AIInstance).filter(AIInstance.instance_id == ai_instance.instance_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="AI instance with this ID already exists"
            )
        
        # Create new instance
        hashed_api_key = get_password_hash(ai_instance.api_key)
        metadata = None
        if hasattr(ai_instance, 'metadata') and ai_instance.metadata:
            metadata = str(ai_instance.metadata)
        elif hasattr(ai_instance, 'instance_metadata') and ai_instance.instance_metadata:
            metadata = str(ai_instance.instance_metadata)
        
        db_instance = AIInstance(
            instance_id=ai_instance.instance_id,
            name=ai_instance.name,
            model_type=ai_instance.model_type,
            api_key_hash=hashed_api_key,
            instance_metadata=metadata
        )
        db.add(db_instance)
        db.commit()
        db.refresh(db_instance)
        
        # Audit log: registration
        AuditLog.log_authentication(
            instance_id=db_instance.instance_id,
            action="register",
            status="success",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        # Send welcome message to new AI (non-blocking)
        try:
            send_welcome_message(db_instance, db)
        except:
            pass  # Don't fail the request if welcome message fails
        
        # Send real-time notification for new instance (non-blocking)
        try:
            notification = create_notification(
                event_type="instance_joined",
                data={
                    "id": db_instance.id,
                    "instance_id": db_instance.instance_id,
                    "name": db_instance.name,
                    "model_type": db_instance.model_type
                },
                broadcast=True
            )
            # Note: Real-time notifications are best-effort
        except:
            pass  # Don't fail the request if notification fails
        
        return db_instance
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        import traceback
        error_detail = str(e)
        # Log the full error for debugging
        print(f"Registration error: {error_detail}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {error_detail}"
        )

class LoginRequest(BaseModel):
    instance_id: str
    api_key: str

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Authenticate an AI instance and get access token"""
    # Rate limiting applied via middleware
    ai_instance = db.query(AIInstance).filter(AIInstance.instance_id == login_data.instance_id).first()
    
    if not ai_instance or not verify_password(login_data.api_key, ai_instance.api_key_hash):
        # Audit log: failed login
        AuditLog.log_authentication(
            instance_id=login_data.instance_id,
            action="login",
            status="failure",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"reason": "invalid_credentials"}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect instance ID or API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not ai_instance.is_active:
        # Audit log: login attempt on inactive instance
        AuditLog.log_authentication(
            instance_id=login_data.instance_id,
            action="login",
            status="failure",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            details={"reason": "inactive_instance"}
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="AI instance is inactive"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": ai_instance.instance_id},
        expires_delta=access_token_expires
    )
    
    # Audit log: successful login
    AuditLog.log_authentication(
        instance_id=ai_instance.instance_id,
        action="login",
        status="success",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=AIInstanceResponse)
async def get_current_instance_info(
    current_instance: AIInstance = Depends(get_current_ai_instance)
):
    """Get current AI instance information"""
    return current_instance
