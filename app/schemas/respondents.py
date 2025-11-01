from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
import uuid

class RespondentCreate(BaseModel):
    guest_name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    height: Optional[int] = None  # in cm
    weight: Optional[int] = None  # in kg
    status: str = "guest"
    university: Optional[str] = None

class RespondentResponse(BaseModel):
    id: str  # UUID sebagai string
    guest_name: str
    gender: Optional[str]
    age: Optional[int]
    height: Optional[int]
    weight: Optional[int]
    status: str
    university: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

    @validator('id', pre=True)
    def convert_uuid_to_string(cls, value):
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

class RespondentUpdate(BaseModel):
    guest_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    status: Optional[str] = None
    university: Optional[str] = None