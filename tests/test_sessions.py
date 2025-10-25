import pytest
from fastapi import status
import uuid

class TestSessions:
    def test_create_session_success(self, client, operator_token, db, test_operator):
        """Test successful session creation"""
        from app.database.models import Respondent
        
        # Create respondent first
        respondent = Respondent(
            guest_name="Session Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session_data = {
            "respondent_id": str(respondent.id),
            "test_type": "reaction_time",
            "device_id": "TEST001",
            "device_name": "Test Device",
            "measurement_context": "Baseline measurement",
            "environment_notes": "Quiet room",
            "additional_notes": "First session"
        }
        
        response = client.post(
            "/api/v1/mobile/sessions",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=session_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["test_type"] == "reaction_time"
        assert data["status"] == "draft"
        assert "session_code" in data

    def test_create_session_invalid_respondent(self, client, operator_token):
        """Test session creation with invalid respondent"""
        session_data = {
            "respondent_id": str(uuid.uuid4()),  # Non-existent respondent
            "test_type": "reaction_time"
        }
        
        response = client.post(
            "/api/v1/mobile/sessions",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=session_data
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_session_config(self, client, operator_token, db, test_operator):
        """Test adding session configuration"""
        from app.database.models import Respondent, Session
        
        # Create respondent and session
        respondent = Respondent(
            guest_name="Config Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="TEST-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="reaction_time"
        )
        db.add(session)
        db.commit()
        
        config_data = {
            "config_type": "reaction_time",
            "stimulus_type": "red",
            "stimulus_category": "led",
            "trials_per_stimulus": 10,
            "order_index": 1
        }
        
        response = client.post(
            f"/api/v1/mobile/sessions/{session.id}/configs",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=config_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_start_session(self, client, operator_token, db, test_operator):
        """Test starting a session"""
        from app.database.models import Respondent, Session
        
        respondent = Respondent(
            guest_name="Start Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="START-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="reaction_time",
            status="draft"
        )
        db.add(session)
        db.commit()
        
        response = client.patch(
            f"/api/v1/mobile/sessions/{session.id}/start",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify session status changed
        db.refresh(session)
        assert session.status == "active"
        assert session.started_at is not None

    def test_complete_session(self, client, operator_token, db, test_operator):
        """Test completing a session"""
        from app.database.models import Respondent, Session
        
        respondent = Respondent(
            guest_name="Complete Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="COMPLETE-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="reaction_time",
            status="active"
        )
        db.add(session)
        db.commit()
        
        response = client.patch(
            f"/api/v1/mobile/sessions/{session.id}/complete",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify session status changed
        db.refresh(session)
        assert session.status == "completed"
        assert session.ended_at is not None

    def test_update_local_data(self, client, operator_token, db, test_operator):
        """Test updating session local data"""
        from app.database.models import Respondent, Session
        
        respondent = Respondent(
            guest_name="Local Data Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="LOCAL-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="reaction_time"
        )
        db.add(session)
        db.commit()
        
        local_data = {
            "trials": [
                {
                    "stimulus_type": "red",
                    "stimulus_category": "led",
                    "response_time": 150,
                    "trial_number": 1,
                    "timestamp": "2024-01-15T10:00:00Z"
                }
            ],
            "progress": {
                "completed_trials": 1,
                "total_trials": 10
            }
        }
        
        response = client.patch(
            f"/api/v1/mobile/sessions/{session.id}/local-data",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=local_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify local data was saved
        db.refresh(session)
        assert session.local_data is not None

    def test_get_sessions_list(self, client, operator_token, db, test_operator):
        """Test getting sessions list"""
        from app.database.models import Respondent, Session
        
        respondent = Respondent(
            guest_name="List Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session1 = Session(
            session_code="LIST-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="reaction_time"
        )
        session2 = Session(
            session_code="LIST-002",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="tympanic"
        )
        
        db.add_all([session1, session2])
        db.commit()
        
        response = client.get(
            "/api/v1/mobile/sessions",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2