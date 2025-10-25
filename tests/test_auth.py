import pytest
from fastapi import status
from app.core.auth import get_password_hash

class TestAuth:
    def test_login_success(self, client, test_operator):
        """Test successful login"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testoperator",
                "password": "operator123",
                "platform": "mobile"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["requires_password_change"] is False

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "nonexistent",
                "password": "wrongpassword",
                "platform": "mobile"
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_wrong_platform(self, client, test_operator):
        """Test login with wrong platform"""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testoperator",
                "password": "operator123",
                "platform": "web"  # Operator hanya bisa mobile
            }
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_change_password_success(self, client, test_operator):
        """Test successful password change"""
        # First login to get token
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "username": "testoperator",
                "password": "operator123",
                "platform": "mobile"
            }
        )
        
        token = login_response.json()["access_token"]
        
        # Change password
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "temporary_password": "operator123",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data

    def test_change_password_weak_password(self, client, operator_token):
        """Test password change with weak password"""
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {operator_token}"},
            json={
                "temporary_password": "operator123",
                "new_password": "weak",
                "confirm_password": "weak"
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_current_user(self, client, operator_token, test_operator):
        """Test get current user info"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {operator_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "testoperator"
        assert data["full_name"] == "Test Operator"
        assert data["role"] == "operator"

    def test_protected_endpoint_no_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_protected_endpoint_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED