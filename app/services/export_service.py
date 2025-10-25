import csv
import io
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Session, ReactionTrial, TympaniReading, VitalReading, User
import uuid

class ExportService:
    def __init__(self, db: Session):
        self.db = db
    
    def export_session_to_csv(self, session_id: uuid.UUID) -> tuple[str, str]:
        """Export session data to CSV format"""
        session = self.db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise ValueError("Session not found")
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        if session.test_type == "reaction_time":
            writer.writerow(["Trial Number", "Stimulus Type", "Stimulus Category", "Response Time (ms)", "Reaction Type", "Timestamp"])
            
            trials = self.db.query(ReactionTrial).filter(
                ReactionTrial.session_id == session_id
            ).order_by(ReactionTrial.trial_number).all()
            
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
            
            readings = self.db.query(TympaniReading).filter(
                TympaniReading.session_id == session_id
            ).order_by(TympaniReading.reading_number).all()
            
            for reading in readings:
                writer.writerow([
                    reading.reading_number,
                    float(reading.temperature),
                    reading.measurement_phase or "",
                    reading.body_position or "",
                    float(reading.environment_temp) if reading.environment_temp else "",
                    reading.reading_time.isoformat()
                ])
        
        elif session.test_type == "vitals":
            writer.writerow(["Reading Number", "Heart Rate (BPM)", "HRV", "SpO2 (%)", "Measurement Phase", "Activity Context", "Body Position", "Timestamp"])
            
            readings = self.db.query(VitalReading).filter(
                VitalReading.session_id == session_id
            ).order_by(VitalReading.reading_number).all()
            
            for reading in readings:
                writer.writerow([
                    reading.reading_number,
                    reading.heart_rate,
                    float(reading.heart_rate_variability) if reading.heart_rate_variability else "",
                    reading.spo2,
                    reading.measurement_phase or "",
                    reading.activity_context or "",
                    reading.body_position or "",
                    reading.reading_time.isoformat()
                ])
        
        csv_content = output.getvalue()
        filename = f"{session.session_code}_{session.test_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return csv_content, filename
    
    def export_sessions_to_csv(
        self,
        admin_id: uuid.UUID,
        start_date: date,
        end_date: date,
        operator_id: Optional[uuid.UUID] = None,
        test_type: Optional[str] = None
    ) -> tuple[str, str]:
        """Export multiple sessions to CSV format"""
        # Get managed operators
        managed_operators = self.db.query(User.id).filter(
            User.created_by == admin_id,
            User.role == UserRole.OPERATOR
        ).subquery()
        
        query = self.db.query(Session).filter(
            Session.operator_id.in_(managed_operators),
            Session.created_at >= start_date,
            Session.created_at <= end_date
        )
        
        if operator_id:
            query = query.filter(Session.operator_id == operator_id)
        
        if test_type:
            query = query.filter(Session.test_type == test_type)
        
        sessions = query.order_by(Session.created_at).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Session Code", "Operator", "Respondent", "Test Type", "Status", 
            "Device", "Start Time", "End Time", "Trials Completed", 
            "Measurement Context", "Environment Notes"
        ])
        
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
                session.measurement_context or "",
                session.environment_notes or ""
            ])
        
        csv_content = output.getvalue()
        filename = f"sessions_export_{start_date}_{end_date}.csv"
        
        return csv_content, filename
    
    def export_operator_performance(
        self,
        admin_id: uuid.UUID,
        start_date: date,
        end_date: date
    ) -> tuple[str, str]:
        """Export operator performance report"""
        managed_operators = self.db.query(User).filter(
            User.created_by == admin_id,
            User.role == UserRole.OPERATOR
        ).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            "Operator", "Total Sessions", "Completed Sessions", "Active Sessions",
            "Reaction Time Tests", "Tympanic Tests", "Vitals Tests",
            "Total Trials", "Avg Trials per Session", "Last Activity"
        ])
        
        for operator in managed_operators:
            sessions = self.db.query(Session).filter(
                Session.operator_id == operator.id,
                Session.created_at >= start_date,
                Session.created_at <= end_date
            ).all()
            
            total_sessions = len(sessions)
            completed_sessions = len([s for s in sessions if s.status == "completed"])
            active_sessions = len([s for s in sessions if s.status == "active"])
            
            reaction_time_tests = len([s for s in sessions if s.test_type == "reaction_time"])
            tympanic_tests = len([s for s in sessions if s.test_type == "tympanic"])
            vitals_tests = len([s for s in sessions if s.test_type == "vitals"])
            
            total_trials = sum(s.trials_completed for s in sessions)
            avg_trials = total_trials / total_sessions if total_sessions > 0 else 0
            
            last_activity = max([s.updated_at for s in sessions]) if sessions else None
            
            writer.writerow([
                operator.full_name,
                total_sessions,
                completed_sessions,
                active_sessions,
                reaction_time_tests,
                tympanic_tests,
                vitals_tests,
                total_trials,
                round(avg_trials, 2),
                last_activity.isoformat() if last_activity else ""
            ])
        
        csv_content = output.getvalue()
        filename = f"operator_performance_{start_date}_{end_date}.csv"
        
        return csv_content, filename