try:
    from app.core import auth
    print("✅ app.core.auth import successful")
    
    from app.database import models
    print("✅ app.database.models import successful")
    
    from app.config import settings
    print("✅ app.config import successful")
    
    print("🎉 All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")