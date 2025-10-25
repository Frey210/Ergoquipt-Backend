from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import csv
import io
from datetime import datetime, date
from app.database.database import get_db
from app.core.auth import get_current_user, require_admin, require_web_platform
from app.database.models import Session, ReactionTrial, TympaniReading, VitalReading, User
import uuid

router = APIRouter()

@router.get("/sessions/{session_id}/export.csv")
async def export_session_data(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify session access
    session = db.query(Session).filter(Session.id == uuid.UUID(session_id)).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if user has access to this session
    if current_user.role in ["admin", "super_admin"]:
        if session.operator_id != current_user.id and session.operator.created_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        if session.operator_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header based on session type
    if session.test_type == "reaction_time":
        writer.writerow(["Trial Number", "Stimulus Type", "Stimulus Category", "Response Time (ms)", "Reaction Type", "Timestamp"])
        
        trials = db.query(ReactionTrial).filter(ReactionTrial.session_id == session.id).order_by(ReactionTrial.trial_number).all()
        for trial in trials:
            writer.writerow([
                trial.trial_number,
                trial.stimulus_type,
                trial.stimulus_category,
                trial.response_time,
                trial.reaction_type,
                trial.created_at.isoformat()
            ])
    
    elif session.test_type == "tympanic":
        writer.writerow(["Reading Number", "Temperature (°C)", "Measurement Phase", "Body Position", "Environment Temp", "Timestamp"])
        
        readings = db.query(TympaniReading).filter(TympaniReading.session_id == session.id).order_by(TympaniReading.reading_number).all()
        for reading in readings:
            writer.writerow([
                reading.reading_number,
                float(reading.temperature),
                reading.measurement_phase,
                reading.body_position,
                float(reading.environment_temp) if reading.environment_temp else "",
                reading.reading_time.isoformat()
            ])
    
    elif session.test_type == "vitals":
        writer.writerow(["Reading Number", "Heart Rate (BPM)", "HRV", "SpO2 (%)", "Measurement Phase", "Activity Context", "Body Position", "Timestamp"])
        
        readings = db.query(VitalReading).filter(VitalReading.session_id == session.id).order_by(VitalReading.reading_number).all()
        for reading in readings:
            writer.writerow([
                reading.reading_number,
                reading.heart_rate,
                float(reading.heart_rate_variability) if reading.heart_rate_variability else "",
                reading.spo2,
                reading.measurement_phase,
                reading.activity_context,
                reading.body_position,
                reading.reading_time.isoformat()
            ])
    
    output.seek(0)
    
    filename = f"{session.session_code}_{session.test_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/admin/export/sessions.csv")
async def export_sessions_data(
    start_date: date = Query(...),
    end_date: date = Query(...),
    operator_id: Optional[str] = Query(None),
    test_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
    platform_check: User = Depends(require_web_platform)
):
    # Build query for sessions managed by this admin
    query = db.query(Session).join(User).filter(User.created_by == admin.id)
    
    # Apply filters
    query = query.filter(Session.created_at >= start_date, Session.created_at <= end_date)
    
    if operator_id:
        query = query.filter(Session.operator_id == uuid.UUID(operator_id))
    
    if test_type:
        query = query.filter(Session.test_type == test_type)
    
    sessions = query.order_by(Session.created_at).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Session Code", "Operator", "Respondent", "Test Type", "Status", "Device", "Start Time", "End Time", "Trials Completed", "Environment Notes"])
    
    for session in sessions:
        writer.writerow([
            session.session_code,
            session.operator.full_name,
            session.respondent.guest_name,
            session.test_type,
            session.status,
            session.device_name or "",
            session.started_at.isoformat() if session.started_at else "",
            session.ended_at.isoformat() if session.ended_at else "",
            session.trials_completed,
            session.environment_notes or ""
        ])
    
    output.seek(0)
    filename = f"sessions_export_{start_date}_{end_date}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )