from pydantic_settings import BaseSettings
from typing import List
import os

class Settings(BaseSettings):
    # Database - untuk Docker
    DATABASE_URL: str = "postgresql://ergoquipt:password@db:5432/ergoquipt"
    
    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-in-production-123456"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Security
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:8000", "http://0.0.0.0:8000"]
    
    # Platform
    ALLOWED_PLATFORMS: List[str] = ["mobile", "web"]
    
    # Admin
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin123"
    DEFAULT_ADMIN_EMAIL: str = "admin@ergoquipt.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()