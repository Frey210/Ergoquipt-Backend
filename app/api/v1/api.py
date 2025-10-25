from fastapi import APIRouter
from app.api.v1.endpoints import auth, admin, sessions, respondents, trials, export

api_router = APIRouter()

# Public endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])

# Mobile operator endpoints
api_router.include_router(respondents.router, prefix="/mobile", tags=["respondents"])
api_router.include_router(sessions.router, prefix="/mobile", tags=["sessions"])
api_router.include_router(trials.router, prefix="/mobile", tags=["trials"])

# Admin web endpoints
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(export.router, prefix="/admin", tags=["export"])

# Common endpoints (both mobile and web)
api_router.include_router(export.router, prefix="/export", tags=["export"])