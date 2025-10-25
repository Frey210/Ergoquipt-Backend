from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.api import api_router
from app.database.database import engine, Base
from app.database.models import User, UserRole
from app.core.auth import get_password_hash
from sqlalchemy.orm import Session
from app.database.database import get_db
import logging
from datetime import datetime

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Ergoquipt Backend API",
    description="Backend system for Ergoquipt Reaction-Time and Physiological Data Acquisition",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    """Create default admin user on startup"""
    try:
        db = next(get_db())
        # Check if default admin exists
        admin_user = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
        if not admin_user:
            admin_user = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                full_name="System Administrator",
                role=UserRole.SUPER_ADMIN,
                status="active",
                platform_access="both"
            )
            db.add(admin_user)
            db.commit()
            logging.info("Default admin user created")
    except Exception as e:
        logging.error(f"Error creating default admin: {e}")
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Ergoquipt Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)