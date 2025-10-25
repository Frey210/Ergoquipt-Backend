import uuid
from datetime import datetime, date
from typing import Any, Dict, List
import json
import random
import string

def generate_uuid() -> str:
    """Generate UUID string"""
    return str(uuid.uuid4())

def generate_session_code(prefix: str = "RT") -> str:
    """Generate unique session code: PREFIX-YYYYMMDD-XXX"""
    date_str = datetime.now().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
    return f"{prefix}-{date_str}-{random_str}"

def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO format string"""
    return dt.isoformat() if dt else None

def parse_date(date_str: str) -> date:
    """Parse date string to date object"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

def calculate_age(birth_date: date) -> int:
    """Calculate age from birth date"""
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def safe_json_loads(json_str: str) -> Dict[str, Any]:
    """Safely load JSON string"""
    try:
        return json.loads(json_str) if json_str else {}
    except json.JSONDecodeError:
        return {}

def safe_json_dumps(data: Dict[str, Any]) -> str:
    """Safely dump to JSON string"""
    try:
        return json.dumps(data, default=str)
    except (TypeError, ValueError):
        return "{}"

def calculate_statistics(numbers: List[float]) -> Dict[str, float]:
    """Calculate basic statistics from a list of numbers"""
    if not numbers:
        return {}
    
    return {
        "mean": sum(numbers) / len(numbers),
        "min": min(numbers),
        "max": max(numbers),
        "count": len(numbers)
    }

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable string"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"