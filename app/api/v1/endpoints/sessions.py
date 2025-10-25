from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database.database import get_db
from app.core.auth import get_current_user, require_mobile_platform, require_admin, require_web_platform
from app.schemas.sessions import SessionCreate, SessionResponse, SessionConfigCreate, SessionUpdate
from app.database.models import Session, SessionConfig, SessionStatus, User, Respondent
import uuid
from datetime import datetime
import random
import string

router = APIRouter()

def generate_session_code():
    """Generate unique session code: RT-YYYYMMDD-XXX"""
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"RT-{date_str}-{random_str}"

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    # Verify respondent exists and belongs to current user
    respondent = db.query(Respondent).filter(
        Respondent.id == uuid.UUID(session_data.respondent_id),
        Respondent.created_by == current_user.id
    ).first()
    
    if not respondent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Respondent not found"
        )
    
    # Create session
    session = Session(
        session_code=generate_session_code(),
        operator_id=current_user.id,
        respondent_id=respondent.id,
        test_type=session_data.test_type,
        device_id=session_data.device_id,
        device_name=session_data.device_name,
        measurement_context=session_data.measurement_context,
        environment_notes=session_data.environment_notes,
        additional_notes=session_data.additional_notes,
        status=SessionStatus.DRAFT
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session

@router.post("/sessions/{session_id}/configs")
async def add_session_config(
    session_id: str,
    config_data: SessionConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    session = db.query(Session).filter(
        Session.id == uuid.UUID(session_id),
        Session.operator_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    config = SessionConfig(
        session_id=session.id,
        config_type=config_data.config_type,
        stimulus_type=config_data.stimulus_type,
        stimulus_category=config_data.stimulus_category,
        trials_per_stimulus=config_data.trials_per_stimulus,
        order_index=config_data.order_index,
        measurement_duration=config_data.measurement_duration,
        sampling_interval=config_data.sampling_interval,
        target_condition=config_data.target_condition
    )
    
    db.add(config)
    db.commit()
    
    return {"success": True, "message": "Configuration added"}

@router.patch("/sessions/{session_id}/start")
async def start_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    session = db.query(Session).filter(
        Session.id == uuid.UUID(session_id),
        Session.operator_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    if session.status != SessionStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session can only be started from draft status"
        )
    
    session.status = SessionStatus.ACTIVE
    session.started_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Session started"}

@router.patch("/sessions/{session_id}/complete")
async def complete_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    session = db.query(Session).filter(
        Session.id == uuid.UUID(session_id),
        Session.operator_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.status = SessionStatus.COMPLETED
    session.ended_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Session completed"}

@router.patch("/sessions/{session_id}/local-data")
async def update_local_data(
    session_id: str,
    local_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    session = db.query(Session).filter(
        Session.id == uuid.UUID(session_id),
        Session.operator_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.local_data = local_data
    session.updated_at = datetime.utcnow()
    db.commit()
    
    return {"success": True, "message": "Local data updated"}

@router.get("/sessions", response_model=List[SessionResponse])
async def get_my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100)
):
    query = db.query(Session).filter(Session.operator_id == current_user.id)
    
    if status:
        query = query.filter(Session.status == SessionStatus(status))
    
    sessions = query.order_by(Session.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return sessions

@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    session = db.query(Session).filter(
        Session.id == uuid.UUID(session_id),
        Session.operator_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    return session