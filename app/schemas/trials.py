from pydantic import BaseModel, validator
from typing import Optional, List
from datetime import datetime
import uuid

class ReactionTrialCreate(BaseModel):
    stimulus_type: str
    stimulus_category: str
    response_time: int
    trial_number: int
    reaction_type: str = "correct"

class ReactionTrialBatchCreate(BaseModel):
    trials: List[ReactionTrialCreate]

class TympaniReadingCreate(BaseModel):
    temperature: float
    reading_number: int
    measurement_phase: Optional[str] = None
    body_position: Optional[str] = None
    environment_temp: Optional[float] = None
    reading_time: Optional[datetime] = None

class VitalReadingCreate(BaseModel):
    heart_rate: int
    heart_rate_variability: float
    spo2: int
    reading_number: int
    measurement_phase: Optional[str] = None
    activity_context: Optional[str] = None
    body_position: Optional[str] = None
    reading_time: Optional[datetime] = None

class TrialResponse(BaseModel):
    id: str  # UUID sebagai string
    stimulus_type: str
    stimulus_category: str
    response_time: int
    trial_number: int
    reaction_type: str
    created_at: datetime

    class Config:
        from_attributes = True

    @validator('id', pre=True)
    def convert_uuid_to_string(cls, value):
        if isinstance(value, uuid.UUID):
            return str(value)
        return value

class TrialStatistics(BaseModel):
    total_trials: int
    mean_response_time: float
    min_response_time: int
    max_response_time: int
    std_deviation: Optional[float] = None

class SessionStatisticsResponse(BaseModel):
    overall: TrialStatistics
    by_stimulus: dict