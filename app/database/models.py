from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Enum as SQLEnum, DECIMAL, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .database import Base
import enum

class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"

class UserStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"

class RegistrationType(str, enum.Enum):
    ADMIN_CREATED = "admin_created"
    SELF_REGISTERED = "self_registered"

class PlatformAccess(str, enum.Enum):
    MOBILE = "mobile"
    WEB = "web"
    BOTH = "both"

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

class StimulusType(str, enum.Enum):
    RED = "red"
    YELLOW = "yellow"
    BLUE = "blue"
    SIREN = "siren"
    AMBULANCE = "ambulance"
    GAUGE = "gauge"
    SPECTRUM = "spectrum"

class StimulusCategory(str, enum.Enum):
    LED = "led"
    SOUND = "sound"
    VISUAL = "visual"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    university = Column(String(255))
    role = Column(SQLEnum(UserRole), default=UserRole.OPERATOR)
    status = Column(SQLEnum(UserStatus), default=UserStatus.PENDING)
    
    # Registration system
    registration_type = Column(SQLEnum(RegistrationType), default=RegistrationType.ADMIN_CREATED)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    initial_password = Column(Boolean, default=True)
    
    # Platform access
    platform_access = Column(SQLEnum(PlatformAccess), default=PlatformAccess.MOBILE)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class UserRegistrationLog(Base):
    __tablename__ = "user_registration_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # create, activate, deactivate, suspend, password_reset
    notes = Column(Text)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Respondent(Base):
    __tablename__ = "respondents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guest_name = Column(String(255), nullable=False)
    gender = Column(String(10))  # male, female, other
    age = Column(Integer)
    height = Column(Integer)  # in cm
    weight = Column(Integer)  # in kg
    status = Column(String(20), default="guest")  # student, guest
    university = Column(String(255))
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Session(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_code = Column(String(50), unique=True, nullable=False)
    operator_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    respondent_id = Column(UUID(as_uuid=True), ForeignKey("respondents.id"), nullable=False)
    test_type = Column(SQLEnum(TestType), nullable=False)
    device_id = Column(String(100))
    device_name = Column(String(255))
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.DRAFT)
    
    # Metadata kontekstual
    measurement_context = Column(Text)
    environment_notes = Column(Text)
    additional_notes = Column(Text)
    
    # Data sementara
    local_data = Column(JSON)
    trials_completed = Column(Integer, default=0)
    total_trials = Column(Integer, default=0)
    
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class SessionConfig(Base):
    __tablename__ = "session_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    config_type = Column(String(50), nullable=False)  # reaction_time, tympanic, vitals
    
    # Untuk Reaction Time
    stimulus_type = Column(SQLEnum(StimulusType), nullable=True)
    stimulus_category = Column(SQLEnum(StimulusCategory), nullable=True)
    trials_per_stimulus = Column(Integer, default=10)
    order_index = Column(Integer)
    
    # Untuk Tympanic & Vitals
    measurement_duration = Column(Integer)  # Durasi dalam menit
    sampling_interval = Column(Integer)  # Interval dalam detik
    target_condition = Column(Text)  # Target kondisi
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReactionTrial(Base):
    __tablename__ = "reaction_trials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    stimulus_type = Column(SQLEnum(StimulusType), nullable=False)
    stimulus_category = Column(SQLEnum(StimulusCategory), nullable=False)
    response_time = Column(Integer, nullable=False)  # dalam milidetik
    trial_number = Column(Integer, nullable=False)
    reaction_type = Column(String(20), default="correct")  # correct, incorrect, timeout
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TympaniReading(Base):
    __tablename__ = "tympani_readings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    temperature = Column(DECIMAL(4, 2), nullable=False)
    reading_number = Column(Integer, nullable=False)
    measurement_phase = Column(String(50))  # baseline, intervention, recovery
    body_position = Column(String(50))  # sitting, standing, lying_down
    environment_temp = Column(DECIMAL(4, 1))  # Suhu lingkungan
    reading_time = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class VitalReading(Base):
    __tablename__ = "vital_readings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    heart_rate = Column(Integer)
    heart_rate_variability = Column(DECIMAL(5, 2))
    spo2 = Column(Integer)
    reading_number = Column(Integer, nullable=False)
    measurement_phase = Column(String(50))  # baseline, exercise, recovery, sleep
    activity_context = Column(String(50))  # resting, light_activity, moderate_exercise, intense_exercise, sleep
    body_position = Column(String(50))  # sitting, standing, lying_down
    reading_time = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())