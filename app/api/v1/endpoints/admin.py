from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.database import get_db
from app.core.auth import require_admin, require_web_platform, get_current_user, get_password_hash
from app.schemas.users import UserCreate, UserResponse, UserRegisterResponse, UserStatusUpdate
from app.database.models import (
    User,
    UserRole,
    UserStatus,
    UserRegistrationLog,
    Respondent,
    Session,
    SessionConfig,
    ReactionTrial,
    TympaniReading,
    VitalReading,
    TympaniBulkRecording,
    TympaniBulkReading,
    HrvBulkRecording,
    HrvBulkReading,
)
from app.api.v1.endpoints.auth import generate_temporary_password
import uuid
from datetime import datetime

router = APIRouter()

def _delete_operator_data(db: Session, operator_id: uuid.UUID):
    respondent_ids = [
        row[0]
        for row in db.query(Respondent.id).filter(Respondent.created_by == operator_id).all()
    ]
    session_query = db.query(Session.id).filter(Session.operator_id == operator_id)
    if respondent_ids:
        session_query = session_query.union(
            db.query(Session.id).filter(Session.respondent_id.in_(respondent_ids))
        )
    session_ids = [row[0] for row in session_query.all()]

    if session_ids:
        db.query(ReactionTrial).filter(ReactionTrial.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(TympaniReading).filter(TympaniReading.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(VitalReading).filter(VitalReading.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(SessionConfig).filter(SessionConfig.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(Session).filter(Session.id.in_(session_ids)).delete(synchronize_session=False)

    if respondent_ids:
        db.query(Respondent).filter(Respondent.id.in_(respondent_ids)).delete(synchronize_session=False)

    tympani_recording_ids = [
        row[0]
        for row in db.query(TympaniBulkRecording.id).filter(TympaniBulkRecording.operator_id == operator_id).all()
    ]
    if tympani_recording_ids:
        db.query(TympaniBulkReading).filter(
            TympaniBulkReading.recording_id.in_(tympani_recording_ids)
        ).delete(synchronize_session=False)
        db.query(TympaniBulkRecording).filter(
            TympaniBulkRecording.id.in_(tympani_recording_ids)
        ).delete(synchronize_session=False)

    hrv_recording_ids = [
        row[0]
        for row in db.query(HrvBulkRecording.id).filter(HrvBulkRecording.operator_id == operator_id).all()
    ]
    if hrv_recording_ids:
        db.query(HrvBulkReading).filter(
            HrvBulkReading.recording_id.in_(hrv_recording_ids)
        ).delete(synchronize_session=False)
        db.query(HrvBulkRecording).filter(
            HrvBulkRecording.id.in_(hrv_recording_ids)
        ).delete(synchronize_session=False)

    db.query(UserRegistrationLog).filter(UserRegistrationLog.operator_id == operator_id).delete(synchronize_session=False)
    db.query(UserRegistrationLog).filter(UserRegistrationLog.admin_id == operator_id).delete(synchronize_session=False)

    db.query(User).filter(User.id == operator_id).delete(synchronize_session=False)

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
    
    if user_data.role not in [UserRole.OPERATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role for registration"
        )

    if user_data.role == UserRole.ADMIN and admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin can create admins"
        )

    if user_data.role == UserRole.OPERATOR and admin.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
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
    role: Optional[str] = Query(None),
    created_by: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    if admin.role == UserRole.SUPER_ADMIN:
        query = db.query(User).filter(User.role.in_([UserRole.ADMIN, UserRole.OPERATOR]))
        if created_by:
            try:
                created_by_uuid = uuid.UUID(created_by)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid created_by filter"
                )
            query = query.filter(User.created_by == created_by_uuid)
    else:
        query = db.query(User).filter(User.created_by == admin.id, User.role == UserRole.OPERATOR)
    
    if role:
        query = query.filter(User.role == UserRole(role))
    
    if role:
        try:
            query = query.filter(User.role == UserRole(role))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role filter"
            )

    if status_filter:
        try:
            query = query.filter(User.status == UserStatus(status_filter))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status filter"
            )

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

