from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database.models import Session, SessionConfig, SessionStatus, TestType, Respondent, User
from app.core.utils import generate_session_code
import uuid
from datetime import datetime

class SessionService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_session(
        self,
        respondent_id: uuid.UUID,
        test_type: TestType,
        operator_id: uuid.UUID,
        device_id: Optional[str] = None,
        device_name: Optional[str] = None,
        measurement_context: Optional[str] = None,
        environment_notes: Optional[str] = None,
        additional_notes: Optional[str] = None
    ) -> Session:
        """Create a new session"""
        # Verify respondent exists and belongs to operator
        respondent = self.db.query(Respondent).filter(
            Respondent.id == respondent_id,
            Respondent.created_by == operator_id
        ).first()
        
        if not respondent:
            raise ValueError("Respondent not found")
        
        session = Session(
            session_code=generate_session_code(),
            operator_id=operator_id,
            respondent_id=respondent_id,
            test_type=test_type,
            device_id=device_id,
            device_name=device_name,
            measurement_context=measurement_context,
            environment_notes=environment_notes,
            additional_notes=additional_notes,
            status=SessionStatus.DRAFT
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def get_user_sessions(
        self,
        user_id: uuid.UUID,
        status_filter: Optional[SessionStatus] = None,
        page: int = 1,
        limit: int = 20
    ) -> List[Session]:
        """Get sessions for a specific user"""
        query = self.db.query(Session).filter(Session.operator_id == user_id)
        
        if status_filter:
            query = query.filter(Session.status == status_filter)
        
        return query.order_by(Session.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    def get_admin_sessions(
        self,
        admin_id: uuid.UUID,
        operator_id: Optional[uuid.UUID] = None,
        status_filter: Optional[SessionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        limit: int = 50
    ) -> List[Session]:
        """Get sessions for admin (all operators managed by this admin)"""
        # Get operators managed by this admin
        managed_operators = self.db.query(User.id).filter(
            User.created_by == admin_id,
            User.role == UserRole.OPERATOR
        ).subquery()
        
        query = self.db.query(Session).filter(Session.operator_id.in_(managed_operators))
        
        if operator_id:
            query = query.filter(Session.operator_id == operator_id)
        
        if status_filter:
            query = query.filter(Session.status == status_filter)
        
        if start_date:
            query = query.filter(Session.created_at >= start_date)
        
        if end_date:
            query = query.filter(Session.created_at <= end_date)
        
        return query.order_by(Session.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    def start_session(self, session_id: uuid.UUID, operator_id: uuid.UUID) -> Session:
        """Start a session"""
        session = self.db.query(Session).filter(
            Session.id == session_id,
            Session.operator_id == operator_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        if session.status != SessionStatus.DRAFT:
            raise ValueError("Session can only be started from draft status")
        
        session.status = SessionStatus.ACTIVE
        session.started_at = datetime.utcnow()
        self.db.commit()
        
        return session
    
    def complete_session(self, session_id: uuid.UUID, operator_id: uuid.UUID) -> Session:
        """Complete a session"""
        session = self.db.query(Session).filter(
            Session.id == session_id,
            Session.operator_id == operator_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        session.status = SessionStatus.COMPLETED
        session.ended_at = datetime.utcnow()
        self.db.commit()
        
        return session
    
    def update_session_local_data(
        self, 
        session_id: uuid.UUID, 
        operator_id: uuid.UUID, 
        local_data: Dict[str, Any]
    ) -> Session:
        """Update session local data"""
        session = self.db.query(Session).filter(
            Session.id == session_id,
            Session.operator_id == operator_id
        ).first()
        
        if not session:
            raise ValueError("Session not found")
        
        session.local_data = local_data
        session.updated_at = datetime.utcnow()
        self.db.commit()
        
        return session