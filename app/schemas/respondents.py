from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RespondentCreate(BaseModel):
    guest_name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    height: Optional[int] = None  # in cm
    weight: Optional[int] = None  # in kg
    status: str = "guest"
    university: Optional[str] = None

class RespondentResponse(BaseModel):
    id: str
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

class RespondentUpdate(BaseModel):
    guest_name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    status: Optional[str] = None
    university: Optional[str] = None