@router.patch("/admins/{admin_id}/status")
async def update_admin_status(
    admin_id: str,
    status_data: UserStatusUpdate,
    db: Session = Depends(get_db),
    super_admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform)
):
    if super_admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )

    try:
        admin_uuid = uuid.UUID(admin_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid admin ID")

    if super_admin.id == admin_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot update your own status")

    admin_user = db.query(User).filter(
        User.id == admin_uuid,
        User.role == UserRole.ADMIN
    ).first()

    if not admin_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    admin_user.status = status_data.status
    admin_user.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "message": f"Admin status updated to {status_data.status}"}

@router.post("/admins/{admin_id}/reset-password")
async def reset_admin_password(
    admin_id: str,
    db: Session = Depends(get_db),
    super_admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform)
):
    if super_admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )

    try:
        admin_uuid = uuid.UUID(admin_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid admin ID")

    admin_user = db.query(User).filter(
        User.id == admin_uuid,
        User.role == UserRole.ADMIN
    ).first()

    if not admin_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    temporary_password = generate_temporary_password()
    admin_user.password_hash = get_password_hash(temporary_password)
    admin_user.initial_password = True
    admin_user.updated_at = datetime.utcnow()
    db.commit()

    return {
        "success": True,
        "temporary_password": temporary_password,
        "message": "Password reset successfully"
    }

@router.delete("/operators/{operator_id}")
async def delete_operator(
    operator_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform)
):
    try:
        operator_uuid = uuid.UUID(operator_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid operator ID")

    operator = db.query(User).filter(User.id == operator_uuid, User.role == UserRole.OPERATOR).first()
    if not operator:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator not found")

    if admin.role != UserRole.SUPER_ADMIN and operator.created_by != admin.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    _delete_operator_data(db, operator_uuid)
    db.commit()

    return {"success": True, "message": "Operator deleted"}

@router.delete("/admins/{admin_id}")
async def delete_admin(
    admin_id: str,
    db: Session = Depends(get_db),
    super_admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform)
):
    if super_admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super admin access required")

    try:
        admin_uuid = uuid.UUID(admin_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid admin ID")

    if super_admin.id == admin_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account")

    target_admin = db.query(User).filter(User.id == admin_uuid, User.role == UserRole.ADMIN).first()
    if not target_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found")

    operator_ids = [
        row[0]
        for row in db.query(User.id).filter(
            User.created_by == admin_uuid,
            User.role == UserRole.OPERATOR
        ).all()
    ]
    for operator_id in operator_ids:
        _delete_operator_data(db, operator_id)

    admin_session_ids = [
        row[0]
        for row in db.query(Session.id).filter(Session.operator_id == admin_uuid).all()
    ]
    if admin_session_ids:
        db.query(ReactionTrial).filter(ReactionTrial.session_id.in_(admin_session_ids)).delete(synchronize_session=False)
        db.query(TympaniReading).filter(TympaniReading.session_id.in_(admin_session_ids)).delete(synchronize_session=False)
        db.query(VitalReading).filter(VitalReading.session_id.in_(admin_session_ids)).delete(synchronize_session=False)
        db.query(SessionConfig).filter(SessionConfig.session_id.in_(admin_session_ids)).delete(synchronize_session=False)
        db.query(Session).filter(Session.id.in_(admin_session_ids)).delete(synchronize_session=False)

    admin_respondent_ids = [
        row[0]
        for row in db.query(Respondent.id).filter(Respondent.created_by == admin_uuid).all()
    ]
    if admin_respondent_ids:
        db.query(Respondent).filter(Respondent.id.in_(admin_respondent_ids)).delete(synchronize_session=False)

    db.query(UserRegistrationLog).filter(UserRegistrationLog.admin_id == admin_uuid).delete(synchronize_session=False)
    db.query(UserRegistrationLog).filter(UserRegistrationLog.operator_id == admin_uuid).delete(synchronize_session=False)

    db.query(User).filter(User.id == admin_uuid).delete(synchronize_session=False)
    db.commit()

    return {"success": True, "message": "Admin deleted"}
