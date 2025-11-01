from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.api import api_router
from app.database.database import engine, Base, SessionLocal
from app.database.models import User, UserRole, UserStatus
from app.core.auth import get_password_hash
import logging
from datetime import datetime
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def create_default_admin():
    """Create default admin user"""
    db = SessionLocal()
    try:
        # Check if default admin exists
        admin_user = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
        if not admin_user:
            logger.info("Creating default admin user...")
            admin_user = User(
                username=settings.DEFAULT_ADMIN_USERNAME,
                email=settings.DEFAULT_ADMIN_EMAIL,
                password_hash=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                full_name="System Administrator",
                role=UserRole.SUPER_ADMIN,
                status=UserStatus.ACTIVE,
                platform_access="both",
                registration_type="admin_created",
                initial_password=False  # ✅ Admin tidak perlu ganti password pertama
            )
            db.add(admin_user)
            db.commit()
            logger.info("✅ Default admin user created successfully")
            logger.info(f"Username: {settings.DEFAULT_ADMIN_USERNAME}")
            logger.info(f"Password: {settings.DEFAULT_ADMIN_PASSWORD}")
        else:
            # ✅ Pastikan admin tidak punya initial_password flag
            if admin_user.initial_password:
                admin_user.initial_password = False
                db.commit()
                logger.info("✅ Updated admin user: removed initial_password flag")
            logger.info("✅ Default admin user already exists")
    except Exception as e:
        logger.error(f"❌ Error creating default admin: {e}")
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    create_default_admin()

@app.get("/")
async def root():
    return {"message": "Ergoquipt Backend API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)