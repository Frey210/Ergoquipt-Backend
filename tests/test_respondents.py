import pytest
from fastapi import status

class TestRespondents:
    def test_create_respondent_success(self, client, operator_token):
        """Test successful respondent creation"""
        respondent_data = {
            "guest_name": "Jane Smith",
            "gender": "female",
            "age": 30,
            "height": 165,
            "weight": 60,
            "status": "guest",
            "university": "Test University"
        }
        
        response = client.post(
            "/api/v1/mobile/respondents",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=respondent_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["guest_name"] == "Jane Smith"
        assert data["gender"] == "female"
        assert data["age"] == 30

    def test_create_respondent_missing_required_fields(self, client, operator_token):
        """Test respondent creation with missing required fields"""
        respondent_data = {
            "gender": "female",
            "age": 30
            # Missing guest_name (required)
        }
        
        response = client.post(
            "/api/v1/mobile/respondents",
            headers={"Authorization": f"Bearer {operator_token}"},
            json=respondent_data
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_respondents_list(self, client, operator_token, db, test_operator):
        """Test getting list of respondents"""
        # Create test respondents first
        from app.database.models import Respondent
        
        respondent1 = Respondent(
            guest_name="Respondent 1",
            created_by=test_operator.id
        )
        respondent2 = Respondent(
            guest_name="Respondent 2", 
            created_by=test_operator.id
        )
        
        db.add_all([respondent1, respondent2])
        db.commit()
        
        response = client.get(
            "/api/v1/mobile/respondents",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2
        assert data[0]["guest_name"] == "Respondent 1"

    def test_get_respondents_pagination(self, client, operator_token, db, test_operator):
        """Test respondents list with pagination"""
        from app.database.models import Respondent
        
        # Create multiple respondents
        for i in range(15):
            respondent = Respondent(
                guest_name=f"Respondent {i}",
                created_by=test_operator.id
            )
            db.add(respondent)
        db.commit()
        
        response = client.get(
            "/api/v1/mobile/respondents?page=1&limit=10",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 10

    def test_get_respondent_detail(self, client, operator_token, db, test_operator):
        """Test getting respondent details"""
        from app.database.models import Respondent
        import uuid
        
        respondent = Respondent(
            id=uuid.uuid4(),
            guest_name="Detail Test",
            age=25,
            created_by=test_operator.id
        )
        db.add(respondent)
        db.commit()
        
        response = client.get(
            f"/api/v1/mobile/respondents/{respondent.id}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["guest_name"] == "Detail Test"
        assert data["age"] == 25

    def test_get_nonexistent_respondent(self, client, operator_token):
        """Test getting non-existent respondent"""
        import uuid
        
        response = client.get(
            f"/api/v1/mobile/respondents/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND