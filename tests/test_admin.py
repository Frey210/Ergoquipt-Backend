import pytest
from fastapi import status

class TestAdmin:
    def test_register_operator_success(self, client, admin_token):
        """Test successful operator registration by admin"""
        operator_data = {
            "username": "newoperator",
            "email": "newoperator@test.com",
            "full_name": "New Operator",
            "university": "Test University",
            "role": "operator",
            "platform_access": "mobile"
        }
        
        response = client.post(
            "/api/v1/admin/users/register",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=operator_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "newoperator"
        assert data["email"] == "newoperator@test.com"
        assert "temporary_password" in data

    def test_register_operator_duplicate_username(self, client, admin_token, test_operator):
        """Test operator registration with duplicate username"""
        operator_data = {
            "username": "testoperator",  # Already exists
            "email": "new@test.com",
            "full_name": "New Operator",
            "role": "operator",
            "platform_access": "mobile"
        }
        
        response = client.post(
            "/api/v1/admin/users/register",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=operator_data
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_get_managed_operators(self, client, admin_token, db, test_admin):
        """Test getting list of managed operators"""
        from app.database.models import User, UserRole
        
        # Create test operators
        operator1 = User(
            username="managed1",
            email="managed1@test.com",
            password_hash="hash",
            full_name="Managed 1",
            role=UserRole.OPERATOR,
            created_by=test_admin.id
        )
        operator2 = User(
            username="managed2",
            email="managed2@test.com", 
            password_hash="hash",
            full_name="Managed 2",
            role=UserRole.OPERATOR,
            created_by=test_admin.id
        )
        
        db.add_all([operator1, operator2])
        db.commit()
        
        response = client.get(
            "/api/v1/admin/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

    def test_update_operator_status(self, client, admin_token, db, test_admin):
        """Test updating operator status"""
        from app.database.models import User, UserRole, UserStatus
        
        operator = User(
            username="status_test",
            email="status@test.com",
            password_hash="hash",
            full_name="Status Test",
            role=UserRole.OPERATOR,
            status=UserStatus.ACTIVE,
            created_by=test_admin.id
        )
        db.add(operator)
        db.commit()
        
        status_data = {
            "status": "inactive",
            "reason": "Testing status update"
        }
        
        response = client.patch(
            f"/api/v1/admin/users/{operator.id}/status",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=status_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        
        # Verify status changed
        db.refresh(operator)
        assert operator.status == "inactive"

    def test_reset_operator_password(self, client, admin_token, db, test_admin):
        """Test resetting operator password"""
        from app.database.models import User, UserRole
        
        operator = User(
            username="reset_test",
            email="reset@test.com",
            password_hash="old_hash",
            full_name="Reset Test",
            role=UserRole.OPERATOR,
            created_by=test_admin.id
        )
        db.add(operator)
        db.commit()
        
        response = client.post(
            f"/api/v1/admin/users/{operator.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "temporary_password" in data
        
        # Verify password was reset
        db.refresh(operator)
        assert operator.initial_password is True