import pytest
from fastapi import status
import uuid
from datetime import datetime, date

class TestExport:
    def test_export_session_csv(self, client, operator_token, db, test_operator):
        """Test exporting session data to CSV"""
        from app.database.models import Respondent, Session, ReactionTrial
        
        # Setup session with trials
        respondent = Respondent(
            guest_name="Export Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="EXPORT-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="reaction_time",
            status="completed"
        )
        db.add(session)
        db.commit()
        
        # Add some trials
        trial1 = ReactionTrial(
            session_id=session.id,
            stimulus_type="red",
            stimulus_category="led",
            response_time=150,
            trial_number=1
        )
        trial2 = ReactionTrial(
            session_id=session.id,
            stimulus_type="blue", 
            stimulus_category="led",
            response_time=160,
            trial_number=2
        )
        db.add_all([trial1, trial2])
        db.commit()
        
        response = client.get(
            f"/api/v1/export/sessions/{session.id}/export.csv",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv"
        assert "attachment" in response.headers["content-disposition"]
        
        # Verify CSV content
        content = response.content.decode()
        assert "Trial Number" in content
        assert "red" in content
        assert "blue" in content

    def test_export_nonexistent_session(self, client, operator_token):
        """Test exporting non-existent session"""
        response = client.get(
            f"/api/v1/export/sessions/{uuid.uuid4()}/export.csv",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_export_sessions(self, client, admin_token, db, test_admin):
        """Test admin export of multiple sessions"""
        from app.database.models import User, UserRole, Respondent, Session
        
        # Create operator and sessions
        operator = User(
            username="export_op",
            email="export@test.com",
            password_hash="hash",
            full_name="Export Operator",
            role=UserRole.OPERATOR,
            created_by=test_admin.id
        )
        db.add(operator)
        db.commit()
        
        respondent = Respondent(
            guest_name="Admin Export Test",
            created_by=operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="ADMIN-EXPORT-001",
            operator_id=operator.id,
            respondent_id=respondent.id,
            test_type="reaction_time",
            status="completed"
        )
        db.add(session)
        db.commit()
        
        today = date.today()
        response = client.get(
            f"/api/v1/admin/export/sessions.csv?start_date={today}&end_date={today}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/csv"