from pydantic import BaseModel, EmailStr, validator
from typing import Optional
import re

class LoginRequest(BaseModel):
    username: str
    password: str
    platform: str  # "mobile" or "web"

    @validator('platform')
    def validate_platform(cls, v):
        if v not in ['mobile', 'web']:
            raise ValueError('Platform must be either "mobile" or "web"')
        return v

class Token(BaseModel):
    access_token: str
    token_type: str
    requires_password_change: bool = False

class TokenData(BaseModel):
    user_id: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    temporary_password: str
    new_password: str
    confirm_password: str

    @validator('new_password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class ChangePasswordInitialRequest(BaseModel):
    username: str
    temporary_password: str
    new_password: str
    confirm_password: str

    @validator('new_password')
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', v):
            raise ValueError('Password must contain at least one special character')
        return v

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v