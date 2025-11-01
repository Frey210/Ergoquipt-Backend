from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.core.auth import require_admin, require_web_platform, get_current_user, get_password_hash
from app.schemas.users import UserCreate, UserResponse, UserRegisterResponse, UserStatusUpdate
from app.database.models import User, UserRole, UserStatus, UserRegistrationLog
from app.api.v1.endpoints.auth import generate_temporary_password
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/users/register", response_model=UserRegisterResponse)
async def register_operator(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform)
):
    # Check if username or email already exists
    existing_user = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    # Generate temporary password
    temporary_password = generate_temporary_password()
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(temporary_password),
        full_name=user_data.full_name,
        university=user_data.university,
        role=user_data.role,
        status=UserStatus.PENDING,
        platform_access=user_data.platform_access,
        created_by=admin.id,
        initial_password=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log the registration
    log = UserRegistrationLog(
        admin_id=admin.id,
        operator_id=user.id,
        action="create",
        notes=f"Registered operator {user_data.username}",
        ip_address="127.0.0.1"
    )
    db.add(log)
    db.commit()
    
    return UserRegisterResponse(
        id=str(user.id),  # Convert UUID to string
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        temporary_password=temporary_password,
        status=user.status,
        created_at=user.created_at
    )

@router.get("/users", response_model=List[UserResponse])
async def get_managed_operators(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform),
    status_filter: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    # Get operators managed by this admin
    query = db.query(User).filter(User.created_by == admin.id, User.role == UserRole.OPERATOR)
    
    if status_filter:
        query = query.filter(User.status == UserStatus(status_filter))
    
    users = query.offset((page - 1) * limit).limit(limit).all()
    
    # Convert to response models
    return [UserResponse(
        id=str(user.id),  # Convert UUID to string
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        university=user.university,
        role=user.role,
        status=user.status,
        platform_access=user.platform_access,
        initial_password=user.initial_password,
        created_at=user.created_at
    ) for user in users]

@router.patch("/users/{user_id}/status")
async def update_operator_status(
    user_id: str,
    status_data: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform)
):
    # Check if operator exists and is managed by this admin
    operator = db.query(User).filter(
        User.id == uuid.UUID(user_id),
        User.created_by == admin.id,
        User.role == UserRole.OPERATOR
    ).first()
    
    if not operator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operator not found"
        )
    
    # Update status
    operator.status = status_data.status
    operator.updated_at = datetime.utcnow()
    
    # Log the action
    log = UserRegistrationLog(
        admin_id=admin.id,
        operator_id=operator.id,
        action="status_update",
        notes=f"Changed status to {status_data.status}. Reason: {status_data.reason}",
        ip_address="127.0.0.1"
    )
    db.add(log)
    db.commit()
    
    return {"success": True, "message": f"Operator status updated to {status_data.status}"}

@router.post("/users/{user_id}/reset-password")
async def reset_operator_password(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform)
):
    operator = db.query(User).filter(
        User.id == uuid.UUID(user_id),
        User.created_by == admin.id,
        User.role == UserRole.OPERATOR
    ).first()
    
    if not operator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Operator not found"
        )
    
    # Generate new temporary password
    temporary_password = generate_temporary_password()
    operator.password_hash = get_password_hash(temporary_password)
    operator.initial_password = True
    operator.updated_at = datetime.utcnow()
    
    # Log the action
    log = UserRegistrationLog(
        admin_id=admin.id,
        operator_id=operator.id,
        action="password_reset",
        notes="Password reset by admin",
        ip_address="127.0.0.1"
    )
    db.add(log)
    db.commit()
    
    return {
        "success": True,
        "temporary_password": temporary_password,
        "message": "Password reset successfully"
    }