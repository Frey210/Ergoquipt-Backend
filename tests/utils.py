import uuid
from datetime import datetime, timedelta

def generate_test_data():
    """Generate test data for testing"""
    return {
        "respondent_id": str(uuid.uuid4()),
        "session_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4())
    }

def get_auth_headers(token: str):
    """Get authorization headers with token"""
    return {"Authorization": f"Bearer {token}"}

def create_test_respondent_data():
    return {
        "guest_name": "John Doe",
        "gender": "male",
        "age": 25,
        "height": 175,
        "weight": 70,
        "status": "student",
        "university": "Test University"
    }

def create_test_session_data(respondent_id: str):
    return {
        "respondent_id": respondent_id,
        "test_type": "reaction_time",
        "device_id": "TEST001",
        "device_name": "Test Device",
        "measurement_context": "Test measurement",
        "environment_notes": "Test environment",
        "additional_notes": "Test notes"
    }

def create_test_trial_data():
    return {
        "stimulus_type": "red",
        "stimulus_category": "led",
        "response_time": 150,
        "trial_number": 1,
        "reaction_type": "correct"
    }