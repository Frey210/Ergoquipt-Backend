import pytest
from fastapi import status
import uuid
from datetime import datetime

class TestTrials:
    def test_create_reaction_trials_batch(self, client, operator_token, db, test_operator):
        """Test batch creation of reaction trials"""
        from app.database.models import Respondent, Session
        
        # Setup
        respondent = Respondent(
            guest_name="Trial Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="TRIAL-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="reaction_time",
            status="active"
        )
        db.add(session)
        db.commit()
        
        # Test data
        trials_data = {
            "trials": [
                {
                    "stimulus_type": "red",
                    "stimulus_category": "led",
                    "response_time": 150,
                    "trial_number": 1,
                    "reaction_type": "correct"
                },
                {
                    "stimulus_type": "red",
                    "stimulus_category": "led", 
                    "response_time": 145,
                    "trial_number": 2,
                    "reaction_type": "correct"
                }
            ]
        }
        
        response = client.post(
            f"/api/v1/mobile/sessions/{session.id}/trials/batch",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=trials_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "2 trials recorded" in data["message"]
        
        # Verify session progress updated
        db.refresh(session)
        assert session.trials_completed == 2

    def test_create_tympani_reading(self, client, operator_token, db, test_operator):
        """Test creating tympanic reading"""
        from app.database.models import Respondent, Session
        
        respondent = Respondent(
            guest_name="Tympanic Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="TYMP-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="tympanic"
        )
        db.add(session)
        db.commit()
        
        reading_data = {
            "temperature": 36.5,
            "reading_number": 1,
            "measurement_phase": "baseline",
            "body_position": "sitting",
            "environment_temp": 24.0
        }
        
        response = client.post(
            f"/api/v1/mobile/sessions/{session.id}/tympani-readings",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=reading_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_create_vital_reading(self, client, operator_token, db, test_operator):
        """Test creating vital reading"""
        from app.database.models import Respondent, Session
        
        respondent = Respondent(
            guest_name="Vital Test",
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        session = Session(
            session_code="VITAL-001",
            operator_id=test_operator.id,
            respondent_id=respondent.id,
            test_type="vitals"
        )
        db.add(session)
        db.commit()
        
        reading_data = {
            "heart_rate": 72,
            "heart_rate_variability": 45.2,
            "spo2": 98,
            "reading_number": 1,
            "measurement_phase": "baseline",
            "activity_context": "resting",
            "body_position": "sitting"
        }
        
        response = client.post(
            f"/api/v1/mobile/sessions/{session.id}/vital-readings",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=reading_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True

    def test_create_trials_invalid_session(self, client, operator_token):
        """Test creating trials for non-existent session"""
        trials_data = {
            "trials": [
                {
                    "stimulus_type": "red",
                    "stimulus_category": "led",
                    "response_time": 150,
                    "trial_number": 1
                }
            ]
        }
        
        response = client.post(
            f"/api/v1/mobile/sessions/{uuid.uuid4()}/trials/batch",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=trials_data
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND