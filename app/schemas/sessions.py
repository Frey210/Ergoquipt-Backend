from pydantic import BaseModel, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import enum
import uuid

class TestType(str, enum.Enum):
    REACTION_TIME = "reaction_time"
    TYMPANIC = "tympanic"
    VITALS = "vitals"
    COMBINED = "combined"

class SessionStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class SessionCreate(BaseModel):
    respondent_id: str
    test_type: TestType
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    measurement_context: Optional[str] = None
    environment_notes: Optional[str] = None
    additional_notes: Optional[str] = None

class SessionConfigCreate(BaseModel):
    config_type: str  # reaction_time, tympanic, vitals
    stimulus_type: Optional[str] = None
    stimulus_category: Optional[str] = None
    trials_per_stimulus: Optional[int] = 10
    order_index: Optional[int] = None
    measurement_duration: Optional[int] = None
    sampling_interval: Optional[int] = None
    target_condition: Optional[str] = None

class SessionResponse(BaseModel):
    id: str  # UUID sebagai string
    session_code: str
    test_type: TestType
    status: SessionStatus
    device_id: Optional[str]
    device_name: Optional[str]
    measurement_context: Optional[str]
    environment_notes: Optional[str]
    additional_notes: Optional[str]
    trials_completed: int
    total_trials: int
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

    @validator('id', pre=True)
    def convert_uuid_to_string(cls, value):
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

class SessionUpdate(BaseModel):
    status: Optional[SessionStatus] = None
    local_data: Optional[Dict[str, Any]] = None
    trials_completed: Optional[int] = None