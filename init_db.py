import os
import sys
from sqlalchemy import create_engine
from app.database.models import Base
from app.config import settings

def init_database():
    try:
        # Create tables
        engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating database tables: {e}")
        return False

if __name__ == "__main__":
    init_database()