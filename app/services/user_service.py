from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database.models import User, UserRole, UserStatus, UserRegistrationLog
from app.core.security import generate_secure_password, get_password_hash
from app.core.utils import generate_uuid
import uuid
from datetime import datetime

class UserService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_operator(
        self, 
        username: str, 
        email: str, 
        full_name: str, 
        university: Optional[str],
        platform_access: str,
        created_by: uuid.UUID
    ) -> Dict[str, Any]:
        """Create a new operator user"""
        # Check if username or email exists
        existing_user = self.db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            raise ValueError("Username or email already exists")
        
        # Generate temporary password
        temporary_password = generate_secure_password()
        
        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(temporary_password),
            full_name=full_name,
            university=university,
            role=UserRole.OPERATOR,
            status=UserStatus.PENDING,
            platform_access=platform_access,
            created_by=created_by,
            initial_password=True
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return {
            "user": user,
            "temporary_password": temporary_password
        }
    
    def get_managed_operators(
        self, 
        admin_id: uuid.UUID, 
        status_filter: Optional[str] = None,
        page: int = 1, 
        limit: int = 20
    ) -> List[User]:
        """Get operators managed by specific admin"""
        query = self.db.query(User).filter(
            User.created_by == admin_id,
            User.role == UserRole.OPERATOR
        )
        
        if status_filter:
            query = query.filter(User.status == UserStatus(status_filter))
        
        return query.offset((page - 1) * limit).limit(limit).all()
    
    def update_user_status(
        self, 
        user_id: uuid.UUID, 
        status: UserStatus, 
        admin_id: uuid.UUID
    ) -> User:
        """Update user status"""
        user = self.db.query(User).filter(
            User.id == user_id,
            User.created_by == admin_id
        ).first()
        
        if not user:
            raise ValueError("User not found or not authorized")
        
        user.status = status
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def reset_user_password(self, user_id: uuid.UUID, admin_id: uuid.UUID) -> str:
        """Reset user password and return temporary password"""
        user = self.db.query(User).filter(
            User.id == user_id,
            User.created_by == admin_id
        ).first()
        
        if not user:
            raise ValueError("User not found or not authorized")
        
        temporary_password = generate_secure_password()
        user.password_hash = get_password_hash(temporary_password)
        user.initial_password = True
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        return temporary_password
    
    def log_admin_action(
        self, 
        admin_id: uuid.UUID, 
        operator_id: uuid.UUID, 
        action: str, 
        notes: str,
        ip_address: str = "127.0.0.1"
    ):
        """Log admin action for audit trail"""
        log = UserRegistrationLog(
            admin_id=admin_id,
            operator_id=operator_id,
            action=action,
            notes=notes,
            ip_address=ip_address
        )
        
        self.db.add(log)
        self.db.commit()