from pydantic import BaseModel, validator
from typing import List, Optional
from datetime import datetime
import uuid

class RespondentSnapshot(BaseModel):
    local_id: Optional[int] = None
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[int] = None
    weight: Optional[int] = None
    created_at: Optional[datetime] = None

class HrvBulkReadingCreate(BaseModel):
    heart_rate: Optional[int] = None
    rr_interval: Optional[float] = None
    hrv: Optional[float] = None
    spo2: Optional[float] = None
    recorded_at: datetime

class HrvBulkCreate(BaseModel):
    respondent: RespondentSnapshot
    time_start: datetime
    time_end: datetime
    readings: List[HrvBulkReadingCreate]

class HrvBulkCreateResponse(BaseModel):
    recording_id: str
    label: str
    count: int

class HrvBulkListItem(BaseModel):
    id: str
    label: str
    respondent: RespondentSnapshot
    time_start: datetime
    time_end: datetime
    count: int
    created_at: datetime

    class Config:
        from_attributes = True

    @validator("id", pre=True)
    def convert_uuid_to_string(cls, value):
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

class HrvBulkListResponse(BaseModel):
    items: List[HrvBulkListItem]
    total: int

class HrvBulkDownloadRequest(BaseModel):
    recording_ids: List[str]
    format: str
