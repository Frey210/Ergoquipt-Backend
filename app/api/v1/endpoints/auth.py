from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.core.auth import authenticate_user, create_access_token, get_password_hash, verify_password, get_current_user
from app.schemas.auth import LoginRequest, Token, ChangePasswordRequest
from app.schemas.users import UserResponse
from app.database.models import User
from datetime import timedelta
import secrets
import string
from uuid import UUID

router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.username, login_data.password, login_data.platform)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # ✅ PERBAIKAN: Berikan token sementara untuk change-password
    access_token_expires = timedelta(minutes=60 * 24)  # 24 hours
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    # ✅ PERBAIKAN: Kembalikan token meskipun perlu ganti password
    return Token(
        access_token=access_token,
        token_type="bearer",
        requires_password_change=user.initial_password
    )

@router.post("/change-password-initial")
async def change_password_initial(
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Change password for first-time login (without requiring authentication)
    """
    # Find user by temporary password
    user = db.query(User).filter(
        User.initial_password == True,
        User.status.in_([UserStatus.ACTIVE, UserStatus.PENDING])
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user found with temporary password or user not active"
        )
    
    # Verify temporary password
    if not verify_password(password_data.temporary_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid temporary password"
        )
    
    # Update password
    user.password_hash = get_password_hash(password_data.new_password)
    user.initial_password = False
    user.status = UserStatus.ACTIVE  # Aktifkan user setelah ganti password
    
    # Log the action
    log = UserRegistrationLog(
        admin_id=user.created_by if user.created_by else user.id,
        operator_id=user.id,
        action="password_change_initial",
        notes="User changed initial password",
        ip_address="127.0.0.1"
    )
    db.add(log)
    db.commit()
    
    # Generate new token after password change
    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "message": "Password changed successfully. Account is now active."
    }

@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Change password for authenticated users
    """
    # For initial password change, verify the temporary password
    if current_user.initial_password:
        if not verify_password(password_data.temporary_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid temporary password"
            )
    else:
        # For regular password change, verify current password
        if not verify_password(password_data.temporary_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password"
            )
    
    # Update password
    current_user.password_hash = get_password_hash(password_data.new_password)
    current_user.initial_password = False
    db.commit()
    
    # Generate new token
    access_token_expires = timedelta(minutes=60 * 24)
    access_token = create_access_token(
        data={"sub": str(current_user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "message": "Password changed successfully"
    }

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    # Convert UUID to string untuk response
    user_dict = {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "university": current_user.university,
        "role": current_user.role,
        "status": current_user.status,
        "platform_access": current_user.platform_access,
        "initial_password": current_user.initial_password,
        "created_at": current_user.created_at
    }
    return UserResponse(**user_dict)

def generate_temporary_password(length=12):
    """Generate a secure temporary password"""
    characters = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(characters) for _ in range(length))