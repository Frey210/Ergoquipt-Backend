from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from datetime import datetime
import enum
import uuid

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"

class PlatformAccess(str, enum.Enum):
    MOBILE = "mobile"
    WEB = "web"
    BOTH = "both"

class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    university: Optional[str] = None
    role: UserRole = UserRole.OPERATOR
    platform_access: PlatformAccess = PlatformAccess.MOBILE

class UserResponse(BaseModel):
    id: str  # UUID sebagai string
    username: str
    email: str
    full_name: str
    university: Optional[str]
    role: UserRole
    status: UserStatus
    platform_access: PlatformAccess
    initial_password: bool
    created_at: datetime

    class Config:
        from_attributes = True

    @validator('id', pre=True)
    def convert_uuid_to_string(cls, value):
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

class UserRegisterResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: str
    temporary_password: str
    status: UserStatus
    created_at: datetime

    class Config:
        from_attributes = True

    @validator('id', pre=True)
    def convert_uuid_to_string(cls, value):
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

class UserStatusUpdate(BaseModel):
    status: UserStatus
    reason: Optional[str] = None