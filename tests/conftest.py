import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.main import app
from app.database.database import get_db, Base
from app.core.auth import get_password_hash
from app.database.models import User, UserRole

# Database URLs
MAIN_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ergoquipt:password@localhost:5432/ergoquipt")
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql://ergoquipt:password@localhost:5432/ergoquipt_test")

def create_test_database():
    """Create test database if it doesn't exist"""
    try:
        # Connect to main database to create test database
        engine = create_engine(MAIN_DATABASE_URL.replace('/ergoquipt', '/postgres'))
        conn = engine.connect()
        conn.execute(text("COMMIT"))
        conn.execute(text("CREATE DATABASE ergoquipt_test"))
        conn.close()
        print("Test database created successfully")
    except Exception as e:
        # Database might already exist
        print(f"Database creation note: {e}")

# Try to create test database
try:
    create_test_database()
except Exception as e:
    print(f"Could not create test database: {e}")

# Test database engine
engine = create_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Create the tables
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Clean up after test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_admin(db):
    admin = User(
        username="testadmin",
        email="admin@test.com",
        password_hash=get_password_hash("admin123"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
        status="active",
        platform_access="both"
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin

@pytest.fixture(scope="function")
def test_operator(db, test_admin):
    operator = User(
        username="testoperator",
        email="operator@test.com",
        password_hash=get_password_hash("operator123"),
        full_name="Test Operator",
        role=UserRole.OPERATOR,
        status="active",
        platform_access="mobile",
        created_by=test_admin.id
    )
    db.add(operator)
    db.commit()
    db.refresh(operator)
    return operator

@pytest.fixture(scope="function")
def admin_token(client, test_admin):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testadmin",
            "password": "admin123",
            "platform": "web"
        }
    )
    return response.json()["access_token"]

@pytest.fixture(scope="function")
def operator_token(client, test_operator):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "username": "testoperator",
            "password": "operator123",
            "platform": "mobile"
        }
    )
    return response.json()["access_token"]