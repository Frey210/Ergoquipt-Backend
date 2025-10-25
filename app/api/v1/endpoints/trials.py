from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database.database import get_db
from app.core.auth import get_current_user, require_mobile_platform
from app.schemas.trials import ReactionTrialBatchCreate, TympaniReadingCreate, VitalReadingCreate
from app.database.models import ReactionTrial, TympaniReading, VitalReading, Session, SessionStatus, User
import uuid
from datetime import datetime

router = APIRouter()

@router.post("/sessions/{session_id}/trials/batch")
async def create_reaction_trials_batch(
    session_id: str,
    trials_data: ReactionTrialBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    platform_check: User = Depends(require_mobile_platform)
):
    # Verify session exists and belongs to current user
    session = db.query(Session).filter(
        Session.id == uuid.UUID(session_id),
        Session.operator_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    # Create trials
    trials = []
    for trial_data in trials_data.trials:
        trial = ReactionTrial(
            session_id=session.id,
            stimulus_type=trial_data.stimulus_type,
            stimulus_category=trial_data.stimulus_category,
            response_time=trial_data.response_time,
            trial_number=trial_data.trial_number,
            reaction_type=trial_data.reaction_type
        )
        trials.append(trial)
    
    db.add_all(trials)
    
    # Update session progress
    session.trials_completed += len(trials_data.trials)
    db.commit()
    
    return {"success": True, "message": f"{len(trials_data.trials)} trials recorded"}

@router.post("/sessions/{session_id}/tympani-readings")
async def create_tympani_reading(
    session_id: str,
    reading_data: TympaniReadingCreate,
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
    
    reading = TympaniReading(
        session_id=session.id,
        temperature=reading_data.temperature,
        reading_number=reading_data.reading_number,
        measurement_phase=reading_data.measurement_phase,
        body_position=reading_data.body_position,
        environment_temp=reading_data.environment_temp,
        reading_time=reading_data.reading_time or datetime.utcnow()
    )
    
    db.add(reading)
    db.commit()
    
    return {"success": True, "message": "Tympanic reading recorded"}

@router.post("/sessions/{session_id}/vital-readings")
async def create_vital_reading(
    session_id: str,
    reading_data: VitalReadingCreate,
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
    
    reading = VitalReading(
        session_id=session.id,
        heart_rate=reading_data.heart_rate,
        heart_rate_variability=reading_data.heart_rate_variability,
        spo2=reading_data.spo2,
        reading_number=reading_data.reading_number,
        measurement_phase=reading_data.measurement_phase,
        activity_context=reading_data.activity_context,
        body_position=reading_data.body_position,
        reading_time=reading_data.reading_time or datetime.utcnow()
    )
    
    db.add(reading)
    db.commit()
    
    return {"success": True, "message": "Vital reading recorded"}